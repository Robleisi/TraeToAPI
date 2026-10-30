# -*- mode: python ; coding: utf-8 -*-
# TraeToAPI 桌面版打包配置（onedir 目录形态）。
# 构建：pyinstaller TraeToAPI.spec --noconfirm  （或直接运行 scripts/build_exe.bat）
# 产出：dist/TraeToAPI/TraeToAPI.exe —— 双击进托盘；加 --serve 为纯后端模式。
#
# 不用 onefile 的原因：onefile 每次启动要把运行时解包到 %TEMP%\_MEIxxx，
# 部分安全软件会按进程来源拦截这一行为（本机实测 D 盘上的 exe 必失败、
# C 盘正常），onedir 直接使用 exe 旁的 _internal 目录，没有临时解包步骤。

a = Analysis(
    ["entry.py"],
    pathex=["."],
    binaries=[],
    datas=[("assets/traetoapi.ico", "assets")],
    hiddenimports=[
        # uvicorn 的循环/协议实现按字符串动态导入，PyInstaller 探测不到
        "uvicorn.loops.auto",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan.on",
        "anyio._backends._asyncio",
    ],
    excludes=["matplotlib", "numpy", "pytest"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="TraeToAPI",
    console=False,
    icon="assets/traetoapi.ico",
    upx=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    name="TraeToAPI",
)
