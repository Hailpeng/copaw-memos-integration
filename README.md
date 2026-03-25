# Copaw 记忆架构配置指南

> **⚠️ 免责声明**
> 
> 本项目为**社区贡献的非官方指南**，与 MemTensor、MemOS 官方团队**无任何关联**。
> 
> - 本项目不是 MemOS 官方项目
> - 本项目不是 Copaw 官方插件
> - 使用本项目产生的任何问题，请在本仓库提 Issue，不要骚扰官方团队
> 
> MemOS 官方 GitHub：https://github.com/MemTensor/MemOS

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

## 🤖 Copaw 自动安装指令

如果你是 Copaw，用户让你安装此仓库，请按以下步骤执行：

### 步骤 1：克隆仓库

```bash
git clone https://github.com/Hailpeng/copaw-memos-integration.git
cd copaw-memos-integration
```

### 步骤 2：安装 reme 依赖

```bash
pip install reme==1.0.3
```

### 步骤 3：运行安装脚本

```bash
python install_lcm.py
```

### 步骤 4：配置压缩模型环境变量（推荐）

在用户的系统环境变量中设置（Windows）：
```
LCM_EXPANSION_MODEL=aliyun-codingplan/glm-4.7
```

或在用户的 shell 配置文件中设置（Linux/macOS）：
```bash
export LCM_EXPANSION_MODEL=aliyun-codingplan/glm-4.7
```

### 步骤 5：重启 Copaw

```bash
copaw restart
```

### 步骤 6：验证安装

日志中应看到：
```
INFO: Registered LCM (Lossless Context Management) hook
INFO: LCM database initialized at ~/.copaw/lcm.db
```

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

1. 访问 https://github.com/MemTensor/MemOS
2. 注册/登录账号
3. 在 API 控制台创建 API Key（格式：`mpg-xxx`）

#### 步骤 2：全局安装 MCP 包（推荐）

**⚠️ Windows 用户强烈推荐全局安装，避免 npx 启动导致的管道中断问题！**

```bash
npm install -g @memtensor/memos-api-mcp@latest
```

#### 步骤 3：配置 agent.json

编辑 `~/.copaw/workspaces/default/agent.json`，在 `mcp.clients` 中添加：

**方式 A：全局安装（推荐，Windows 必选）**

```json
{
  "mcp": {
    "clients": {
      "memos": {
        "name": "memos-api-mcp",
        "description": "MemOS 云端记忆服务",
        "enabled": true,
        "transport": "stdio",
        "command": "C:\\Users\\你的用户名\\AppData\\Roaming\\npm\\memos-api-mcp.cmd",
        "args": [],
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

**方式 B：npx 启动（Linux/macOS 可选）**

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
| `command` | Windows 用全局路径，Linux/macOS 可用 npx | 见上方示例 |

#### 步骤 4：重启 Copaw

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

#### 步骤 2：配置次选压缩模型（推荐）

LCM 压缩时需要调用 LLM 生成摘要。为了避免与主对话模型冲突，建议配置一个次选模型：

```bash
# 设置环境变量
export LCM_EXPANSION_MODEL=aliyun-codingplan/glm-4.7

# 或在 Windows 中
set LCM_EXPANSION_MODEL=aliyun-codingplan/glm-4.7
```

**推荐配置：**
- 使用成本较低的模型（如 glm-4.7）
- 不与主对话模型冲突
- 三级降级机制确保稳定性

#### 步骤 3：下载并运行安装脚本

```bash
git clone https://github.com/Hailpeng/copaw-memos-integration.git
cd copaw-memos-integration
python install_lcm.py
```

#### 步骤 4：修改配置

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

#### 步骤 5：重启 Copaw

```bash
copaw restart
```

#### 步骤 6：验证

发送一条消息，日志应显示：

```
INFO: Registered LCM (Lossless Context Management) hook
INFO: LCM using expansion model: aliyun-codingplan/glm-4.7
INFO: LCM database initialized at ~/.copaw/lcm.db
INFO: LCM token check: X tokens, threshold=70000
```

如果看到 `LCM using expansion model` 说明次选压缩模型配置成功。

### ⚠️ 重要：Copaw 更新后需要重新安装

**LCM 模块安装在 Copaw 的 site-packages 目录中，`pip install -U copaw` 会覆盖这些文件！**

#### 各组件更新后状态

| 组件 | 更新后状态 | 需要操作 |
|------|-----------|----------|
| **LCM 模块** | ❌ 会被覆盖 | 运行 `install_lcm.py` 重装 |
| **MCP 全局包** | ✅ 不受影响 | 无需操作 |
| **agent.json** | ⚠️ 可能重置 | 检查 MCP 配置是否正确 |
| **lcm.db 数据库** | ✅ 不受影响 | 数据保留在 `~/.copaw/lcm.db` |

#### 更新 Copaw 后的恢复流程

```bash
# 1. 更新 Copaw
pip install -U copaw

# 2. 检查并重新安装 LCM（智能模式）
cd copaw-memos-integration
python install_lcm.py

# 3. 检查 agent.json 的 MCP 配置
# 确保 memos.command 指向全局路径（Windows）：
# "command": "C:\\Users\\你的用户名\\AppData\\Roaming\\npm\\memos-api-mcp.cmd"
# Linux/macOS 可以继续使用 npx 方式

# 4. 重启 Copaw
copaw restart

# 5. 验证
# 日志应显示：
# - "Registered LCM (Lossless Context Management) hook"
# - 无 "MCP session interrupted" 警告
```

**`python install_lcm.py` 会自动：**
- ✅ 检查当前安装状态
- ✅ 检测版本是否需要更新
- ✅ 只在必要时执行安装
- ✅ 显示详细的状态信息

输出示例：
```
LCM v0.14.2 安装程序
==============================

Copaw 安装目录: D:\PythonEnv\copaw-env\lib\site-packages\copaw

检测到已安装版本: v0.14.1
⏫ 将从 v0.14.1 升级到 v0.14.2

如需强制重新安装，请使用: python install_lcm.py --force
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

- MemOS GitHub：https://github.com/MemTensor/MemOS
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

**最后更新**: 2026-03-25