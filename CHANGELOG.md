# 更新日志

所有重要的更改都会记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [v0.07] - 2026-03-22

### 修复
- **根因修复**: 移除 `memory_block` 模板中硬编码的 `user原始query：` 前缀
  - 这个前缀会在每次召回时累积，导致用户消息开头出现重复的前缀
  - v0.05/v0.06 的修复只是"创可贴"，v0.07 才是根因修复

### 技术细节
- **问题**: 云端存储的消息会包含旧记忆块和前缀，每次召回都会累积
- **根因**: 模板硬编码了 `user原始query：` 前缀，每次注入都添加
- **解决**: 删除模板中的前缀，依赖 `_remove_memory_blocks` 清理历史残留

### 影响版本
- v0.05 及更早版本：每次召回都会在用户消息开头添加 `user原始query：` 前缀
- v0.06：添加了清理旧记忆块的逻辑，但模板仍包含前缀
- v0.07：彻底移除模板前缀，根因修复

## [v0.06] - 2026-03-22

### 修复
- 在注入新记忆块前，清理用户消息中的旧记忆块和残留前缀
- 添加 `_remove_memory_blocks()` 和 `_clean_memory_blocks_in_msg()` 方法

## [v0.05] - 2026-03-22

### 新增
- **Copaw 自动安装指南** - 在 README 开头添加详细的自动安装步骤
- 用户只需对 Copaw 说"帮我安装这个仓库中的 MemOS 记忆架构"即可自动安装

### 改进
- 安装步骤更加清晰，Copaw 能理解并自动执行
- 每个步骤都有具体的命令和代码示例

## [v0.04] - 2026-03-22

### 修复
- **严重问题**: 修复 TypedDict isinstance 检查错误
  - `TextBlock` 是 `TypedDict`，不支持 `isinstance` 检查
  - 改用 `isinstance(block, dict) and block.get("type") == "text"`
  - 修复 `memory_search` 工具搜索云端时的错误

### 影响
- 修复前：`memory_search` 工具搜索云端时报错 "TypedDict does not support instance and class checks"
- 修复后：云端搜索正常工作

## [v0.03] - 2026-03-22

### 修复
- **严重问题**: 修复配置路径使用错误工作目录的问题
  - 使用 `workspace_dir` 而非全局 `WORKING_DIR` 加载 MemOS 配置
  - 此问题导致 MemOS hooks 未被注册，云端记忆功能完全失效

### 影响
- 修复前：新会话无法召回云端记忆，`memory_search` 工具未搜索云端
- 修复后：MemOS hooks 正确注册，云端记忆功能正常工作

## [v0.02] - 2026-03-22

### 修复
- 修复上下文过长导致报错的问题
- 修复 `MemosRecallHook.__call__` 记忆注入逻辑，正确将记忆注入到用户消息

### 新增
- `maxItemChars` 配置项（默认 8000 字符），限制每条记忆最大字符数
- `config.json` 默认配置模板
- `_truncate_text()` 方法截断超长记忆
- `_format_facts()` / `_format_preferences()` 按 MemOS 格式化记忆

### 变更
- **禁用 `MemoryCompactionHook`** - 由 MemOS 负责上下文统一管理
- 更新默认配置为原版 OpenClaw Plugin 默认值：
  - `memoryLimit`: 10 → 9
  - `preferenceLimit`: 5 → 6
  - `toolMemoryLimit`: 5 → 6
  - `threshold`: 0.1 → 0.45

### 文档
- 新增「上下文管理策略」章节
- 更新配置说明

## [v0.01] - 2026-03-22

### 新增
- MemOS Cloud 基础集成
- `MemosRecallHook` - 自动召回记忆
- `MemosAddHook` - 自动存储对话
- `Recall Filter` - LLM 二次过滤支持
- 知识库管理工具
- 多模态记忆支持
- 备份恢复机制

### 已知问题
- 上下文过长时会报错
- 缺少 `maxItemChars` 配置限制记忆大小

---

## 版本说明

### 版本号格式

- **主版本号 (Major)**: 不兼容的 API 更改
- **次版本号 (Minor)**: 向后兼容的功能新增
- **修订号 (Patch)**: 向后兼容的问题修复

### 变更类型

- `新增` - 新功能
- `变更` - 现有功能的变更
- `弃用` - 即将移除的功能
- `移除` - 已移除的功能
- `修复` - 问题修复
- `安全` - 安全相关修复