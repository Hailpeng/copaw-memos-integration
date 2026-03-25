# Release v1.2.0 - LCM 字符级早期检测

## 问题

用户粘贴大量文本（如完整日志输出）时，即使 LCM 配置正确，仍会触发 API 输入限制错误：

```
Range of input length should be [1, 202752]
```

## 根因

Token 计数需要遍历所有消息并调用 tokenizer，速度较慢。在大段文本场景下，计数完成前就已经超限。

## 修复

### 字符级早期检测

在 token 计数前增加快速字符扫描：

```python
# FAST PATH: 字符扫描（快速，提前退出）
for m in messages:
    char_len += len(content)
    if char_len > max_chars:  # 202752
        return await self._do_compaction(...)  # 立即触发压缩

# SLOW PATH: Token 计数（仅在字符未超限时执行）
total_tokens = await self._count_messages_tokens(messages)
```

### 内容截断优化

`_blocks_to_text` 方法增强：

- 添加 `truncate` 参数，默认截断长内容
- `MAX_TEXT_BLOCK_CHARS = 4000` - 文本块最大字符数
- `MAX_TOOL_RESULT_CHARS = 2000` - 工具结果最大字符数
- 防止单个超大内容影响整体处理

### 配置修正

- `max_input_chars` 移到 dataclass 正确位置
- 确保属性可以被正确访问

## 文件变更

| 文件 | 变更 |
|------|------|
| `lcm/agents/lcm/engine.py` | 字符级早期检测 + 内容截断 |
| `lcm/agents/lcm/config.py` | 配置字段位置修正 |

## 安装/升级

```bash
# 如果已安装，更新代码后重启 Copaw
git pull
copaw restart

# 新安装
git clone https://github.com/Hailpeng/copaw-memos-integration.git
cd copaw-memos-integration
python install_lcm.py
pip install reme==1.0.3
copaw restart
```

## 验证

修改后，当用户粘贴大段文本时，日志应显示：

```
LCM: Character limit exceeded during scan: 300000 > 202752, forcing compression (skipped token counting)
```

而不是之前的 API 错误。