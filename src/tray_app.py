"""TraeToAPI 系统托盘。

使用 src/native_tray.py 的原生 Win32 实现（Windows 11 25H2 兼容），
不再依赖 pystray。主线程跑托盘消息循环；服务操作在后台线程执行；
设置窗口（tkinter）在专属线程创建并运行 mainloop，与托盘互不阻塞。
"""

from __future__ import annotations

import os
import queue  # noqa: F401  兼容外部引用
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser
import winreg
from pathlib import Path

from .native_tray import MenuItem, NativeTray


def _tray_log(msg: str) -> None:
    base = getattr(sys, "_MEIPASS", None)
    target = Path(sys.executable).parent if base else Path(__file__).resolve().parent.parent
    try:
        with open(target / "tray-debug.log", "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%H:%M:%S')} {msg}\n")
    except OSError:
        pass


def _resolve_base() -> Path:
    """与 entry.py 一致：取「真正存在 .env」的那一级目录作为运行根。"""
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).parent
        for candidate in (exe_dir, exe_dir.parent, exe_dir.parent.parent):
            if (candidate / ".env").exists():
                return candidate
        return exe_dir
    return Path(__file__).parent.parent


BASE_DIR = _resolve_base()
ENV_PATH = BASE_DIR / ".env"
# onefile 模式下 assets 打进 exe，运行时解包到 _MEIPASS
ICON_PATH = Path(getattr(sys, "_MEIPASS", str(BASE_DIR))) / "assets" / "traetoapi.ico"
APP_NAME = "TraeToAPI"
DEFAULT_PORT = 8899
_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"

# --------------------------------------------------------------------------
# .env 端口读写（只动 PORT 一行，其余内容原样保留）
# --------------------------------------------------------------------------


def read_port() -> int:
    """从 .env 读取 PORT；缺失或非法时返回默认 8899。"""
    try:
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("PORT") and "=" in line:
                value = line.split("=", 1)[1].strip().strip('"').strip("'")
                if value.isdigit():
                    return int(value)
    except OSError:
        pass
    return DEFAULT_PORT


def write_port(port: int) -> None:
    """把 PORT 写回 .env（保留注释与其他行；无文件则新建）。"""
    lines: list[str] = []
    replaced = False
    try:
        lines = ENV_PATH.read_text(encoding="utf-8").splitlines()
    except OSError:
        lines = ["# TraeToAPI 本地配置", ""]
    for i, line in enumerate(lines):
        if line.strip().startswith("PORT") and "=" in line:
            lines[i] = f"PORT={port}"
            replaced = True
            break
    if not replaced:
        lines.append(f"PORT={port}")
    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------
# 开机自启动（注册表 Run 键，机制与 Tauri plugin-autostart 相同）
# --------------------------------------------------------------------------


def autostart_enabled() -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY) as key:
            winreg.QueryValueEx(key, APP_NAME)
            return True
    except OSError:
        return False


def set_autostart(enabled: bool) -> None:
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
        if enabled:
            if getattr(sys, "frozen", False):
                target = f'"{sys.executable}"'
            else:  # 开发模式：pythonw 静默运行 entry.py
                pythonw = Path(sys.executable).with_name("pythonw.exe")
                python = pythonw if pythonw.exists() else Path(sys.executable)
                target = f'"{python}" "{BASE_DIR / "entry.py"}"'
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, target)
        else:
            try:
                winreg.DeleteValue(key, APP_NAME)
            except FileNotFoundError:
                pass


# --------------------------------------------------------------------------
# 后端进程管理
# --------------------------------------------------------------------------


def _serve_command(port: int) -> list[str]:
    if getattr(sys, "frozen", False):
        return [sys.executable, "--serve"]
    return [
        sys.executable, "-m", "uvicorn", "src.main:app",
        "--host", "127.0.0.1", "--port", str(port),
        "--app-dir", str(BASE_DIR),
    ]


_EDGE_PATHS = (
    Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
    Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
    Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
)


def _find_browser() -> str:
    """定位 Edge/Chrome 可执行文件，找不到返回空串。"""
    for name in ("msedge", "chrome"):
        found = shutil.which(name)
        if found:
            return found
    for path in _EDGE_PATHS:
        try:
            if path.is_file():
                return str(path)
        except OSError:
            continue
    return ""


def open_console_window(url: str) -> None:
    """用独立应用窗口打开控制台。

    借助 Edge/Chrome 的 ``--app`` 模式：无地址栏、无标签页、独立窗口，
    配合独立 user-data-dir 不受本机浏览器扩展与登录状态影响。
    不引入额外运行时依赖，因此不影响打包体积与启动速度。
    """
    browser = _find_browser()
    if browser:
        profile = BASE_DIR / "webview-profile"
        try:
            subprocess.Popen(
                [
                    browser,
                    f"--app={url}",
                    f"--user-data-dir={profile}",
                    "--window-size=1280,900",
                    "--no-first-run",
                    "--no-default-browser-check",
                ],
                cwd=str(BASE_DIR),
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            return
        except OSError:
            pass
    webbrowser.open(url)


def server_up(port: int, timeout: float = 0.8) -> bool:
    """探测本机后端是否存活（GET /healthz）。"""
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/healthz", timeout=timeout):
            return True
    except (urllib.error.URLError, OSError):
        return False


class ServerManager:
    """跟踪托盘自己拉起的后端子进程；外部启动的服务只做探测不接管。"""

    def __init__(self) -> None:
        self.proc: subprocess.Popen | None = None

    def is_running(self, port: int) -> bool:
        if self.proc is not None and self.proc.poll() is None:
            return True
        return server_up(port)

    def start(self, port: int) -> None:
        if self.is_running(port):
            return
        env = os.environ.copy()
        env.setdefault("PORT", str(port))
        self.proc = subprocess.Popen(
            _serve_command(port),
            cwd=str(BASE_DIR),
            env=env,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        # 给后端一点启动时间，托盘状态由菜单文本动态反映，不阻塞
        for _ in range(20):
            if self.proc.poll() is not None or server_up(port):
                break
            time.sleep(0.5)

    def stop(self) -> None:
        if self.proc is None:
            return
        if self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=8)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        self.proc = None

    def restart(self, port: int) -> None:
        self.stop()
        self.start(port)


# --------------------------------------------------------------------------
# 设置窗口（tkinter，专属线程创建并运行 mainloop）
# --------------------------------------------------------------------------


def _open_settings(manager: ServerManager) -> None:
    import tkinter as tk
    from tkinter import messagebox

    port = read_port()
    win = tk.Tk()
    win.title(f"{APP_NAME} 设置")
    win.resizable(False, False)
    win.attributes("-topmost", True)

    tk.Label(win, text="服务端口").grid(row=0, column=0, padx=12, pady=12, sticky="e")
    port_var = tk.StringVar(value=str(port))
    tk.Entry(win, textvariable=port_var, width=10, justify="center").grid(row=0, column=1, padx=12, pady=12, sticky="w")

    auto_var = tk.BooleanVar(value=autostart_enabled())
    tk.Checkbutton(win, text="开机自动启动（写入当前用户注册表 Run 键）", variable=auto_var).grid(
        row=1, column=0, columnspan=2, padx=12, sticky="w")

    def save() -> None:
        value = port_var.get().strip()
        if not value.isdigit() or not (1 <= int(value) <= 65535):
            messagebox.showwarning(APP_NAME, "端口必须是 1-65535 的整数。", parent=win)
            return
        new_port = int(value)
        if new_port != port:
            write_port(new_port)
        set_autostart(bool(auto_var.get()))
        if new_port != port or (manager.proc is None and not server_up(new_port)):
            threading.Thread(target=lambda: manager.restart(new_port), daemon=True).start()
        messagebox.showinfo(APP_NAME, "设置已保存，服务将按新配置运行。", parent=win)
        win.destroy()

    tk.Button(win, text="保存并重启服务", width=16, command=save).grid(row=2, column=0, columnspan=2, pady=(4, 12))
    win.eval("tk::PlaceWindow . center")
    win.mainloop()


# --------------------------------------------------------------------------
# 托盘主循环
# --------------------------------------------------------------------------


def run_tray() -> int:
    manager = ServerManager()
    port_holder = {"port": read_port()}
    tray_holder: dict = {}

    def state_text() -> str:
        running = manager.is_running(port_holder["port"])
        return f"{APP_NAME} · 服务{'运行中' if running else '已停止'} · 127.0.0.1:{port_holder['port']}"

    def _open_console() -> None:
        port = port_holder["port"]
        # 服务可能仍在启动中，短暂等待就绪，避免窗口打开后是空白页
        for _ in range(20):
            if server_up(port, timeout=0.5):
                break
            time.sleep(0.5)
        open_console_window(f"http://127.0.0.1:{port}/web/login")

    def on_default() -> None:
        # 托盘回调运行在窗口消息线程，窗口启动放后台线程，避免卡住菜单
        threading.Thread(target=_open_console, daemon=True).start()

    def on_event(key: str) -> None:
        if key == "open":
            on_default()
        elif key == "start":
            port_holder["port"] = read_port()
            threading.Thread(
                target=lambda: (manager.start(port_holder["port"]), tray_holder["tray"].set_tip(state_text())),
                daemon=True).start()
        elif key == "stop":
            threading.Thread(
                target=lambda: (manager.stop(), tray_holder["tray"].set_tip(state_text())),
                daemon=True).start()
        elif key == "restart":
            port_holder["port"] = read_port()
            threading.Thread(
                target=lambda: (manager.restart(port_holder["port"]), tray_holder["tray"].set_tip(state_text())),
                daemon=True).start()
        elif key == "settings":
            # tkinter 窗口在专属线程创建运行，与托盘消息循环互不阻塞
            threading.Thread(target=lambda: _open_settings(manager), daemon=True).start()
        elif key == "autostart":
            set_autostart(not autostart_enabled())
        elif key == "quit":
            threading.Thread(target=manager.stop, daemon=True).start()
            tray_holder["tray"].stop()

    items = [
        MenuItem(state_text, enabled=lambda: False),
        MenuItem(None, separator=True),
        MenuItem("打开控制台", "open", default=True),
        MenuItem("启动服务", "start"),
        MenuItem("停止服务", "stop", enabled=lambda: manager.proc is not None),
        MenuItem("重启服务", "restart"),
        MenuItem(None, separator=True),
        MenuItem("设置…", "settings"),
        MenuItem("开机自启动", "autostart", checked=lambda: autostart_enabled()),
        MenuItem(None, separator=True),
        MenuItem("退出", "quit"),
    ]

    def on_prepare(evidence: dict) -> None:
        _tray_log(f"prepare evidence: {evidence}")
        # 托盘注册失败也照常拉起后端：服务可用性优先，图标问题另行诊断。
        threading.Thread(
            target=lambda: (manager.start(port_holder["port"]), tray_holder["tray"].set_tip(state_text())),
            daemon=True).start()

    tray = NativeTray(
        APP_NAME, str(ICON_PATH), items, on_default, on_event, on_prepare=on_prepare)
    tray_holder["tray"] = tray
    _tray_log("native tray loop start")
    try:
        tray.run()
    finally:
        manager.stop()
    return 0
