# Release v0.14.2 - LCM 压缩 Bug 修复

## 修复

- **LCM 压缩执行失败** - `compactor.py` 中 `Msg` 对象不支持 `id` 参数
  - 错误：`TypeError: Msg.__init__() got an unexpected keyword argument 'id'`
  - 修复：移除 `id=summary["id"]` 参数
  - 影响：压缩触发后无法生成摘要，导致上下文持续增长

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

## 升级指南

### 方法 1: 重新安装（推荐）

```bash
cd D:\PythonEnv\copaw-memos-integration
git pull origin main
python install_lcm.py
```

### 方法 2: 手动替换

仅替换修复的文件：

```bash
copy lcm\agents\lcm\compactor.py D:\PythonEnv\copaw-env\lib\site-packages\copaw\agents\lcm\compactor.py
```

然后重启 Copaw：

```bash
copaw restart
```

## 相关 Issue

- LCM 压缩在阈值触发后无法执行
- 上下文持续增长导致 API 报错 `Range of input length should be [1, 202752]`

---

**完整更新日志**: [CHANGELOG.md](CHANGELOG.md)