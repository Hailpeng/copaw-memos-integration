# 🚨 重要通知：本项目已废弃

## 请迁移到官方 MCP 方式

**本项目（硬编码集成 MemOS）已废弃。**

MemOS 官方已提供 **MCP 方式**，更稳定、更简单、由官方维护。

---

## 📦 新方案：官方 MemOS MCP

### 为什么迁移？

| 旧方式（本仓库） | 新方式（官方 MCP） |
|----------------|-------------------|
| 硬编码修改 Copaw 源码 | 通过 MCP 协议，无需改源码 |
| 每次 `pip upgrade copaw` 会丢失 | 不受 Copaw 更新影响 |
| 自行维护，可能有 Bug | 官方维护，更稳定 |
| 上下文管理容易出问题 | 模型智能控制记忆 |
| 会话崩溃可能丢失记忆 | 模型负责存储，更可靠 |

---

## 🔄 迁移步骤

### 步骤 1：删除旧的硬编码集成

运行卸载脚本：

```bash
# 克隆本仓库（如果还没有）
git clone https://github.com/Hailpeng/copaw-memos-integration.git
cd copaw-memos-integration

# 运行卸载脚本
python uninstall.py
```

### 步骤 2：清理本地文件

删除以下目录和文件：

```bash
# 删除本地 MemOS 配置
rm -rf ~/.copaw/workspaces/default/active_skills/memos-cloud
rm -rf ~/.copaw/workspaces/default/customized_skills/memos-cloud

# 删除备份目录
rm -rf ~/.copaw/workspaces/default/memos-backup
rm -rf ~/.copaw/workspaces/default/memos-integration
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

### 步骤 4：重启 Copaw

```bash
copaw restart
```

### 步骤 5：验证

重启后，模型会自动获得 `search_memory` 和 `add_message` 工具。

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

---

## 🗑️ 本仓库将归档

本仓库将保留作为参考，但不再维护。

**请尽快迁移到官方 MCP 方式！**

---

**更新日期**: 2026-03-23