"""原生 Win32 托盘实现，不依赖 pystray。

Windows 11 25H2 (26200) 的任务栏会拒绝 pystray 的 Shell_NotifyIcon 注册，
而本模块的直接 Win32 调用已在该系统上验证可正常注册（参数、结构、窗口
类、线程模型均按验证结论实现）：WNDCLASSW + WM_APP 回调消息 + V2 结构。
"""

from __future__ import annotations

import ctypes
import logging
import threading
from ctypes import wintypes
from typing import Callable, Optional

logger = logging.getLogger(__name__)

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
user32 = ctypes.WinDLL("user32", use_last_error=True)
shell32 = ctypes.WinDLL("shell32", use_last_error=True)

NIM_ADD, NIM_MODIFY, NIM_DELETE = 0, 1, 2
NIF_MESSAGE, NIF_ICON, NIF_TIP = 0x1, 0x2, 0x4
IMAGE_ICON, LR_DEFAULTSIZE, LR_LOADFROMFILE = 1, 0x40, 0x10
WM_APP_TRAY = 0x8000
WM_LBUTTONUP = 0x0202
WM_RBUTTONUP = 0x0205
WM_COMMAND = 0x0111
WM_CLOSE = 0x0010
WM_DESTROY = 0x0002
TPM_RIGHTBUTTON = 0x0002
TPM_RETURNCMD = 0x0100
TPM_NONOTIFY = 0x0080
MF_STRING = 0x0
MF_SEPARATOR = 0x800
MF_CHECKED = 0x8
MF_GRAYED = 0x1
LRESULT = ctypes.c_longlong
WNDPROC = ctypes.WINFUNCTYPE(LRESULT, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)

user32.DefWindowProcW.restype = LRESULT
user32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.CreateWindowExW.restype = wintypes.HWND
user32.CreatePopupMenu.restype = wintypes.HMENU
shell32.Shell_NotifyIconW.restype = wintypes.BOOL
shell32.Shell_NotifyIconW.argtypes = [wintypes.DWORD, ctypes.c_void_p]


class _V(ctypes.Union):
    _fields_ = [("uTimeout", wintypes.UINT), ("uVersion", wintypes.UINT)]


class NOTIFYICONDATAW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD), ("hWnd", wintypes.HWND), ("uID", wintypes.UINT),
        ("uFlags", wintypes.UINT), ("uCallbackMessage", wintypes.UINT), ("hIcon", wintypes.HICON),
        ("szTip", wintypes.WCHAR * 128), ("dwState", wintypes.DWORD), ("dwStateMask", wintypes.DWORD),
        ("szInfo", wintypes.WCHAR * 256), ("v", _V), ("szInfoTitle", wintypes.WCHAR * 64),
        ("dwInfoFlags", wintypes.DWORD),
    ]
    _anonymous_ = ["v"]


class WNDCLASSW(ctypes.Structure):
    _fields_ = [
        ("style", wintypes.UINT), ("lpfnWndProc", WNDPROC), ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int), ("hInstance", wintypes.HINSTANCE), ("hIcon", wintypes.HICON),
        ("hCursor", wintypes.HANDLE), ("hbrBackground", wintypes.HBRUSH),
        ("lpszMenuName", wintypes.LPCWSTR), ("lpszClassName", wintypes.LPCWSTR),
    ]


MENUITEMW = ctypes.WINFUNCTYPE(ctypes.c_int)  # 占位避免误用
user32.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
user32.TrackPopupMenu.restype = wintypes.BOOL
user32.TrackPopupMenu.argtypes = [
    wintypes.HMENU, wintypes.UINT, ctypes.c_long, ctypes.c_long,
    ctypes.c_int, wintypes.HWND, ctypes.c_void_p]


class MenuItem:
    """托盘菜单项：label 显示文本，key 事件键，checked/enabled 动态查询。"""

    def __init__(self, label, key=None, *, checked=None, enabled=None, default=False, separator=False):
        self.label = label
        self.key = key
        self.checked = checked or (lambda: False)
        self.enabled = enabled or (lambda: True)
        self.default = default
        self.separator = separator


class NativeTray:
    """单实例系统托盘。run() 阻塞在调用线程，事件通过 on_event(key) 回调。"""

    def __init__(self, title: str, icon_path: str, items: list[MenuItem],
                 on_default: Callable[[], None], on_event: Callable[[str], None],
                 on_prepare: Optional[Callable[[dict], None]] = None):
        self.title = title
        self.icon_path = icon_path
        self.items = items
        self.on_default = on_default
        self.on_event = on_event
        self.on_prepare = on_prepare
        self._hwnd = None
        self._hicon = None
        self._nid = None
        self._last_add_gle = 0
        self._stop = threading.Event()
        self._registered = False
        self._proc = WNDPROC(self._wnd_proc)
        self._taskbar_created = user32.RegisterWindowMessageW("TaskbarCreated")

    # -- 窗口过程 -------------------------------------------------------
    def _wnd_proc(self, hwnd, msg, wparam, lparam):
        try:
            if msg == self._taskbar_created and self._registered:
                self._register_icon()  # explorer 重启后重新注册
                return 0
            if msg == WM_APP_TRAY:
                if lparam == WM_LBUTTONUP:
                    self.on_default()
                    return 0
                if lparam == WM_RBUTTONUP:
                    self._show_menu(hwnd)
                    return 0
                return 0
            if msg == WM_CLOSE:
                user32.PostQuitMessage(0)
                return 0
            return user32.DefWindowProcW(hwnd, msg, wparam, lparam)
        except Exception:
            logger.exception("托盘窗口过程异常")
            return 0

    def _show_menu(self, hwnd):
        menu = user32.CreatePopupMenu()
        if not menu:
            return
        cmd_map = {}
        for index, item in enumerate(self.items):
            cmd = index + 1
            flags = MF_STRING
            label = ""
            if item.separator:
                flags = MF_SEPARATOR
            else:
                label = item.label() if callable(item.label) else item.label
                if not item.enabled():
                    flags |= MF_GRAYED
                if item.checked():
                    flags |= MF_CHECKED
            user32.AppendMenuW(menu, flags, cmd, label)
            cmd_map[cmd] = item
        pt = wintypes.POINT()
        user32.GetCursorPos(ctypes.byref(pt))
        user32.SetForegroundWindow(hwnd)
        chosen = user32.TrackPopupMenu(
            menu, TPM_RIGHTBUTTON | TPM_RETURNCMD | TPM_NONOTIFY,
            pt.x, pt.y, 0, hwnd, None)
        user32.PostMessageW(hwnd, 0, 0, 0)  # MSDN：让 TrackPopupMenu 正常消失
        user32.DestroyMenu(menu)
        if chosen:
            item = cmd_map.get(chosen)
            if item is not None and item.key:
                self.on_event(item.key)

    # -- 图标注册 -------------------------------------------------------
    def _register_icon(self, uid: int = 1, cbmsg: int = WM_APP_TRAY, tip: str = "") -> bool:
        nid = NOTIFYICONDATAW()
        nid.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
        nid.hWnd = self._hwnd
        nid.uID = uid
        nid.uFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP
        nid.uCallbackMessage = cbmsg
        nid.hIcon = self._hicon
        nid.szTip = (tip or self.title)[:127]
        ok = bool(shell32.Shell_NotifyIconW(NIM_ADD, ctypes.byref(nid)))
        self._last_add_gle = ctypes.get_last_error() if not ok else 0
        self._registered = ok
        self._nid = nid if ok else None
        return ok

    def prepare(self) -> dict:
        """注册窗口类、建窗、载图标（不含消息循环），返回各步证据。

        run() 与诊断入口共用，保证线上运行与实验走完全同一条代码路径。
        """
        hinst = kernel32.GetModuleHandleW(None)
        wc = WNDCLASSW()
        wc.lpfnWndProc = self._proc
        wc.hInstance = hinst
        wc.lpszClassName = "TraeToAPITrayWnd"
        class_ok = bool(user32.RegisterClassW(ctypes.byref(wc)))
        self._hwnd = user32.CreateWindowExW(
            0, "TraeToAPITrayWnd", self.title, 0, 0, 0, 0, 0, None, None, hinst, None)
        self._hicon = user32.LoadImageW(
            None, self.icon_path, IMAGE_ICON, 0, 0, LR_DEFAULTSIZE | LR_LOADFROMFILE)
        nim_ok = self._register_icon() if self._hwnd and self._hicon else False
        return {
            "class": class_ok, "hwnd": bool(self._hwnd), "hicon": bool(self._hicon),
            "nim_add": nim_ok, "gle": getattr(self, "_last_add_gle", 0),
            "cbSize": ctypes.sizeof(NOTIFYICONDATAW),
        }

    def set_tip(self, text: str) -> None:
        """更新悬浮提示（服务状态变化时调用）。"""
        if not self._registered or self._nid is None:
            return
        self._nid.szTip = text[:127]
        shell32.Shell_NotifyIconW(NIM_MODIFY, ctypes.byref(self._nid))

    # -- 主循环 ---------------------------------------------------------
    def run(self) -> None:
        """阻塞当前线程直到 stop()。必须在主线程调用。"""
        evidence = self.prepare()
        if self.on_prepare is not None:
            try:
                self.on_prepare(evidence)
            except Exception:
                logger.exception("on_prepare 回调异常")
        if not evidence["class"]:
            raise OSError(f"RegisterClassW 失败 gle={ctypes.get_last_error()}")
        if not evidence["hwnd"]:
            raise OSError(f"CreateWindowExW 失败 gle={ctypes.get_last_error()}")
        if not evidence["hicon"]:
            raise OSError(f"图标加载失败 gle={ctypes.get_last_error()}")
        if not evidence["nim_add"]:
            # 失败仍进入消息循环，保证退出路径可用；证据写日志便于诊断。
            logger.error("NIM_ADD 失败 gle=%s cbSize=%s", evidence["gle"], evidence["cbSize"])

        msg = wintypes.MSG()
        while not self._stop.is_set():
            # PeekMessage 轮询：托盘消息与事件驱动逻辑同处主线程
            while user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 1):
                if msg.message == 0x0012:  # WM_QUIT
                    self._stop.set()
                    break
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))
            if self._stop.wait(0.2):
                break
        self.shutdown()

    def stop(self) -> None:
        self._stop.set()
        if self._hwnd:
            user32.PostMessageW(self._hwnd, WM_CLOSE, 0, 0)

    def shutdown(self) -> None:
        if self._nid is not None:
            shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(self._nid))
            self._nid = None
            self._registered = False
        if self._hwnd:
            user32.DestroyWindow(self._hwnd)
            self._hwnd = None
        user32.UnregisterClassW("TraeToAPITrayWnd", kernel32.GetModuleHandleW(None))
