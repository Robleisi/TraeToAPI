@echo off
rem ============================================================
rem  TraeToAPI 授权助手（通用版）
rem  中转站地址自动读取同目录 .env 的 PORT（缺失时用 8899）
rem  本机回调: http://127.0.0.1:8765/authorize
rem  其他部署也可直接从控制台「授权登录」处下载，脚本会内嵌实际地址。
rem ============================================================
setlocal enableextensions enabledelayedexpansion
chcp 65001 >nul

set "RELAY_PORT="
if exist "%~dp0.env" (
  for /f "usebackq tokens=1,2 delims==" %%A in ("%~dp0.env") do (
    set "KEY=%%A"
    set "VAL=%%B"
    for /f "tokens=*" %%K in ("!KEY!") do set "KEY=%%K"
    for /f "tokens=*" %%V in ("!VAL!") do set "VAL=%%V"
    if /i "!KEY!"=="PORT" set "RELAY_PORT=!VAL!"
  )
)
if not defined RELAY_PORT set "RELAY_PORT=8899"
set "RELAY=http://127.0.0.1:!RELAY_PORT!"
set "PORT=8765"
set "HELPER=%~dp0web_login.py"
set "TMP_HELPER=%HELPER%.download-%RANDOM%"

if exist "%HELPER%\" (
  echo web_login.py 目标不能是文件夹，请更换授权助手目录后重试。
  pause
  exit /b 1
)

echo [1/2] 正在从中转站刷新授权助手脚本 web_login.py ...
echo       中转站: !RELAY!
del /q "%TMP_HELPER%" >nul 2>nul
curl -fsSL --max-time 20 -o "%TMP_HELPER%" "!RELAY!/web/login/download?as=py"
if errorlevel 1 (
  del /q "%TMP_HELPER%" >nul 2>nul
  if exist "%HELPER%" (
    echo       中转站暂不可达，继续使用本地已有的 web_login.py。
  ) else (
    echo 授权助手脚本下载失败：请先启动 TraeToAPI（托盘图标），并确认 !RELAY! 可访问。
    pause
    exit /b 1
  )
) else (
  move /y "%TMP_HELPER%" "%HELPER%" >nul
  if errorlevel 1 (
    del /q "%TMP_HELPER%" >nul 2>nul
    echo 无法更新授权助手脚本，请检查本目录写入权限。
    pause
    exit /b 1
  )
)

where python >nul 2>nul
if errorlevel 1 (
  where py >nul 2>nul
  if errorlevel 1 (
    echo 未检测到 Python 3，请先安装 Python 并勾选 Add to PATH。
    pause
    exit /b 1
  )
  set "PYCMD=py -3"
) else (
  set "PYCMD=python"
)

echo [2/2] 启动本机授权监听器: http://127.0.0.1:%PORT%
echo 浏览器会自动打开中转站授权页面，在该页面点击授权登录即可。
%PYCMD% "%HELPER%" --relay "!RELAY!" --port "%PORT%"
if errorlevel 1 (
  echo 启动失败，请确认已安装 Python 3 并加入 PATH。
  pause
  exit /b 1
)
