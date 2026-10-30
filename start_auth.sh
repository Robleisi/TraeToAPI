#!/bin/sh
# ============================================================
#  TraeToAPI 授权助手（通用版）
#  中转站地址自动读取同目录 .env 的 PORT（缺失时用 8899）
#  本机回调: http://127.0.0.1:8765/authorize
#  其他部署也可直接从控制台「授权登录」处下载，脚本会内嵌实际地址。
#  运行: sh start_auth.sh  （或 chmod +x 后直接执行）
# ============================================================
set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
RELAY_PORT=""
if [ -f "$DIR/.env" ]; then
  RELAY_PORT="$(grep -E '^[[:space:]]*PORT[[:space:]]*=' "$DIR/.env" | head -n1 | cut -d= -f2 | tr -d ' \r"' )"
fi
[ -n "$RELAY_PORT" ] || RELAY_PORT=8899
RELAY="http://127.0.0.1:$RELAY_PORT"
PORT="8765"
HELPER="$DIR/web_login.py"

if [ -d "$HELPER" ]; then
  echo "web_login.py 目标不能是文件夹，请更换授权助手目录后重试。"
  exit 1
fi

echo "[1/2] 正在从中转站刷新授权助手脚本 web_login.py ..."
echo "      中转站: $RELAY"
TMP_HELPER="$HELPER.download.$$"
rm -f "$TMP_HELPER"
if ! curl -fsSL --max-time 20 -o "$TMP_HELPER" "$RELAY/web/login/download?as=py"; then
  rm -f "$TMP_HELPER"
  if [ -f "$HELPER" ]; then
    echo "      中转站暂不可达，继续使用本地已有的 web_login.py。"
  else
    echo "授权助手脚本下载失败：请先启动 TraeToAPI，并确认 $RELAY 可访问。"
    exit 1
  fi
elif ! mv "$TMP_HELPER" "$HELPER"; then
  rm -f "$TMP_HELPER"
  echo "无法更新授权助手脚本，请检查本目录写入权限。"
  exit 1
fi

if command -v python3 >/dev/null 2>&1; then
  PYCMD="python3"
elif command -v python >/dev/null 2>&1; then
  PYCMD="python"
else
  echo "未检测到 Python 3，请先安装。"
  exit 1
fi

echo "[2/2] 启动本机授权监听器: http://127.0.0.1:$PORT"
exec "$PYCMD" "$HELPER" --relay "$RELAY" --port "$PORT"
