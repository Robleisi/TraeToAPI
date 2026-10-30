@echo off
setlocal enableextensions enabledelayedexpansion
cd /d "%~dp0"
chcp 65001 >nul

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

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$p=%PORT%; $c=Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue; if($c){$c|ForEach-Object{Stop-Process -Id $_.OwningProcess -Force; Write-Host ('stopped PID '+$_.OwningProcess+' on '+$p)}}else{Write-Host ('port '+$p+' not listening')}"
