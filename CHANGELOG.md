# 更新日志

## [2.0.0] - 2026-03-23

### 🚨 重大变更：项目废弃，迁移到官方 MCP

本项目（硬编码集成 MemOS）已**废弃**。请迁移到官方 MCP 方式。

### 变更内容

- ❌ 删除 `install.py`（不再需要硬编码安装）
- ❌ 删除 `restore_memos.py`（不再需要恢复脚本）
- ✅ 新增 `uninstall.py`（帮助用户删除旧的硬编码集成）
- ✅ 新增 `MIGRATION.md`（迁移指南）
- 📝 更新 `README.md`（引导用户迁移到 MCP）

### 迁移原因

| 旧方式（硬编码） | 新方式（MCP） |
|----------------|---------------|
| Copaw 更新会覆盖修改 | 不受更新影响 |
| 上下文管理问题 | 模型智能控制 |
| 会话崩溃丢失记忆 | 更可靠 |
| 自行维护 | 官方维护 |

### 如何迁移

1. 运行 `python uninstall.py` 删除旧的硬编码集成
2. 配置官方 MCP（见 README.md）
3. 重启 Copaw

### 官方文档

- https://memos-docs.openmem.net/cn/mcp_agent/mcp/guide

---

## [1.0.0] - 2026-03-22

### 新增

- 初始版本：MemOS Cloud 硬编码集成 for Copaw
- 自动记忆召回 (`MemosRecallHook`)
- 自动记忆存储 (`MemosAddHook`)
- 用户偏好管理
- 工具记忆
- 知识库支持
- 多模态记忆支持