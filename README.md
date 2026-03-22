# MemOS Cloud 集成 for Copaw

> 让 Copaw 拥有云端记忆能力，实现跨会话、跨设备的持久化记忆

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Copaw](https://img.shields.io/badge/Copaw-Compatible-green.svg)](https://github.com/agentscope-ai/copaw)
[![MemOS](https://img.shields.io/badge/MemOS-Cloud-orange.svg)](https://github.com/MemTensor/MemOS)

---

## 📖 目录

- [背景介绍](#背景介绍)
- [功能特性](#功能特性)
- [架构设计](#架构设计)
- [快速开始](#快速开始)
- [详细安装](#详细安装)
- [配置说明](#配置说明)
- [使用方法](#使用方法)
- [备份恢复机制](#备份恢复机制)
- [常见问题](#常见问题)
- [贡献指南](#贡献指南)

---

## 背景介绍

### 问题

Copaw 是一个强大的 AI Agent 框架，但其原生记忆系统存在以下局限：

1. **记忆不持久** - 每次会话都是全新的，无法记住之前的对话
2. **无法跨设备** - 在不同设备上无法共享记忆
3. **搜索能力有限** - 仅支持关键词搜索，无语义理解
4. **无分类管理** - 无法区分用户偏好、工具记忆等

### 解决方案

MemOS Cloud 是一个专业的云端记忆服务，提供：

- 🧠 **自动记忆捕获** - 每次对话自动存储
- 🔍 **语义搜索** - 基于向量相似度的智能检索
- 👤 **偏好管理** - 单独存储用户偏好
- 🔧 **工具记忆** - 记录工具调用历史
- 📚 **知识库** - 支持文档上传和检索
- 🖼️ **多模态** - 支持图片、文档等

本项目将 MemOS Cloud 完整集成到 Copaw 中，实现与 OpenClaw 插件相同的功能。

---

## 功能特性

### ✅ 已实现功能

| 功能 | 说明 |
|------|------|
| **MemosRecallHook** | 每次推理前自动召回相关记忆 |
| **MemosAddHook** | 每次回复后自动存储对话 |
| **memory_search** | 手动搜索记忆（本地+云端） |
| **memory_add** | 手动添加记忆 |
| **memory_feedback** | 自然语言反馈修正记忆 |
| **memory_get/delete** | 获取/删除特定记忆 |
| **task_status** | 查询异步任务状态 |
| **knowledgebase** | 知识库管理（创建/删除/文档上传） |
| **Recall Filter** | LLM 二次过滤，减少噪音 |
| **多模态记忆** | 支持图片、文档存储 |
| **多 Agent 支持** | Agent 级别记忆隔离 |

### 🔄 与 OpenClaw 插件对比

| 功能 | OpenClaw 插件 | 本集成 |
|------|--------------|--------|
| 自动召回 | `before_agent_start` hook | `MemosRecallHook` (pre_reasoning) ✅ |
| 自动存储 | `agent_end` hook | `MemosAddHook` (post_reply) ✅ |
| Preference 支持 | ✅ | ✅ |
| Tool Memory 支持 | ✅ | ✅ |
| Knowledge Base | ✅ | ✅ |
| Recall Filter | ✅ | ✅ |
| 多模态 | ✅ | ✅ |

---

## 架构设计

### 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                         Copaw Agent                         │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐                  │
│  │ MemosRecallHook │  │  MemosAddHook   │                  │
│  │  (pre_reasoning)│  │  (post_reply)   │                  │
│  └────────┬────────┘  └────────┬────────┘                  │
│           │                    │                            │
│           v                    v                            │
│  ┌─────────────────────────────────────┐                   │
│  │          MemoryManager              │                   │
│  │  ┌─────────────────────────────┐    │                   │
│  │  │       MemOSClient           │    │                   │
│  │  └─────────────┬───────────────┘    │                   │
│  └────────────────┼────────────────────┘                   │
│                   │                                         │
└───────────────────┼─────────────────────────────────────────┘
                    │
                    v
        ┌───────────────────────┐
        │    MemOS Cloud API    │
        │  (memos.memtensor.cn) │
        └───────────────────────┘
```

### 文件结构

```
copaw/agents/
├── hooks/
│   ├── memos_recall.py      # MemosRecallHook + MemosAddHook
│   └── __init__.py          # 导出 Hooks
├── tools/
│   ├── memory_search.py     # 所有 memory 工具
│   └── __init__.py          # 导出工具函数
├── memory/
│   └── memory_manager.py    # MemOSClient API 客户端
└── react_agent.py           # Hook 注册 + 工具注册
```

### 工作流程

#### 1. 记忆召回流程

```
用户输入
    ↓
MemosRecallHook (pre_reasoning)
    ↓
提取用户查询
    ↓
调用 MemOS Cloud API 搜索
    ↓
获取相关记忆、偏好、工具记忆
    ↓
（可选）Recall Filter LLM 过滤
    ↓
注入到 Agent Context
    ↓
Agent 推理
```

#### 2. 记忆存储流程

```
Agent 回复
    ↓
MemosAddHook (post_reply)
    ↓
提取对话内容
    ↓
截断、格式化
    ↓
调用 MemOS Cloud API 存储
    ↓
完成
```

---

## 快速开始

### 前置条件

- Python 3.10+
- Copaw 已安装
- MemOS Cloud API Key（[获取地址](https://memos.memtensor.cn)）

### 一键安装

```bash
# 1. 克隆仓库
git clone https://github.com/YOUR_USERNAME/copaw-memos-integration.git
cd copaw-memos-integration

# 2. 运行安装脚本
python install.py

# 3. 配置 API Key
# 编辑 ~/.copaw/workspaces/default/active_skills/memos-cloud/config.json
# 填入你的 API Key

# 4. 重启 Copaw
```

---

## 详细安装

### 步骤 1：准备 MemOS Cloud 账号

1. 访问 [MemOS Cloud](https://memos.memtensor.cn) 注册账号
2. 获取 API Key（格式：`mpg-xxx`）

### 步骤 2：创建配置文件

在 Copaw 工作空间创建配置文件：

```bash
# Linux/macOS
mkdir -p ~/.copaw/workspaces/default/active_skills/memos-cloud

# Windows
mkdir "C:\Users\你的用户名\.copaw\workspaces\default\active_skills\memos-cloud"
```

创建 `config.json`：

```json
{
  "apiKey": "mpg-YOUR_API_KEY_HERE",
  "baseUrl": "https://memos.memtensor.cn/api/openmem/v1",
  "userId": "copaw-user"
}
```

### 步骤 3：复制源码文件

将以下文件复制到 Copaw 安装目录：

```bash
# Linux/macOS
COPAW_PATH="$(python -c 'import copaw; print(copaw.__path__[0])')"

# Windows (PowerShell)
$COPAW_PATH = python -c "import copaw; print(copaw.__path__[0])"
```

复制文件：

```bash
cp src/hooks/memos_recall.py "$COPAW_PATH/agents/hooks/"
cp src/tools/memory_search.py "$COPAW_PATH/agents/tools/"
cp src/memory/memory_manager.py "$COPAW_PATH/agents/memory/"
```

### 步骤 4：修改 hooks/__init__.py

在 `copaw/agents/hooks/__init__.py` 中添加：

```python
from .memos_recall import MemosRecallHook, MemosAddHook

__all__ = [
    # ... 原有内容 ...
    "MemosRecallHook",
    "MemosAddHook",
]
```

### 步骤 5：修改 tools/__init__.py

在 `copaw/agents/tools/__init__.py` 中添加：

```python
from .memory_search import (
    create_memory_search_tool,
    create_memory_add_tool,
    create_memory_feedback_tool,
    create_memory_get_tool,
    create_memory_delete_tool,
    create_task_status_tool,
    create_knowledgebase_tools,
)

__all__ = [
    # ... 原有内容 ...
    "create_memory_search_tool",
    "create_memory_add_tool",
    "create_memory_feedback_tool",
    "create_memory_get_tool",
    "create_memory_delete_tool",
    "create_task_status_tool",
    "create_knowledgebase_tools",
]
```

### 步骤 6：修改 react_agent.py

在 `copaw/agents/react_agent.py` 的 `_register_hooks()` 方法中，在 bootstrap_hook 注册代码之后添加 MemOS hook 注册代码。

**详见 `src/patches/react_agent_patch.py`**

### 步骤 7：重启 Copaw

```bash
copaw restart
```

---

## 配置说明

### config.json 完整配置

```json
{
  "apiKey": "mpg-xxx",
  "baseUrl": "https://memos.memtensor.cn/api/openmem/v1",
  "userId": "copaw-user",
  
  "recall": {
    "memoryLimit": 10,
    "preferenceLimit": 5,
    "toolMemoryLimit": 5,
    "includePreference": true,
    "includeToolMemory": true,
    "threshold": 0.1,
    "queryPrefix": "",
    "recallGlobal": true,
    "knowledgebaseIds": [],
    "tags": [],
    "filter": {
      "enabled": false,
      "baseUrl": "http://127.0.0.1:11434/v1",
      "model": "qwen2.5:7b"
    }
  },
  
  "add": {
    "captureStrategy": "last_turn",
    "includeAssistant": false,
    "throttleMs": 0,
    "maxMessageChars": 2000,
    "tags": [],
    "asyncMode": true,
    "multiAgentMode": false
  },
  
  "conversation": {
    "idPrefix": "",
    "idSuffix": "",
    "suffixMode": "none",
    "resetOnNew": true
  }
}
```

### 配置项说明

#### Recall 配置

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `memoryLimit` | int | 10 | 每次召回的普通记忆数量上限 |
| `preferenceLimit` | int | 5 | 每次召回的用户偏好数量上限 |
| `toolMemoryLimit` | int | 5 | 每次召回的工具记忆数量上限 |
| `threshold` | float | 0.1 | 相似度阈值，低于此值的结果会被过滤 |
| `recallGlobal` | bool | true | 是否全局搜索（false 则限制在当前会话） |
| `knowledgebaseIds` | list | [] | 指定搜索的知识库 ID |
| `tags` | list | [] | 按标签过滤 |

#### Add 配置

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `captureStrategy` | string | "last_turn" | 捕获策略：last_turn / full_session |
| `includeAssistant` | bool | false | 是否存储助手的回复 |
| `throttleMs` | int | 0 | 存储节流时间（毫秒），0 表示不节流 |
| `maxMessageChars` | int | 2000 | 单条消息最大字符数，超长会截断 |
| `asyncMode` | bool | true | 是否异步存储（不阻塞主流程） |

#### Recall Filter 配置

Recall Filter 使用 LLM 对召回的记忆进行二次过滤，减少无关内容：

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `enabled` | bool | false | 是否启用 |
| `baseUrl` | string | "http://127.0.0.1:11434/v1" | LLM API 地址 |
| `model` | string | "qwen2.5:7b" | 模型名称 |
| `timeoutMs` | int | 6000 | 超时时间（毫秒） |
| `failOpen` | bool | true | 失败时是否返回所有结果 |

---

## 使用方法

### 自动记忆

安装完成后，记忆会自动流转：

```
用户：我喜欢用中文交流
    ↓
MemosAddHook 自动存储到 MemOS Cloud

下次对话：
用户：你好
    ↓
MemosRecallHook 自动召回："用户偏好：中文交流"
    ↓
助手：（用中文回复）你好！有什么我可以帮你的吗？
```

### 手动记忆操作

#### 添加记忆

```
用户：帮我记住：我明天下午3点有个会议
助手：[调用 memory_add 工具] 已记住你的会议安排。
```

#### 搜索记忆

```
用户：搜索一下关于会议的记忆
助手：[调用 memory_search 工具] 
找到相关记忆：
- 2026-03-22: 用户明天下午3点有个会议
```

#### 反馈修正

```
用户：我刚才说的会议是下午4点，不是3点
助手：[调用 memory_feedback 工具] 已修正记忆：会议时间是下午4点。
```

### 知识库管理

```
用户：创建一个名为"项目文档"的知识库
助手：[调用 knowledgebase_create 工具] 已创建知识库"项目文档"。

用户：把这个 PDF 上传到知识库
助手：[调用 knowledgebase_doc_add 工具] 已上传文档到知识库。
```

---

## 备份恢复机制

### 问题背景

MemOS 集成代码是硬编码在 Copaw 源码中的，`pip upgrade copaw` 会覆盖所有修改。

### 解决方案

提供完整的备份恢复机制，确保 Copaw 更新后 MemOS 集成不丢失。

### 文件清单

需要备份的文件（共 6 个）：

| 文件 | 路径 | 说明 |
|------|------|------|
| `memos_recall.py` | `agents/hooks/` | Hook 实现 |
| `__init__.py` | `agents/hooks/` | Hooks 导出 |
| `memory_search.py` | `agents/tools/` | 工具实现 |
| `__init__.py` | `agents/tools/` | 工具导出 |
| `memory_manager.py` | `agents/memory/` | MemOS 客户端 |
| `react_agent.py` | `agents/` | Hook 注册 |

### 恢复脚本

```bash
# 自动恢复
python restore_memos.py

# 强制完整覆盖
python restore_memos.py --force

# 只检查不执行
python restore_memos.py --dry-run
```

### 集成到更新脚本

在你的 Copaw 更新脚本中添加：

```bash
# 更新 Copaw
pip install --upgrade copaw

# 恢复 MemOS 集成
python /path/to/restore_memos.py
```

---

## 常见问题

### Q: 安装后 Copaw 启动失败？

**A:** 检查以下几点：

1. 确认所有文件都已正确复制
2. 检查 `__init__.py` 是否正确添加了导出
3. 检查 `react_agent.py` 是否正确添加了 hook 注册代码
4. 查看 Copaw 日志获取详细错误信息

### Q: MemOS hooks 未注册？

**A:** 检查：

1. `config.json` 是否存在且包含有效的 `apiKey`
2. `react_agent.py` 中 `_register_hooks()` 是否正确修改
3. 查看 Copaw 启动日志中是否有 "Registered MemOS recall hook"

### Q: memory_search 工具不可用？

**A:** 检查：

1. `tools/__init__.py` 是否正确导出工具函数
2. `react_agent.py` 中 `_setup_memory_manager()` 是否正确注册工具

### Q: Copaw 更新后 MemOS 失效？

**A:** 运行恢复脚本：

```bash
python restore_memos.py
```

或手动恢复（见[详细安装](#详细安装)）。

### Q: 如何获取 MemOS API Key？

**A:** 

1. 访问 [MemOS Cloud](https://memos.memtensor.cn)
2. 注册/登录账号
3. 在控制台获取 API Key（格式：`mpg-xxx`）

---

## 贡献指南

欢迎贡献代码、报告问题或提出建议！

### 开发环境

```bash
# 克隆仓库
git clone https://github.com/YOUR_USERNAME/copaw-memos-integration.git
cd copaw-memos-integration

# 安装开发依赖
pip install -r requirements-dev.txt

# 运行测试
pytest tests/
```

### 提交 PR

1. Fork 本仓库
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

---

## 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件。

---

## 致谢

- [Copaw](https://github.com/agentscope-ai/copaw) - 强大的 AI Agent 框架
- [MemOS](https://github.com/MemTensor/MemOS) - 专业的云端记忆服务
- [MemOS Cloud OpenClaw Plugin](https://github.com/MemTensor/MemOS-Cloud-OpenClaw-Plugin) - 参考实现

---

## 联系方式

- GitHub Issues: [提交问题](https://github.com/YOUR_USERNAME/copaw-memos-integration/issues)
- MemOS 官方文档: [docs.memos.memtensor.cn](https://docs.memos.memtensor.cn)

---

**⭐ 如果这个项目对你有帮助，请给一个 Star！**