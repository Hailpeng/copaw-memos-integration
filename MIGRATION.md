# 迁移指南：从硬编码集成迁移到官方 MCP

本文档帮助你从旧的硬编码 MemOS 集成迁移到官方 MCP 方式。

---

## 🎯 为什么要迁移？

| 问题 | 旧方式（硬编码） | 新方式（MCP） |
|------|----------------|---------------|
| **稳定性** | Copaw 更新会覆盖修改 | 不受 Copaw 更新影响 |
| **上下文管理** | 容易过长导致崩溃 | 模型智能控制 |
| **记忆丢失** | 会话崩溃可能丢失 | 模型负责存储 |
| **维护** | 自行维护 | 官方维护 |

---

## 📦 迁移步骤

### 步骤 1：卸载旧的硬编码集成

```bash
# 克隆仓库
git clone https://github.com/Hailpeng/copaw-memos-integration.git
cd copaw-memos-integration

# 运行卸载脚本
python uninstall.py
```

或者手动删除：

```bash
# 删除 Copaw 源码中的 MemOS 文件
rm /path/to/copaw/agents/hooks/memos_recall.py
rm /path/to/copaw/agents/tools/memory_search.py

# 恢复 __init__.py 文件（移除 MemOS 相关导入）
# 参考 uninstall.py 中的 restore_init_file 函数
```

### 步骤 2：清理本地文件

```bash
# 删除本地 MemOS 配置
rm -rf ~/.copaw/workspaces/default/active_skills/memos-cloud
rm -rf ~/.copaw/workspaces/default/customized_skills/memos-cloud

# 删除备份目录
rm -rf ~/.copaw/workspaces/default/memos-backup
rm -rf ~/.copaw/workspaces/default/memos-integration
rm -rf ~/.copaw/workspaces/default/copaw-memos-integration
rm -rf ~/.copaw/workspaces/default/memos-integration-repo
rm -rf ~/.copaw/workspaces/default/release-repo

# 删除任务文档
rm ~/.copaw/workspaces/default/MEMOS_INTEGRATION_TASKS.md
```

### 步骤 3：配置官方 MCP

编辑 `~/.copaw/workspaces/default/agent.json`：

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

### 步骤 5：验证迁移成功

重启后，模型应该能够使用 `search_memory` 和 `add_message` 工具。

---

## 🔑 获取 API Key

1. 访问 https://github.com/MemTensor/MemOS
2. 注册/登录账号
3. 在 API 控制台创建 API Key

---

## 📚 官方文档

- **MemOS GitHub**: https://github.com/MemTensor/MemOS
- **MCP 配置指南**: https://memos-docs.openmem.net/cn/mcp_agent/mcp/guide
- **Agent 开发指南**: https://memos-docs.openmem.net/cn/mcp_agent/agent/guide

---

## ❓ 常见问题

### Q: 我的记忆数据会丢失吗？

**A: 不会！** MemOS 是云端服务，记忆存储在云端。迁移只是改变访问方式，数据不会丢失。

### Q: 配置中的 USER_ID 应该填什么？

**A:** 推荐使用：
- 个人邮箱地址
- 姓名全称
- 员工 ID

**不要使用**随机值、设备 ID 或会话 ID。

### Q: 迁移后功能会变化吗？

**A:** 功能相同，但更稳定：
- 模型主动决定何时使用记忆
- 上下文由模型控制
- 官方维护

---

**更新日期**: 2026-03-23