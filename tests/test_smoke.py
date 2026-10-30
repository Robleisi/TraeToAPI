"""最小烟测：核心模块可导入。

完整协议、流式与路由回归由开发环境自行扩展；本文件保证任何提交都不会
破坏 `uvicorn src.main:app` 的基本可启动性。
"""

import importlib

import pytest

MODULES = [
    "src.anthropic_api",
    "src.auth",
    "src.auth_cli",
    "src.auth_helper",
    "src.cli_client",
    "src.continuation",
    "src.images",
    "src.main",
    "src.model_limits",
    "src.raw_client",
    "src.reasoning_effort",
    "src.responses_api",
    "src.sse",
    "src.traework_compat",
    "src.traework_native_bridge",
    "src.trae_client",
    "src.trae_decrypt",
    "src.trae_remote_client",
]


@pytest.mark.parametrize("name", MODULES)
def test_module_import(name: str) -> None:
    importlib.import_module(name)
