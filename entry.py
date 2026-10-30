"""TraeToAPI 桌面版入口。

用法（打包后为 TraeToAPI.exe，开发时为 python entry.py）：

  entry.py            启动系统托盘，自动拉起后端服务
  entry.py --serve    仅前台运行后端服务（供托盘子进程或服务器部署使用）

托盘为原生 Win32 实现（ctypes 调用 `Shell_NotifyIcon`），只用标准库；--serve
模式与托盘模式共用同一份 .env 与 data/ 运行数据，工作目录统一为可执行文件
（或本脚本）所在目录。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# 统一工作目录：把自己或任一层父目录中「真正存在 .env」的那一级作为运行根。
# 打包后常见三种布局：
#   分发      D:\Apps\TraeToAPI\TraeToAPI.exe + .env（同级）
#   本仓库    dist\TraeToAPI\TraeToAPI.exe，.env 在仓库根（上两层）
#   开发      entry.py 所在目录
def _resolve_base() -> Path:
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).parent
        for candidate in (exe_dir, exe_dir.parent, exe_dir.parent.parent):
            if (candidate / ".env").exists():
                return candidate
        return exe_dir
    return Path(__file__).parent


BASE_DIR = _resolve_base()
# 传给 src.paths：账号、用量记录等持久化数据写到运行根下的 data/，
# 而不是 PyInstaller 的 _internal 目录（升级会被覆盖）。
os.environ.setdefault("TRAETOAPI_BASE_DIR", str(BASE_DIR))
os.chdir(BASE_DIR)
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# 打包环境下 main.py 的 load_dotenv() 无法可靠回溯到运行根，这里按
# BASE_DIR 显式加载一次。override=False 保证真实环境变量优先。
try:
    from dotenv import load_dotenv

    load_dotenv(BASE_DIR / ".env", override=False)
except Exception:  # 缺少 .env 或 dotenv 不可用时继续，由下游按默认值运行
    pass


class _NullStream:
    """写向不可用流的兜底，避免 logging 抛 "NoneType has no attribute write"。"""

    encoding = "utf-8"

    def write(self, *_args, **_kwargs) -> int:
        return 0

    def flush(self) -> None:
        return None

    def isatty(self) -> bool:
        return False


def _serve() -> int:
    """前台运行后端服务（无托盘）。"""
    # 必须在导入 uvicorn/httpx 之前重定向：它们的 logging StreamHandler 在
    # 创建时就固定了 sys.stderr，窗口化打包下该值为 None，之后每个 HTTP
    # 请求都会往 stderr 写一整段 "Logging error" 转储（gateway.log 曾因此
    # 膨胀到数 MB 并掩盖真正的日志）。
    if getattr(sys, "frozen", False):
        log_path = BASE_DIR / "gateway.log"
        try:
            log = open(log_path, "a", encoding="utf-8", buffering=1)  # noqa: SIM115
        except OSError:
            log = None
        sys.stdout = sys.stderr = log if log is not None else _NullStream()

    from src import main as relay

    import uvicorn

    host = (os.getenv("LISTEN_HOST") or "127.0.0.1").strip()
    port = int((os.getenv("PORT") or os.getenv("RELAY_PORT") or "8899").strip() or "8899")
    uvicorn.run(relay.app, host=host, port=port, log_level="info")
    return 0


def _tray() -> int:
    """启动系统托盘。"""
    try:
        from src.tray_app import run_tray
    except ImportError as exc:  # 托盘模块或其依赖不可用
        print(f"托盘模块加载失败：{exc}\n开发环境请安装：pip install -r requirements-tray.txt")
        return 2
    return run_tray()


def main() -> int:
    argv = sys.argv[1:]
    if "--version" in argv:
        from src.main import APP_VERSION

        print(f"TraeToAPI v{APP_VERSION}")
        return 0
    try:
        if "--envcheck" in argv:
            from src.env_check import run_check

            run_check(BASE_DIR, BASE_DIR / "env-check.txt")
            return 0
        if "--serve" in argv:
            return _serve()
        return _tray()
    except SystemExit:
        raise
    except BaseException:
        # 无控制台窗口的打包版本：崩溃原因落盘，便于排查
        import traceback

        (BASE_DIR / "crash.log").write_text(traceback.format_exc(), encoding="utf-8")
        raise


if __name__ == "__main__":
    raise SystemExit(main())
