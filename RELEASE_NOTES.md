# Release v1.1.1 - 文档更新

## 📚 文档改进

### 新增 Copaw 更新后恢复流程

详细说明了 `pip install -U copaw` 后各组件的状态和恢复步骤：

| 组件 | 更新后状态 | 需要操作 |
|------|-----------|----------|
| **LCM 模块** | ❌ 会被覆盖 | 运行 `install_lcm.py` 重装 |
| **MCP 全局包** | ✅ 不受影响 | 无需操作 |
| **agent.json** | ⚠️ 可能重置 | 检查 MCP 配置 |
| **lcm.db 数据库** | ✅ 不受影响 | 数据保留 |

### 完整恢复流程

```bash
pip install -U copaw
cd copaw-memos-integration
python install_lcm.py
# 检查 agent.json 的 MCP 配置（Windows 需用全局路径）
copaw restart
```

---

## 历史版本

### v1.1.0 - Windows MCP 管道修复

**问题**：Windows 下每次对话 MCP 会话中断（WinError 233）
**解决**：全局安装 MCP 包 + 配置使用全局命令路径

详见：https://github.com/Hailpeng/copaw-memos-integration/releases/tag/v1.1.0

---

**完整文档**：见 [README.md](README.md)