@echo off
rem ============================================================
rem  TraeToAPI 桌面版构建
rem  产出: dist\TraeToAPI\TraeToAPI.exe （onedir 目录形态、无控制台窗口、双击进托盘）
rem  说明: 使用独立构建环境 .venv-build，不影响运行用 .venv
rem        不用 onefile 单文件：其启动时要向 %%TEMP%% 解包运行时，
rem        部分安全软件会按进程来源拦截导致无法启动
rem ============================================================
setlocal
cd /d "%~dp0.."

if not exist .venv-build (
  echo [1/5] 创建构建虚拟环境 .venv-build ...
  python -m venv .venv-build
  if errorlevel 1 goto :fail
)
call .venv-build\Scripts\activate.bat

echo [2/5] 安装构建依赖 ...
python -m pip install -q -r requirements.txt -r requirements-tray.txt
if errorlevel 1 goto :fail

echo [3/5] PyInstaller 打包 ...
python -m PyInstaller TraeToAPI.spec --noconfirm
if errorlevel 1 goto :fail

rem 产物目录被 PyInstaller 重建过，配置必须在打包之后再放进去。
rem 分发时整个 dist\TraeToAPI 目录连同 .env 一起拷走即可独立运行。
echo [4/5] 准备运行配置与授权助手 ...
if exist .env (
  copy /y .env "dist\TraeToAPI\.env" >nul
  echo     已复制 .env 到 dist\TraeToAPI
) else (
  echo     警告: 未找到 .env，产物将以默认配置启动（端口 8899、无 API Key）
)
rem 控制台的「授权登录」需要在本机运行授权助手，脚本需与 exe 同目录。
if exist web_login.py copy /y web_login.py "dist\TraeToAPI\" >nul
if exist start_auth.bat copy /y start_auth.bat "dist\TraeToAPI\" >nul
if exist start_auth.sh copy /y start_auth.sh "dist\TraeToAPI\" >nul
if not exist "dist\TraeToAPI\data" mkdir "dist\TraeToAPI\data"

echo [5/5] Robleisi 自签名 ...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0sign_exe.ps1" -Target "%CD%\dist\TraeToAPI\TraeToAPI.exe"
rem 签名失败不阻断构建（证书缺失时 sign_exe.ps1 会自动跳过）

echo.
echo 构建完成: dist\TraeToAPI\TraeToAPI.exe （同目录含 .env）
endlocal
exit /b 0

:fail
echo.
echo 构建失败，请检查上方日志。
endlocal
exit /b 1
