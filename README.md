# Copaw MemOS 集成指南

> 本仓库提供 MemOS Cloud 与 Copaw 的集成方案，帮助 Copaw 用户获得云端记忆能力

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Copaw](https://img.shields.io/badge/Copaw-Compatible-green.svg)](https://github.com/agentscope-ai/copaw)
[![MemOS](https://img.shields.io/badge/MemOS-Cloud-orange.svg)](https://github.com/MemTensor/MemOS)

---

## 📖 关于本项目

### 项目目的

本项目是一个**集成指南**，帮助 Copaw 用户将 [MemOS Cloud](https://github.com/MemTensor/MemOS) 的云端记忆能力集成到 Copaw Agent 中。

**为什么需要这个项目？**

- Copaw 原生不支持 MemOS Cloud
- OpenClaw 有官方的 MemOS 插件，但 Copaw 没有类似的插件系统
- 本项目通过硬编码方式，将 MemOS 功能集成到 Copaw 源码中

### 引用的开源项目

本项目依赖并引用以下开源项目：

| 项目 | 说明 | 许可证 |
|------|------|--------|
| [**MemOS**](https://github.com/MemTensor/MemOS) | 云端记忆服务核心项目 | Apache 2.0 |
| [**MemOS Cloud OpenClaw Plugin**](https://github.com/MemTensor/MemOS-Cloud-OpenClaw-Plugin) | OpenClaw 官方插件，本项目的参考实现 | Apache 2.0 |
| [**Copaw**](https://github.com/agentscope-ai/copaw) | AI Agent 框架 | Apache 2.0 |

**特别感谢 MemTensor 团队开发的 MemOS 云端记忆服务！**

### 与 MemOS 官方项目的关系

- **本项目不是 MemOS 的官方项目**
- **本项目不是 MemOS 官方支持的 Copaw 插件**
- 本项目是社区贡献的集成方案，参考了 MemOS Cloud OpenClaw Plugin 的实现

### MemOS Cloud 服务

MemOS Cloud 是 MemTensor 提供的云端记忆服务：

- 官网：https://memos.memtensor.cn
- 文档：https://docs.memos.memtensor.cn
- API：https://memos.memtensor.cn/api/openmem/v1

---

## ✨ 功能特性

通过本集成方案，Copaw 将获得以下能力：

| 功能 | 说明 |
|------|------|
| **自动记忆召回** | 每次对话前自动搜索相关记忆 |
| **自动记忆存储** | 每次对话后自动存储到云端 |
| **语义搜索** | 基于向量相似度的智能检索 |
| **用户偏好管理** | 单独存储和管理用户偏好 |
| **工具记忆** | 记录工具调用历史 |
| **知识库** | 上传文档，构建专属知识库 |
| **多模态记忆** | 支持图片、文档等 |
| **跨设备同步** | 在不同设备间共享记忆 |

### 与 OpenClaw 插件功能对比

| 功能 | OpenClaw 插件 | 本集成方案 |
|------|--------------|-----------|
| 自动召回 | ✅ | ✅ |
| 自动存储 | ✅ | ✅ |
| 偏好管理 | ✅ | ✅ |
| 工具记忆 | ✅ | ✅ |
| 知识库 | ✅ | ✅ |
| Recall Filter | ✅ | ✅ |
| 多模态 | ✅ | ✅ |

---

## 🚀 快速开始

### 前置条件

- Python 3.10+
- Copaw 已安装并正常运行
- MemOS Cloud API Key（从 [memos.memtensor.cn](https://memos.memtensor.cn) 获取）

### 安装步骤

```bash
# 1. 克隆本仓库
git clone https://github.com/Hailpeng/copaw-memos-integration.git
cd copaw-memos-integration

# 2. 运行安装脚本
python install.py --api-key YOUR_API_KEY

# 3. 重启 Copaw
copaw restart
```

安装完成后，Copaw 启动日志中应该看到：

```
INFO: Registered MemOS recall hook
INFO: Registered MemOS add hook
```

---

## 📚 详细安装指南

### 步骤 1：获取 MemOS Cloud API Key

1. 访问 [MemOS Cloud](https://memos.memtensor.cn)
2. 注册/登录账号
3. 在控制台获取 API Key（格式：`mpg-xxx`）

### 步骤 2：创建配置文件

```bash
# 创建配置目录
mkdir -p ~/.copaw/workspaces/default/active_skills/memos-cloud
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

将本仓库 `src/` 目录下的文件复制到 Copaw 安装目录：

```bash
# 查找 Copaw 安装路径
python -c "import copaw; print(copaw.__path__[0])"

# 复制文件（替换上面的路径）
cp src/hooks/memos_recall.py /path/to/copaw/agents/hooks/
cp src/tools/memory_search.py /path/to/copaw/agents/tools/
cp src/memory/memory_manager.py /path/to/copaw/agents/memory/
```

### 步骤 4：修改 Copaw 源码

需要修改以下文件（详见 `src/patches/` 目录）：

1. `agents/hooks/__init__.py` - 添加 Hooks 导出
2. `agents/tools/__init__.py` - 添加工具导出
3. `agents/react_agent.py` - 注册 Hooks

**详细修改步骤请参考 `src/patches/` 目录中的示例文件。**

### 步骤 5：验证安装

重启 Copaw 后，测试记忆功能：

```
用户：帮我记住：我喜欢用中文交流
助手：已记住你的偏好。

用户：我之前说过什么偏好？
助手：你之前说过：喜欢用中文交流
```

---

## ⚙️ 配置说明

### 完整配置示例

```json
{
  "apiKey": "mpg-xxx",
  "baseUrl": "https://memos.memtensor.cn/api/openmem/v1",
  "userId": "copaw-user",
  
  "recall": {
    "memoryLimit": 9,
    "preferenceLimit": 6,
    "toolMemoryLimit": 6,
    "includePreference": true,
    "includeToolMemory": true,
    "threshold": 0.45,
    "maxItemChars": 8000,
    "recallGlobal": true
  },
  
  "add": {
    "captureStrategy": "last_turn",
    "includeAssistant": false,
    "maxMessageChars": 2000,
    "asyncMode": true
  }
}
```

### 配置项说明

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `memoryLimit` | 9 | 每次召回的记忆数量上限 |
| `preferenceLimit` | 6 | 每次召回的偏好数量上限 |
| `toolMemoryLimit` | 6 | 每次召回的工具记忆数量上限 |
| `threshold` | 0.45 | 相似度阈值 |
| `maxItemChars` | 8000 | 每条记忆最大字符数 |
| `captureStrategy` | "last_turn" | 捕获策略：last_turn / full_session |
| `asyncMode` | true | 异步存储，不阻塞主流程 |

> **注意**: 以上默认值与 MemOS OpenClaw Plugin 官方默认值一致

---

## 🧠 上下文管理策略

### MemoryCompactionHook 已禁用

本集成方案**禁用了 Copaw 原生的 `MemoryCompactionHook`**，原因如下：

1. **上下文碎片化问题**: 原生压缩机制不知道哪些是"关键信息"，简单地按时间/位置裁剪
2. **任务中断**: 压缩后丢失重要上下文，导致任务执行中断
3. **MemOS 负责上下文统一**: MemOS 通过语义化召回保持上下文连贯性

### 与 MemOS OpenClaw Plugin 一致

原版 MemOS OpenClaw Plugin **没有上下文压缩机制**，完全依靠 MemOS 管理上下文。本集成方案与此保持一致。

### 上下文过长怎么办？

如果遇到上下文过长问题，请调整以下配置：

| 方法 | 配置项 | 说明 |
|------|--------|------|
| 减少召回数量 | `memoryLimit` | 降低召回的记忆数量 |
| 减少偏好数量 | `preferenceLimit` | 降低召回的偏好数量 |
| 限制记忆大小 | `maxItemChars` | 降低每条记忆最大字符数 |

**不要启用 MemoryCompactionHook**，它会破坏上下文连贯性。

---

## 🔄 备份与恢复

### 问题背景

由于本集成方案采用硬编码方式修改 Copaw 源码，`pip upgrade copaw` 会覆盖所有修改。

### 解决方案

每次更新 Copaw 后，运行恢复脚本：

```bash
python restore_memos.py
```

### 集成到更新脚本

建议在你的 Copaw 更新脚本中添加：

```bash
pip install --upgrade copaw
python /path/to/restore_memos.py
```

---

## ❓ 常见问题

### Q: 安装后 Copaw 启动失败？

**A:** 检查以下内容：
1. 确认所有文件已正确复制
2. 确认 `__init__.py` 文件已正确修改
3. 查看 Copaw 日志获取详细错误信息

### Q: 记忆功能不工作？

**A:** 检查以下内容：
1. `config.json` 中 API Key 是否正确
2. 网络是否能访问 `memos.memtensor.cn`
3. Copaw 日志中是否有 "Registered MemOS recall hook"

### Q: Copaw 更新后功能失效？

**A:** 运行恢复脚本：
```bash
python restore_memos.py
```

### Q: 如何获取 MemOS Cloud API Key？

**A:** 
1. 访问 https://memos.memtensor.cn
2. 注册/登录账号
3. 在控制台获取 API Key

### Q: MemOS 收费吗？

**A:** 请查看 MemOS Cloud 官网了解定价详情。

---

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

### 开发环境

```bash
git clone https://github.com/Hailpeng/copaw-memos-integration.git
cd copaw-memos-integration
pip install -r requirements-dev.txt
```

### 提交规范

- `feat:` 新功能
- `fix:` 修复 Bug
- `docs:` 文档更新
- `chore:` 其他修改

---

## 📄 许可证

本项目采用 **MIT 许可证** - 详见 [LICENSE](LICENSE) 文件。

**注意**：本项目依赖的 MemOS 采用 Apache 2.0 许可证。

---

## 🙏 致谢

### MemOS 团队

感谢 [MemTensor](https://github.com/MemTensor) 团队开发的 MemOS 云端记忆服务，让 AI Agent 拥有了持久化的记忆能力。

### 相关项目

- [MemOS](https://github.com/MemTensor/MemOS) - 云端记忆服务
- [MemOS Cloud OpenClaw Plugin](https://github.com/MemTensor/MemOS-Cloud-OpenClaw-Plugin) - OpenClaw 官方插件
- [Copaw](https://github.com/agentscope-ai/copaw) - AI Agent 框架

---

## 📞 联系方式

- **Issues**: [提交问题](https://github.com/Hailpeng/copaw-memos-integration/issues)
- **MemOS 官方**: [memos.memtensor.cn](https://memos.memtensor.cn)

---

**⭐ 如果这个项目对你有帮助，欢迎 Star！**