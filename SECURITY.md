# Security Policy

## 支持范围

本项目是面向学习的 Trae CN / Solo CN 协议反代。请勿在公网裸奔部署；若对外暴露，必须设置强 `RELAY_API_KEYS` 并配合 TLS / 反向代理访问控制。

## 报告漏洞

请通过 GitHub 仓库的 **Private vulnerability reporting**（若已启用）或维护者私下渠道报告，并包含：

- 影响版本 / commit
- 复现步骤（不含真实凭据）
- 预期与实际行为
- 可行的修复建议（可选）

**不要**在公开 Issue、PR 或讨论区粘贴：

- Cloud-IDE-JWT / refresh token / 账号 cookie
- `data/accounts.json` 或完整 `.env`
- 可直接冒充用户的抓包原文

## 运维建议

- `.env` 与 `data/` 仅本机或私有卷保留，权限收紧（Unix 建议 `0600` / 目录 `0700`）
- 定期轮换 `RELAY_API_KEYS`
- 公网部署关闭不必要的管理面暴露，或加额外认证层
- 备份含凭据，按敏感数据处理

本软件按 MIT 许可「按现状」提供，不附带任何担保。
