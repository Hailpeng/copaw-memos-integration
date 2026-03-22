# 🚨 重要通知：本项目已废弃

## 请迁移到官方 MCP 方式

**本项目（硬编码集成 MemOS）已废弃。**

MemOS 官方已提供 **MCP 方式**，更稳定、更简单、由官方维护。

---

## 🤖 Copaw 用户一句话安装

**如果你是 Copaw 用户，只需要对 Copaw 说：**

> "帮我从这个仓库迁移到官方 MemOS MCP：https://github.com/Hailpeng/copaw-memos-integration"

Copaw 将自动执行以下步骤：

### 步骤 1：运行卸载脚本

```bash
git clone https://github.com/Hailpeng/copaw-memos-integration.git
cd copaw-memos-integration
python uninstall.py
```

### 步骤 2：清理本地文件

删除以下目录：

```bash
rm -rf ~/.copaw/workspaces/default/active_skills/memos-cloud
rm -rf ~/.copaw/workspaces/default/customized_skills/memos-cloud
rm -rf ~/.copaw/workspaces/default/memos-backup
rm -rf ~/.copaw/workspaces/default/memos-integration
rm -rf ~/.copaw/workspaces/default/copaw-memos-integration
rm -rf ~/.copaw/workspaces/default/memos-integration-repo
rm -rf ~/.copaw/workspaces/default/release-repo
rm -f ~/.copaw/workspaces/default/MEMOS_INTEGRATION_TASKS.md
```

### 步骤 3：配置官方 MCP

编辑 `~/.copaw/workspaces/default/agent.json`，在 `mcp.clients` 中添加：

```json
{
  "mcp": {
    "clients": {
      "memos": {
        "name": "memos-api-mcp",
        "description": "MemOS 云端记忆服务",
        "enabled": true,
        "transport": "stdio",
        "command": "npx",
        "args": ["-y", "@memtensor/memos-api-mcp@latest"],
        "env": {
          "MEMOS_API_KEY": "mpg-你的API密钥",
          "MEMOS_USER_ID": "你的用户标识",
          "MEMOS_CHANNEL": "MODELSCOPE"
        }
      }
    }
  }
}
```

**重要配置说明：**

| 环境变量 | 说明 | 示例值 |
|---------|------|--------|
| `MEMOS_API_KEY` | MemOS API 密钥（从 [memos.memtensor.cn](https://memos.memtensor.cn) 获取） | `mpg-xxx` |
| `MEMOS_USER_ID` | 用户标识（推荐使用邮箱、姓名或员工ID，**不要用随机值**） | `user@example.com` |
| `MEMOS_CHANNEL` | 固定填写 `MODELSCOPE` | `MODELSCOPE` |

### 步骤 4：重启 Copaw

```bash
copaw restart
```

### 步骤 5：验证迁移成功

重启后，模型应该能够使用 `search_memory` 和 `add_message` 工具。

---

## 📦 为什么迁移到官方 MCP？

| 问题 | 旧方式（硬编码） | 新方式（MCP） |
|------|----------------|---------------|
| **稳定性** | Copaw 更新会覆盖修改 | 不受 Copaw 更新影响 |
| **上下文管理** | 容易过长导致崩溃 | 模型智能控制 |
| **记忆丢失** | 会话崩溃可能丢失 | 模型负责存储 |
| **维护** | 自行维护 | 官方维护 |

---

## 📖 官方文档

- **MCP 配置指南**: https://memos-docs.openmem.net/cn/mcp_agent/mcp/guide
- **Agent 开发指南**: https://memos-docs.openmem.net/cn/mcp_agent/agent/guide
- **npm 包**: https://www.npmjs.com/package/@memtensor/memos-api-mcp

---

## ❓ 常见问题

### Q: 我的记忆数据会丢失吗？

**A: 不会！** MemOS 是云端服务，记忆存储在云端。迁移只是改变访问方式，数据不会丢失。

### Q: 之前的配置文件怎么办？

**A:** 你可以从旧的 `config.json` 中获取 API Key，用于 MCP 配置。

### Q: 迁移后功能会变化吗？

**A:** 功能相同，但更稳定：
- 模型主动决定何时使用记忆（不会盲目注入）
- 上下文由模型控制（不会过长崩溃）
- 官方维护（不会因为 Copaw 更新失效）

### Q: 如何获取 MemOS API Key？

**A:**
1. 访问 https://memos.memtensor.cn
2. 注册/登录账号
3. 在 API 控制台创建 API Key

---

## 🗑️ 本仓库将归档

本仓库将保留作为参考，但不再维护。

**请尽快迁移到官方 MCP 方式！**

---

**更新日期**: 2026-03-23