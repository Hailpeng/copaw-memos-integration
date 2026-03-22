# Copaw 记忆架构配置指南

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

本项目帮助 Copaw 用户配置完整的记忆架构：

1. **MemOS MCP** - 云端长期记忆（跨会话）
2. **LCM 模块** - 本地上下文管理（会话内，永不丢失）

### 架构对比

| 组件 | 存储位置 | 用途 | 功能 |
|------|----------|------|------|
| **MemOS MCP** | 云端 | 跨会话长期记忆 | `search_memory`, `add_message` |
| **LCM 模块** | 本地 SQLite | 会话内上下文管理 | `lcm_grep`, `lcm_describe`, `lcm_expand` |

---

## ⚠️ 重要：检查你是否安装过旧的硬编码集成

**在安装之前，请先检查你是否之前通过本项目安装过硬编码集成！**

### 如何检查

运行以下命令，查看是否存在这些文件：

```bash
# 检查 Copaw 源码中的 MemOS 文件
ls ~/.copaw-env/lib/site-packages/copaw/agents/hooks/memos_recall.py 2>/dev/null && echo "⚠️ 检测到硬编码集成！"

# 或者检查本地配置目录
ls ~/.copaw/workspaces/default/active_skills/memos-cloud 2>/dev/null && echo "⚠️ 检测到旧配置！"
```

### 如果你检测到硬编码集成

**必须先卸载旧集成再安装新的！**

```bash
git clone https://github.com/Hailpeng/copaw-memos-integration.git
cd copaw-memos-integration
python uninstall.py
```

详见 [MIGRATION.md](MIGRATION.md)

---

## 🚀 快速安装

**对 Copaw 说：**

> "帮我配置完整的记忆架构，仓库地址：https://github.com/Hailpeng/copaw-memos-integration"

---

## 📦 组件一：MemOS MCP（云端记忆）

### 功能

| 功能 | 说明 |
|------|------|
| `search_memory` | 语义搜索云端记忆 |
| `add_message` | 自动存储对话到云端 |
| 跨设备同步 | 在不同设备间共享记忆 |
| 用户偏好管理 | 单独存储用户偏好 |
| 知识库支持 | 上传文档构建专属知识库 |

### 安装步骤

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
| `MEMOS_USER_ID` | 用户标识（**推荐用邮箱/姓名**） | `user@example.com` |
| `MEMOS_CHANNEL` | 固定值 | `MODELSCOPE` |

#### 步骤 3：重启 Copaw

```bash
copaw restart
```

---

## 📦 组件二：LCM 模块（本地上下文管理）

### 功能

| 功能 | 说明 |
|------|------|
| **SQLite 持久化** | 所有消息存储到本地，永不丢失 |
| **DAG 多层摘要** | 智能压缩，保护最近消息 |
| **FTS5 全文搜索** | 支持中文搜索历史 |
| **Agent 工具** | `lcm_grep`, `lcm_describe`, `lcm_expand` |
| **阈值触发** | 上下文达到 70% 时自动压缩 |

### 为什么需要 LCM？

**问题**：Copaw 默认的上下文管理会丢失消息，长对话容易超出 API 限制导致报错。

**解决**：LCM 实现无损上下文管理：
- 所有消息持久化到 SQLite
- DAG 结构智能压缩
- Agent 可搜索和展开压缩的历史

### 安装步骤

#### 步骤 1：安装 reme 包

```bash
pip install reme==1.0.3
```

#### 步骤 2：下载并运行安装脚本

```bash
git clone https://github.com/Hailpeng/copaw-memos-integration.git
cd copaw-memos-integration
python install_lcm.py
```

#### 步骤 3：修改配置

编辑 `~/.copaw/workspaces/default/agent.json`，确保以下配置：

```json
{
  "running": {
    "max_input_length": 100000,
    "memory_compact_ratio": 0.7,
    "memory_reserve_ratio": 0.15
  }
}
```

#### 步骤 4：重启 Copaw

```bash
copaw restart
```

#### 步骤 5：验证

发送一条消息，日志应显示：

```
INFO: Registered LCM (Lossless Context Management) hook
INFO: LCM database initialized at ~/.copaw/lcm.db
```

### LCM Agent 工具

安装后，Agent 自动获得以下工具：

| 工具 | 功能 |
|------|------|
| `lcm_grep(query)` | 搜索所有历史（包括压缩的内容） |
| `lcm_describe()` | 查看 DAG 结构和统计信息 |
| `lcm_expand(summary_id)` | 展开摘要，恢复原始消息 |

---

## 📁 文件位置

| 文件 | 路径 |
|------|------|
| LCM 数据库 | `~/.copaw/lcm.db` |
| agent.json | `~/.copaw/workspaces/default/agent.json` |

---

## ❓ 常见问题

### Q: MemOS 和 LCM 有什么区别？

**A:** 
- **MemOS**：云端长期记忆，跨会话共享
- **LCM**：本地上下文管理，会话内不丢失

两者配合使用，实现完整的记忆架构。

### Q: LCM 会影响性能吗？

**A:** 
- 消息写入 SQLite 是异步的，不影响响应速度
- 压缩只在达到阈值时触发
- 数据库大小通常在 MB 级别

### Q: 如何卸载 LCM？

**A:**
```bash
cd copaw-memos-integration
python install_lcm.py --uninstall
```

### Q: 配置后 Copaw 启动失败？

**A:** 检查：
1. `agent.json` 格式是否正确（JSON 不能有注释）
2. API Key 是否正确
3. 查看日志获取详细错误

---

## 📚 相关资源

### 官方资源

- MemOS 官网：https://memos.memtensor.cn
- MemOS 文档：https://memos-docs.openmem.net
- npm 包：https://www.npmjs.com/package/@memtensor/memos-api-mcp

### 参考项目

- [lossless-claw](https://github.com/Martian-Engineering/lossless-claw) - LCM 概念来源（3.2k stars）

### 本项目资源

- 本仓库：https://github.com/Hailpeng/copaw-memos-integration
- 问题反馈：https://github.com/Hailpeng/copaw-memos-integration/issues

---

## 📄 许可证

MIT License

---

## 🙏 致谢

感谢 MemTensor 团队开发 MemOS 云端记忆服务。
感谢 lossless-claw 项目提供 LCM 设计思路。

**再次声明：本项目与 MemTensor 官方团队无任何关联，如有问题请在本仓库提 Issue。**

---

**最后更新**: 2026-03-23