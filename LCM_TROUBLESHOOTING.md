# LCM 故障排除指南

本文档记录了 LCM (Lossless Context Management) 模块开发过程中遇到的问题及其解决方案。

## 问题 1: 上下文超限错误

### 症状

```
AGENT_UNKNOWN_ERROR
Unknown agent error: BadRequestError: Error code: 400 - {'error': {'code': 'invalid_parameter_error', 'message': '<400> InternalError.Algo.InvalidParameter: Range of input length should be [1, 202752]', 'param': None, 'type': 'invalid_request_error'}}
```

### 根本原因

**问题链：**

1. `max_input_length` 设置为 99999999999
   - 压缩阈值 = max_input_length × memory_compact_ratio
   - 当前配置 = 99999999999 × 0.75 ≈ 750亿 tokens
   - 实际 API 限制是 **202752 字符**

2. `reme` 包未安装
   - Copaw 的 `MemoryCompactionHook` 依赖 `reme` 包
   - `_REME_AVAILABLE = False` 导致压缩功能完全不可用

3. `_count_messages_tokens()` Bug
   - 只计算 `type == "text"` 的内容
   - 完全忽略 `tool_use` 和 `tool_result` 块
   - 导致 token 计数严重低估

### 解决方案

#### 步骤 1: 修复配置

修改 `agent.json`:

```json
{
  "running": {
    "max_input_length": 100000,
    "memory_compact_ratio": 0.7,
    "memory_reserve_ratio": 0.15
  }
}
```

#### 步骤 2: 安装依赖

```bash
pip install reme==1.0.3
```

#### 步骤 3: 修复 Token 计数 Bug

修改 `copaw/agents/lcm/engine.py` 中的 `_count_messages_tokens` 方法：

```python
async def _count_messages_tokens(self, messages: list[Msg]) -> int:
    total = 0
    for msg in messages:
        try:
            if isinstance(msg.content, str):
                text = msg.content
            elif isinstance(msg.content, list):
                text_parts = []
                for block in msg.content:
                    if isinstance(block, dict):
                        block_type = block.get("type", "")
                        if block_type == "text":
                            text_parts.append(block.get("text", ""))
                        elif block_type == "tool_use":
                            tool_name = block.get("name", "?")
                            tool_args = block.get("input", {})
                            args_str = str(tool_args)[:1000]
                            text_parts.append(f"[Tool: {tool_name}] {args_str}")
                        elif block_type == "tool_result":
                            result = block.get("content", "")
                            if len(result) > 2000:
                                result = result[:2000] + "...[truncated]"
                            text_parts.append(f"[ToolResult] {result}")
                text = " ".join(text_parts)
            # ... rest of the method
```

---

## 问题 2: LCM Hook 未注册

### 症状

日志中没有看到 `Registered LCM hook` 消息。

### 根本原因

`_enable_memory_manager` 为 False 或 `memory_manager` 为 None。

### 解决方案

确保 `agent.json` 中启用了 memory_manager：

```json
{
  "running": {
    // ... other config
  }
}
```

检查 `react_agent.py` 中的 `_register_hooks()` 方法是否正确调用 LCM hook。

---

## 问题 3: Token 计数返回 0 或异常低

### 症状

```
LCM token check: 500 tokens, threshold=70000
```

但实际对话明显更长。

### 根本原因

`_count_messages_tokens()` 只计算 `text` 块，忽略工具调用和结果。

### 解决方案

确保修复后的代码计算所有块类型（见问题 1 的步骤 3）。

---

## 验证方法

### 检查 LCM 日志

```bash
# 查看日志中的 LCM token check
findstr /i "LCM token check" copaw.log
```

正常输出应该类似：
```
LCM token check: 7159 tokens, threshold=70000, max=100000
```

### 检查数据库

```python
import sqlite3
conn = sqlite3.connect('~/.copaw/lcm.db')
c = conn.cursor()
c.execute('SELECT COUNT(*) FROM messages')
print(f'消息总数: {c.fetchone()[0]}')
c.execute('SELECT COUNT(*) FROM summaries')
print(f'摘要总数: {c.fetchone()[0]}')
```

### 检查 reme 包

```bash
python -c "from reme.reme_light import ReMeLight; print('OK')"
```

---

## 配置参考

| 参数 | 推荐值 | 说明 |
|------|--------|------|
| `max_input_length` | 100000 | 100K tokens 上限 |
| `memory_compact_ratio` | 0.7 | 70% 时触发压缩 |
| `memory_reserve_ratio` | 0.15 | 压缩时保留 15% |
| `fresh_tail_count` | 32 | 保护最近 32 条消息 |

---

## 恢复丢失的记忆

如果对话因为上下文超限而崩溃，可以从 LCM 数据库恢复：

```bash
python -c "
import sqlite3
conn = sqlite3.connect('~/.copaw/lcm.db')
c = conn.cursor()
c.execute('SELECT conversation_id, COUNT(*) FROM messages GROUP BY conversation_id ORDER BY COUNT(*) DESC')
for row in c.fetchall():
    print(f'{row[0]}: {row[1]} 条消息')
"
```

详见 `recovered_memories/` 目录下的恢复脚本。

---

## 相关文件

- `copaw/agents/lcm/engine.py` - LCM 主引擎
- `copaw/agents/lcm/database.py` - SQLite 持久化
- `copaw/agents/lcm/compactor.py` - DAG 压缩器
- `copaw/agents/hooks/lcm_hook.py` - Hook 集成

---

*最后更新: 2026-03-23*