"""运行根目录解析。

开发时是仓库根目录；打包后是 exe 所在目录。PyInstaller 下 ``__file__``
会落到 ``_internal``，因此 entry.py 启动时把解析结果写入环境变量
``TRAETOAPI_BASE_DIR``，各模块统一通过 :func:`app_dir` 读取，避免把账号
等持久化数据写进会被升级覆盖的 ``_internal`` 目录。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def app_dir() -> Path:
    override = os.environ.get("TRAETOAPI_BASE_DIR", "").strip()
    if override:
        return Path(override)
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


def data_dir() -> Path:
    """持久化数据目录（账号、用量记录等）。

    放在运行根下的 ``data/``，与 ``.env`` 同级，便于用户自行备份或迁移。
    """
    return app_dir() / "data"
