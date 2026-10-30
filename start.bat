@echo off
setlocal enableextensions enabledelayedexpansion
cd /d "%~dp0"
chcp 65001 >nul

rem 从 .env 读取 PORT（缺省 8899）；优先使用仓库内 .venv
set "PORT=8899"
if exist "%~dp0.env" (
  for /f "usebackq tokens=1,* delims==" %%A in ("%~dp0.env") do (
    set "KEY=%%A"
    set "VAL=%%B"
    for /f "tokens=*" %%K in ("!KEY!") do set "KEY=%%K"
    for /f "tokens=*" %%V in ("!VAL!") do set "VAL=%%V"
    if /i "!KEY!"=="PORT" if not "!VAL!"=="" set "PORT=!VAL!"
  )
)

set "PY="
if exist "%~dp0.venv\Scripts\python.exe" set "PY=%~dp0.venv\Scripts\python.exe"
if not defined PY if exist "%~dp0.venv-build\Scripts\python.exe" set "PY=%~dp0.venv-build\Scripts\python.exe"
if not defined PY set "PY=python"

echo [TraeToAPI] starting on 127.0.0.1:!PORT!  (log: gateway.log)
"!PY!" -m uvicorn src.main:app --host 127.0.0.1 --port !PORT! >> "%~dp0gateway.log" 2>&1
