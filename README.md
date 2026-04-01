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

## 📝 卸载指南

如果你之前安装过本项目，请按以下步骤清理：

### 方式一：使用自动卸载脚本（推荐）

```bash
git clone https://github.com/Hailpeng/copaw-memos-integration.git
cd copaw-memos-integration
python uninstall.py
```

脚本会自动执行：
1. ✅ 删除 LCM 模块和 Hook
2. ✅ 清理本地配置文件和数据库
3. ✅ 更新 agent.json 配置
4. ✅ 删除 MemOS 相关目录

### 方式二：手动卸载

如果自动脚本无法使用，请按以下步骤手动清理：

#### 第一步：保存你的记忆

**⚠️ 重要：卸载前请先保存你在 MemOS 中的记忆！**

由于 MemOS 服务可能不稳定，建议你：

1. 在 Copaw 中运行此命令，尝试导出记忆：
   ```
   请帮我搜索所有记忆并保存到 MEMORY.md
   ```

2. 如果 MemOS 服务无法访问，你的记忆可能已经丢失
3. 卸载后 MemOS 云端记忆将无法恢复

#### 第二步：删除 LCM 相关文件

**Windows 用户：**
```cmd
del C:\Users\你的用户名\.copaw\lcm.db
del C:\Users\你的用户名\.copaw\check_lcm_data.py
del C:\Users\你的用户名\.copaw\recover_lcm_memories.py
del C:\Users\你的用户名\.copaw\workspaces\default\check_lcm*.py
del C:\Users\你的用户名\.copaw\workspaces\default\test_lcm*.py
del C:\Users\你的用户名\.copaw\workspaces\default\LCM_DESIGN.md
```

**Linux/macOS：**
```bash
rm ~/.copaw/lcm.db
rm ~/.copaw/check_lcm_data.py
rm ~/.copaw/recover_lcm_memories.py
rm ~/.copaw/workspaces/default/check_lcm*.py
rm ~/.copaw/workspaces/default/test_lcm*.py
rm ~/.copaw/workspaces/default/LCM_DESIGN.md
```

#### 第三步：删除 LCM 模块（Copaw 源码）

**找到你的 Copaw 安装目录：**
```bash
python -c "import copaw; print(copaw.__path__[0])"
```

**然后删除：**

**Windows（示例路径）：**
```cmd
rmdir /s /q "D:\PythonEnv\copaw-env\lib\site-packages\copaw\agents\lcm"
del "D:\PythonEnv\copaw-env\lib\site-packages\copaw\agents\hooks\lcm_hook.py"
del "D:\PythonEnv\copaw-env\lib\site-packages\copaw\agents\hooks\lcm_hook.py.bak"
```

**Linux/macOS：**
```bash
rm -rf ~/.copaw-env/lib/site-packages/copaw/agents/lcm
rm ~/.copaw-env/lib/site-packages/copaw/agents/hooks/lcm_hook.py
rm ~/.copaw-env/lib/site-packages/copaw/agents/hooks/lcm_hook.py.bak
```

#### 第四步：卸载 MemOS MCP

1. **从 agent.json 中删除 MemOS 配置**

   编辑 `~/.copaw/workspaces/default/agent.json`，删除 `mcp.clients.memos` 部分：
   ```json
   {
     "mcp": {
       "clients": {}
     }
   }
   ```

2. **删除 system_prompt_files 中的 LCM_DESIGN.md**

   ```json
   {
     "system_prompt_files": [
       "AGENTS.md",
       "SOUL.md",
       "PROFILE.md",
       "MEMORY.md",
       "HEARTBEAT.md"
     ]
   }
   ```

3. **恢复默认的 running 配置**（可选）

   ```json
   {
     "running": {
       "max_input_length": 80000,
       "memory_compact_ratio": 0.8,
       "memory_reserve_ratio": 0.2
     }
   }
   ```

4. **卸载全局 npm 包**（可选）

   ```bash
   npm uninstall -g @memtensor/memos-api-mcp
   ```

#### 第五步：重启 Copaw

```bash
copaw restart
```

#### 第六步：验证卸载

检查日志中不再出现：
- ❌ `Registered LCM hook`
- ❌ `MCP session memos`

---

## ❓ 常见问题

### Q: 卸载后我的记忆还在吗？

**A:** 
- **Copaw 本地记忆**：`MEMORY.md`、`memory/*.md` 文件不受影响
- **MemOS 云端记忆**：卸载后将无法访问，建议提前导出

### Q: 我找不到 Copaw 安装目录怎么办？

**A:** 运行此命令：
```bash
python -c "import copaw; print(copaw.__path__[0])"
```

### Q: agent.json 格式错误怎么办？

**A:** 
- JSON 不允许注释（`//`），请删除所有注释
- 使用在线 JSON 验证器检查格式

---

## 📚 替代方案

如果需要更好的上下文管理，建议：

1. **等待 Copaw 官方更新** - 官方可能会推出更好的记忆方案
2. **使用 Copaw 内置的 MemoryCompactionHook** - 已经包含在 Copaw 中，无需额外安装
3. **手动管理 MEMORY.md** - 简单可靠的方式

---

**本项目不再维护，请删除本仓库的克隆副本。**

**最后更新**: 2026-04-02
