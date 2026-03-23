# Release v0.11 - LCM Token 计数关键 Bug 修复

## 关键修复 🐛

### Token 计数 Bug（严重）

**问题：** `_count_messages_tokens()` 只计算 `text` 块，完全忽略 `tool_use`/`tool_result`，导致 token 计数严重低估，压缩永不触发。

**影响：** 长对话中上下文不断累积，最终超出 API 限制（202752 字符），导致对话崩溃。

**修复：** 现在完整计算所有消息块类型，并添加调试日志。

## 问题诊断记录

本次修复基于完整的调试过程，发现问题链：

| 问题 | 原因 | 影响 |
|------|------|------|
| `max_input_length` = 99999999999 | 阈值计算错误 | 压缩永不触发 |
| `reme` 包未安装 | 依赖缺失 | MemoryCompactionHook 不工作 |
| Token 计数只看 text | 代码 Bug | 计数严重低估 |

## 验证结果

- ✅ 集成测试全部通过
- ✅ 实际运行成功验证
- ✅ 日志确认: `LCM token check: X tokens, threshold=70000`

## 新增文档

- `LCM_TROUBLESHOOTING.md` - 完整的故障排除指南

## 升级建议

如果你使用 LCM 模块，强烈建议升级到此版本。

```bash
pip install reme==1.0.3
# 然后重启 Copaw
```

## 文件变更

- `CHANGELOG.md` - 更新日志
- `LCM_TROUBLESHOOTING.md` - 新增故障排除指南

---

**完整变更日志:** 查看 [CHANGELOG.md](CHANGELOG.md)