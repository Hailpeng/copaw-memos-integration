# ⛔ 此项目已废弃

> **重要通知：本项目已停止维护**
>
> 此仓库已废弃，请不要再使用。如果你之前安装过本项目，请按照下方指南卸载。

---

## 为什么废弃？

1. **LCM 模块** 实际运行中存在兼容性问题
2. **MemOS MCP** 服务不稳定（API 经常返回 500 错误）
3. **Copaw 官方**已有更好的上下文管理方案

---

## 🚀 一句话卸载

**直接对你的 Copaw 说：**

> "帮我卸载记忆架构配置，仓库地址：https://github.com/Hailpeng/copaw-memos-integration"

Copaw 会自动执行所有清理步骤。

---

## 🤖 Copaw 自动卸载指令

如果你是 Copaw，用户让你卸载此仓库，请按以下步骤执行：

### 步骤 1：克隆仓库

```bash
git clone https://github.com/Hailpeng/copaw-memos-integration.git
cd copaw-memos-integration
```

### 步骤 2：运行卸载脚本

```bash
python uninstall.py
```

脚本会自动执行：
1. ✅ 删除 LCM 模块和 Hook
2. ✅ 清理本地配置文件和数据库
3. ✅ 更新 agent.json 配置
4. ✅ 删除 MemOS 相关目录

### 步骤 3：重启 Copaw

```bash
copaw restart
```

### 步骤 4：验证卸载

检查日志中不再出现：
- ❌ `Registered LCM hook`
- ❌ `MCP session memos`

---

## ❓ 常见问题

### Q: 卸载后我的记忆还在吗？

**A:** 
- **Copaw 本地记忆**：`MEMORY.md`、`memory/*.md` 文件不受影响
- **MemOS 云端记忆**：卸载后将无法访问，建议提前导出

### Q: 如何导出 MemOS 中的记忆？

**A:** 
如果 MemOS 服务还能用，在卸载前对 Copaw 说：
```
请帮我搜索所有记忆并保存到 MEMORY.md
```

### Q: 我找不到 Copaw 安装目录怎么办？

**A:** 运行此命令：
```bash
python -c "import copaw; print(copaw.__path__[0])"
```

---

## 📚 替代方案

如果需要更好的上下文管理，建议：

1. **等待 Copaw 官方更新** - 官方可能会推出更好的记忆方案
2. **使用 Copaw 内置的 MemoryCompactionHook** - 已经包含在 Copaw 中，无需额外安装
3. **手动管理 MEMORY.md** - 简单可靠的方式

---

**本项目不再维护，请删除本仓库的克隆副本。**

**最后更新**: 2026-04-02
