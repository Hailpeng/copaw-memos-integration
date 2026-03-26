# 更新日志

## [1.3.0] - 2026-03-26

### 修复

- **🔴 关键：单条大消息截断** - 当只有一条消息但超过 API 限制时，现在会正确截断
  - 问题：`compactor.py` 对单条消息返回原消息，不触发任何处理
  - 修复：新增 `_truncate_message()` 和 `_truncate_all_messages()` 方法
  - 效果：单条 250k 字符消息正确截断到 202k 以内

- **🔴 关键：字符检查阈值优化** - 更早触发压缩，防止 API 超限
  - 问题：字符检查使用绝对限制而非阈值，导致压缩触发太晚
  - 修复：改用 `max_chars * context_threshold` 作为触发阈值
  - 效果：字符达到 141,926（70%）时就开始压缩，而不是等到 202,752

- **实际序列化大小检查** - 使用 `model_dump_json()` 获取真实发送大小
  - 问题：`_blocks_to_text()` 有截断，低估了实际发送的字符数
  - 修复：字符扫描使用 `model_dump_json()` 获取精确的序列化大小
  - 效果：准确检测何时会触发 API 限制

### 技术细节

```python
# 1. 使用实际序列化大小
if hasattr(m, 'model_dump_json'):
    char_len += len(m.model_dump_json())

# 2. 阈值触发（更早）
char_threshold = int(max_chars * self.config.context_threshold)
if char_len > char_threshold:
    return await self._do_compaction(messages, max_tokens)

# 3. 单条大消息截断
if content_size > max_chars:
    return [self._truncate_message(msg, max_chars - 100)]

# 4. 压缩失败的后备方案
return self._truncate_all_messages(messages, max_chars)
```

### 验证

- ✅ 单条 250k 字符消息 → 截断到 202k
- ✅ 10 条共 300k 字符 → 压缩成 2 条，30k 字符
- ✅ 字符超限检测 → 立即触发压缩

---

## [1.2.0] - 2026-03-25

### 修复

- **LCM 字符级早期检测** - 用户粘贴大量文本时仍超限报错的问题
  - 问题：Token 计数很慢，大段文本在计数完成前就已经超限
  - 修复：在 token 计数前增加快速字符扫描，超过 `max_input_chars` 立即触发压缩
  - 优化：扫描过程中提前退出，不浪费时间

### 改进

- **`_blocks_to_text` 方法增强**
  - 添加 `truncate` 参数，默认截断长内容
  - 新增类常量：`MAX_TEXT_BLOCK_CHARS = 4000`、`MAX_TOOL_RESULT_CHARS = 2000`
  - 对所有内容块类型进行长度限制，防止超大内容

- **配置字段位置修正**
  - `max_input_chars` 移到 dataclass 正确位置（`enable_fts` 后面）
  - 确保属性可以被正确访问

### 技术细节

```python
# FAST PATH: 字符扫描（快速，提前退出）
for m in messages:
    char_len += len(content)
    if char_len > max_chars:  # 202752
        return await self._do_compaction(...)  # 立即触发

# SLOW PATH: Token 计数（仅在字符未超限时执行）
total_tokens = await self._count_messages_tokens(messages)
```

---

## [0.14.2] - 2026-03-24

### 修复

- **LCM 压缩执行失败** - `compactor.py` 中 `Msg` 对象不支持 `id` 参数
  - 错误：`TypeError: Msg.__init__() got an unexpected keyword argument 'id'`
  - 修复：移除 `id=summary["id"]` 参数，summary ID 仅存储在数据库中
  - 影响：压缩触发后无法生成摘要，导致上下文持续增长

### 改进

- **同步运行环境修复到仓库** - 确保用户安装后功能正常
  - `config.py`: 添加 `max_input_chars` 字段用于强制压缩
  - `lcm_hook.py`: 添加 `model_id_for_tokenizer` 支持 tokenizer 选择

### 验证

- 压缩触发：✅ token 超过阈值时正确触发
- 压缩执行：✅ 100 条消息压缩至 33 条
- Summaries 存储：✅ 正确写入数据库

---

## [0.14.1] - 2026-03-23

### 修复

- **Windows GBK 编码问题** - 移除 `uninstall.py` 中的所有 emoji
  - 替换为 ASCII 兼容的文本：`[OK]`, `[X]`, `[!]`, `[i]` 等
  - 确保脚本在 Windows 默认控制台上正常运行

### 原因

Windows 默认使用 GBK 编码，无法显示 Unicode emoji。用户克隆仓库后运行 `python uninstall.py` 会报：

```
UnicodeEncodeError: 'gbk' codec can't encode character '\U0001f5d1'
```

---

## [0.14] - 2026-03-23

### 新增

- **自动清理旧的 MemOS 硬编码集成** - 安装 LCM 前自动检测并清理
  - 删除 `memory_search.py`（整个文件都是 MemOS 工具）
  - 清理 `memory_manager.py` 中的 `MemOSClient` 类和相关方法
  - 清理 `react_agent.py` 中的 `memory_add` 工具注册
  - 更新 `tools/__init__.py` 移除相关导出

### 原因

迁移到 MCP 方式后，Copaw 源码中仍残留旧的硬编码 MemOS 代码，导致：
- `memory_add` 等工具检查错误的配置路径
- 与 MCP 工具 `search_memory`/`add_message` 混淆
- 日志显示 "MemOS Cloud not configured" 误导用户

### 迁移指南

如果之前通过本项目安装过硬编码集成，请先运行：

```bash
python uninstall.py
```

然后再安装 LCM：

```bash
python install_lcm.py
```

**新用户直接运行 `python install_lcm.py` 即可，会自动清理。**

---

## [0.13] - 2026-03-23

### 新增

- **次选压缩模型机制** - 避免 LCM 压缩与主模型并发冲突
  - 新增配置字段: `expansion_provider`, `expansion_model`
  - 环境变量配置: `LCM_EXPANSION_MODEL=provider/model`
  - 示例: `LCM_EXPANSION_MODEL=aliyun-codingplan/glm-4.7`

- **三级优先级模型选择**
  1. expansion_model (专用 LCM 模型)
  2. memory_manager.chat_model
  3. create_model_and_formatter (当前会话模型)

- **create_model_by_slot 函数** - model_factory.py 扩展
  - 按指定 provider/model 创建模型实例
  - 用于次选压缩模型创建

### 修复

- **lcm_hook.py 异步调用修复**
  - `memory.clear()` → `await memory.clear()`
  - `memory.add(msg)` → `await memory.add(msg)`
  - `memory.update_compressed_summary()` → `await memory.update_compressed_summary()`

### 安装脚本优化

- 新增 `[4/6] 更新 model_factory.py` 步骤
- 自动合并 `create_model_by_slot` 函数到 Copaw 源码

### 配置示例

```bash
# .env 或环境变量
LCM_EXPANSION_MODEL=aliyun-codingplan/glm-4.7
```

```json
// 或在 config.py 中直接设置
expansion_provider: "aliyun-codingplan"
expansion_model: "glm-4.7"
```

### 验证日志

```
LCM using expansion model: aliyun-codingplan/glm-4.7
LCM token check: 8485 tokens, threshold=70000, max=100000
```

---

## [0.12] - 2026-03-23

### 新增

- **智能安装模式** - `python install_lcm.py` 自动检查并安装
  - 检测已安装版本
  - 只在必要时执行安装
  - 已是最新版本时跳过

- **版本检查功能**
  - `python install_lcm.py --force` 强制重新安装

### 文档

- **README 更新** - 添加 Copaw 更新后重新安装的重要提示
- 明确说明 `pip install -U copaw` 会覆盖 LCM 模块

### 用法

```bash
python install_lcm.py          # 智能检查 + 安装
python install_lcm.py --force  # 强制重新安装
python install_lcm.py --uninstall  # 卸载
```

---

## [0.11] - 2026-03-23

### 修复 (关键 Bug)

- **LCM Token 计数 Bug 修复** - `_count_messages_tokens()` 只计算 `text` 块，完全忽略 `tool_use`/`tool_result` 导致 token 计数严重低估，压缩永不触发
  - 修复位置: `copaw/agents/lcm/engine.py`
  - 现在完整计算所有消息块类型
  - 添加调试日志 `LCM token check: X tokens, threshold=Y`

### 问题诊断记录

本次修复基于完整的调试过程，发现问题链：

1. `max_input_length` 设置为 99999999999 → 压缩阈值计算错误
2. `reme` 包未安装 → `MemoryCompactionHook` 无法工作
3. `_count_messages_tokens` 只看 text 块 → token 计数严重低估

### 验证结果

- 集成测试: 全部通过 ✅
- 实际运行: 2026-03-23 成功验证
- 日志确认: `LCM token check: X tokens, threshold=70000`

---

## [0.10] - 2026-03-23

### 变更

- **恢复** MIGRATION.md 和 uninstall.py（部分用户仍在迁移中）

---

## [0.09] - 2026-03-23

### 新增

- **LCM 无损上下文管理模块**
  - SQLite 持久化所有消息（永不丢失）
  - DAG 多层摘要结构
  - FTS5 全文搜索（支持中文）
  - Agent 工具：`lcm_grep`, `lcm_describe`, `lcm_expand`
  - 阈值触发压缩（70% 时自动压缩）
- **install_lcm.py** 一键安装脚本

### 架构说明

| 组件 | 存储位置 | 用途 |
|------|----------|------|
| MemOS MCP | 云端 | 跨会话长期记忆 |
| LCM 模块 | 本地 SQLite | 会话内上下文管理 |

### 参考项目

- [lossless-claw](https://github.com/Martian-Engineering/lossless-claw) (3.2k stars)

---

## [0.08] - 2026-03-22

### 优化

- 默认配置优化
- 引导用户迁移到官方 MCP 方式

---

## [0.07] - 2026-03-22

### 变更

- 重构 README，区分新旧用户
- 明确本项目为非官方社区贡献

---

## [0.06] - 2026-03-22

### 修复

- 修复 install.py 中的路径问题

---

## [0.05] - 2026-03-22

### 新增

- 知识库支持

---

## [0.04] - 2026-03-22

### 新增

- 多模态记忆支持
- 工具记忆功能

---

## [0.03] - 2026-03-22

### 新增

- 用户偏好管理
- 自动记忆存储

---

## [0.02] - 2026-03-22

### 新增

- 自动记忆召回 (MemosRecallHook)

---

## [0.01] - 2026-03-22

### 新增

- 初始版本：MemOS Cloud 集成 for Copaw