# Release v0.14.2 - LCM 压缩 Bug 修复

## 修复

- **LCM 压缩执行失败** - `compactor.py` 中 `Msg` 对象不支持 `id` 参数
  - 错误：`TypeError: Msg.__init__() got an unexpected keyword argument 'id'`
  - 修复：移除 `id=summary["id"]` 参数
  - 影响：压缩触发后无法生成摘要，导致上下文持续增长

## 改进

- **同步运行环境修复到仓库** - 确保用户安装后功能正常
  - `config.py`: 添加 `max_input_chars` 字段用于强制压缩
  - `lcm_hook.py`: 添加 `model_id_for_tokenizer` 支持 tokenizer 选择

- **README 新增 Copaw 自动安装指令** - Copaw 可直接按步骤执行安装

## 安装方式

用户对 Copaw 说：

> "帮我配置完整的记忆架构，仓库地址：https://github.com/Hailpeng/copaw-memos-integration"

Copaw 将自动执行：
1. 克隆仓库
2. 安装 reme 依赖
3. 运行安装脚本
4. 配置环境变量
5. 重启 Copaw

## 技术细节

### 问题

`compactor.py` 第 128 行创建摘要消息时：

```python
# 问题代码
summary_msg = Msg(
    name="system",
    role="system",
    content=[TextBlock(type="text", text=f"[Context Summary]\n{summary['content']}")],
    id=summary["id"],  # ❌ Msg 类不支持此参数
)
```

AgentScope 的 `Msg` 类不支持 `id` 参数，导致压缩执行时抛出 TypeError。

### 修复

```python
# 修复后
summary_msg = Msg(
    name="system",
    role="system",
    content=[TextBlock(type="text", text=f"[Context Summary]\n{summary['content']}")],
    # Note: Msg doesn't accept 'id' parameter
)
```

摘要 ID 仅存储在 SQLite 数据库中，不需要在 Msg 对象中携带。

## 验证结果

| 项目 | 状态 |
|------|------|
| 压缩触发 | ✅ 71,191 tokens >= 70,000 threshold |
| 压缩执行 | ✅ 100 -> 33 messages |
| Summaries 存储 | ✅ 2 条写入数据库 |

---

**完整更新日志**: [CHANGELOG.md](CHANGELOG.md)