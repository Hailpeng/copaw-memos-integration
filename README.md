# Copaw MemOS MCP 配置指南

> **⚠️ 免责声明**
> 
> 本项目为**社区贡献的非官方指南**，与 MemTensor、MemOS 官方团队**无任何关联**。
> 
> - 本项目不是 MemOS 官方项目
> - 本项目不是 Copaw 官方插件
> - 使用本项目产生的任何问题，请在本仓库提 Issue，不要骚扰官方团队
> 
> MemOS 官方网站：https://memos.memtensor.cn

---

## 🎯 这是什么？

本项目帮助 Copaw 用户配置 **MemOS MCP**，让 AI Agent 拥有云端记忆能力。

### MemOS MCP 功能

| 功能 | 说明 |
|------|------|
| `search_memory` | 语义搜索云端记忆 |
| `add_message` | 自动存储对话到云端 |
| 跨设备同步 | 在不同设备间共享记忆 |
| 用户偏好管理 | 单独存储用户偏好 |
| 知识库支持 | 上传文档构建专属知识库 |

---

## 🤖 Copaw 用户一句话安装

**对 Copaw 说：**

> "帮我配置 MemOS MCP 记忆服务，仓库地址：https://github.com/Hailpeng/copaw-memos-integration"

---

## 📦 安装指南

### 情况 A：新用户（没有用过硬编码集成）

直接配置 MCP：

#### 步骤 1：获取 MemOS API Key

1. 访问 https://memos.memtensor.cn
2. 注册/登录账号
3. 在 API 控制台创建 API Key（格式：`mpg-xxx`）

#### 步骤 2：配置 agent.json

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

**配置说明：**

| 参数 | 说明 | 示例 |
|------|------|------|
| `MEMOS_API_KEY` | API 密钥（从官网获取） | `mpg-xxx` |
| `MEMOS_USER_ID` | 用户标识（**推荐用邮箱/姓名，不要用随机值**） | `user@example.com` |
| `MEMOS_CHANNEL` | 固定值 | `MODELSCOPE` |

#### 步骤 3：重启 Copaw

```bash
copaw restart
```

#### 步骤 4：验证

重启后，模型会自动获得 `search_memory` 和 `add_message` 工具。

---

### 情况 B：旧用户（之前用过硬编码集成）

**⚠️ 如果你之前通过本项目安装过硬编码集成，需要先卸载！**

#### 步骤 1：卸载旧的硬编码集成

```bash
git clone https://github.com/Hailpeng/copaw-memos-integration.git
cd copaw-memos-integration
python uninstall.py
```

#### 步骤 2：清理本地文件

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

#### 步骤 3：按"情况 A"的步骤配置 MCP

见上方新用户安装步骤。

---

## ❓ 常见问题

### Q: 记忆数据存在哪里？

**A:** 记忆存储在 MemOS 云端服务器，不是本地。

### Q: 我的数据安全吗？

**A:** 数据存储在 MemOS 云端，请阅读 MemOS 官方的隐私政策。

### Q: 配置后 Copaw 启动失败？

**A:** 检查：
1. `agent.json` 格式是否正确（JSON 不能有注释）
2. API Key 是否正确
3. 查看日志获取详细错误

### Q: 如何获取 API Key？

**A:** 访问 https://memos.memtensor.cn 注册并创建。

### Q: MEMOS_USER_ID 填什么？

**A:** 推荐使用：
- 个人邮箱地址
- 姓名全称
- 员工 ID

**不要使用**随机字符串、设备 ID 或会话 ID，这会导致记忆无法跨设备同步。

### Q: MCP 和硬编码集成有什么区别？

| 方式 | 说明 | 优缺点 |
|------|------|--------|
| **MCP（推荐）** | 官方 npm 包，通过 MCP 协议 | ✅ 稳定、官方维护、不受 Copaw 更新影响 |
| **硬编码（已废弃）** | 修改 Copaw 源码 | ❌ Copaw 更新会丢失、有 bug、不再维护 |

---

## 📚 相关资源

### 官方资源

- MemOS 官网：https://memos.memtensor.cn
- MemOS 文档：https://memos-docs.openmem.net
- npm 包：https://www.npmjs.com/package/@memtensor/memos-api-mcp

### 本项目资源

- 本仓库：https://github.com/Hailpeng/copaw-memos-integration
- 问题反馈：https://github.com/Hailpeng/copaw-memos-integration/issues

---

## 📄 许可证

MIT License

---

## 🙏 致谢

感谢 MemTensor 团队开发 MemOS 云端记忆服务。

**再次声明：本项目与 MemTensor 官方团队无任何关联，如有问题请在本仓库提 Issue。**

---

**最后更新**: 2026-03-23