# Contributing

感谢关注 TraeToAPI。提交前请先确认改动可离线复现，且不引入真实账号凭据。

## 开发环境

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
python -m pytest -q
```

本地启动：

```bash
uvicorn src.main:app --host 127.0.0.1 --port 8899
```

Windows 也可使用 `start.bat` / `停止网关.bat`，或打包后的托盘版（见 README）。

## 提交约定

- 不要提交 `.env`、`data/accounts.json`、日志、证书、`dist/`、分享包或抓包材料。
- 协议/路由改动请附带或更新 `tests/` 中的回归用例。
- 保持对外 API 兼容；破坏性变更请在 README / PR 中明确写出。
- 大文件与二进制产物用 Release 分发，不要塞进默认分支。

## Pull Request

1. Fork 并基于最新 `main` 开分支。
2. 本地 `pytest` 通过。
3. PR 说明：改了什么、为什么、如何验证。
4. 涉及上游协议时，写明端点（Remote / IDE / Solo / Work）与复现步骤；不要粘贴完整 token。

## 安全与凭据

发现可利用的安全问题，请按 [SECURITY.md](SECURITY.md) 私下披露，不要在公开 Issue 里贴 token / refresh token / JWT。
