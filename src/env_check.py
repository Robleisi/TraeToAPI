"""打印运行时配置状态，用于确认 .env 是否被正确加载。

只输出键名与「是否设置 / 条数」，不打印任何密钥值。
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

_CHECKED_KEYS = (
    "PORT",
    "RELAY_PORT",
    "HOST",
    "UPSTREAM_MODE",
    "TRAE_AUTH_SOURCE",
    "TRAE_RAW_BASE_URL",
    "TRAE_API_HOST",
    "LOG_LEVEL",
)


def run_check(base: Path, out_path: Optional[Path] = None) -> list[str]:
    lines: list[str] = []

    def add(msg: str) -> None:
        lines.append(msg)

    env_file = base / ".env"
    add(f"BASE_DIR={base}")
    add(f"env_file={env_file} exists={env_file.exists()}")

    keys = [k.strip() for k in os.environ.get("RELAY_API_KEYS", "").split(",") if k.strip()]
    add(f"RELAY_API_KEYS count={len(keys)}")
    for name in _CHECKED_KEYS:
        add(f"{name}={os.environ.get(name) or '<unset>'}")

    for name in ("TRAE_TOKEN", "TRAE_REFRESH_TOKEN", "TRAE_USER_ID"):
        add(f"{name} set={bool(os.environ.get(name))}")

    add(f"data_dir={(base / 'data').exists()}")

    text = "\n".join(lines)
    print(text)
    if out_path is not None:
        try:
            out_path.write_text(text, encoding="utf-8")
        except OSError:
            pass
    return lines
