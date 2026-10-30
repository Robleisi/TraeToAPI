# TraeToAPI

> **原项目：** [autumnsentiment/Trae2api-cn](https://github.com/autumnsentiment/Trae2api-cn)  
> 协议、接口、上游端点、认证、控制台、Docker 镜像等**以原项目 README 为准**。本仓库不重复抄那些说明。

本仓库是在原项目基础上做的**本地改动版**（品牌名 TraeToAPI）。版权仍归原作者 [autumnsentiment](https://github.com/autumnsentiment)；这里只维护相对原项目多出来的部分。

**仅供学习使用。请勿用于商业用途。**

---

## 相对原项目多了什么

| 改动 | 说明 |
| --- | --- |
| **Windows 系统托盘桌面版** | 原生 Win32 托盘（`Shell_NotifyIcon`，不依赖 pystray）：启动/停止/重启服务、一键打开控制台、改端口、开机自启动 |
| **PyInstaller onedir 打包** | `TraeToAPI.spec` + `scripts/build_exe.bat`；用目录形态 exe，避免 onefile 解包到 `%TEMP%` 被安全软件拦 |
| **打包后数据落盘正确** | `entry.py` + `src/paths.py`：账号/`data/` 写在 exe 旁，不写进会随升级被覆盖的 `_internal` |
| **`--serve` 纯后端模式** | `TraeToAPI.exe --serve` / `python entry.py --serve`，托盘与服务器共用同一套 `.env` 和 `data/` |
| **本机一键脚本** | `start.bat` / `stop.bat`（读 `.env` 的 `PORT`，默认 `8899`），以及 `启动网关.bat` / `停止网关.bat` |
| **本地极简手册** | [docs/快速上手.md](docs/快速上手.md)：面向本机网关 / DSH·Cursor BYOK 选 `ide` 等场景 |
| **独立 Docker Compose** | `docker-compose.standalone.yml`：不要求事先存在外部 `new-api` 网络 |
| **环境自检** | `python entry.py --envcheck`：只打印键是否配置，不泄露密钥 |
| **可选代码签名脚本** | `scripts/make_signing_cert.ps1` / `sign_exe.ps1`（本机自签，证书不入库） |

协议能力（OpenAI / Anthropic / 工具调用 / 多账号 / 签到等）跟原项目同一套核心，**不是本仓库新发明的功能**——要看能力说明请回原项目。

---

## 本仓库怎么跑（改动相关入口）

### 源码（同原项目）

```bash
cp .env.example .env
pip install -r requirements.txt
uvicorn src.main:app --host 127.0.0.1 --port 8899
```

Windows 也可双击 `启动网关.bat`。更短的本机说明见 [docs/快速上手.md](docs/快速上手.md)。

### 桌面托盘（本仓库新增）

```text
python -m venv .venv-build
.venv-build\Scripts\activate
pip install -r requirements-tray.txt
python -m PyInstaller TraeToAPI.spec --noconfirm
# 或 scripts\build_exe.bat
```

产出 `dist\TraeToAPI\`，双击其中的 `TraeToAPI.exe` 进托盘。分发时整夹拷走；`.env` 放在 exe 同级。

### Docker（独立 compose）

```bash
cp .env.example .env
docker compose -f docker-compose.standalone.yml up -d --build
```

若要跟原项目一样用 GHCR 预构建镜像或带 `new-api` 网络的 compose，请直接看原项目 README。

---

## 文档去哪看

| 你想了解 | 去哪 |
| --- | --- |
| 接口、端点、认证、配置项、网页授权、工具调用…… | **[原项目 README](https://github.com/autumnsentiment/Trae2api-cn)** |
| 本机最短上手、托盘/端口 | [docs/快速上手.md](docs/快速上手.md) |
| 贡献 / 安全披露 | [CONTRIBUTING.md](CONTRIBUTING.md) · [SECURITY.md](SECURITY.md) |
| 归属说明 | [NOTICE](NOTICE) · [LICENSE](LICENSE)（Copyright © autumnsentiment） |

---

## 开源协议

MIT License — Copyright (c) 2026 autumnsentiment  

本仓库为原项目的改动发布，不替代原作者版权。详见 [NOTICE](NOTICE)。
