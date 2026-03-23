# Release v0.12 - LCM 版本检查 + Copaw 更新重装提示

## 新增功能 ✨

### LCM 版本检查

```bash
# 检查安装状态
python install_lcm.py --check

# 强制重新安装
python install_lcm.py --force
```

输出示例：
```
✅ LCM 模块: D:\PythonEnv\copaw-env\lib\site-packages\copaw\agents\lcm
✅ LCM Hook: .../lcm_hook.py
✅ reme 依赖: 已安装
已安装版本: v0.12
✅ LCM 安装完整，可以正常使用
```

## 重要提示 ⚠️

### Copaw 更新后需要重新安装 LCM

`pip install -U copaw` 会覆盖 LCM 模块！更新后请运行：

```bash
cd copaw-memos-integration
python install_lcm.py
copaw restart
```

## 包含 v0.11 的修复

- Token 计数 Bug 修复（完整计算所有消息块类型）
- 添加调试日志 `LCM token check: X tokens, threshold=Y`

## 文件变更

- `install_lcm.py` - 版本检查功能
- `README.md` - Copaw 更新提示
- `lcm/agents/lcm/engine.py` - Token 计数修复

---

**完整变更日志:** 查看 [CHANGELOG.md](CHANGELOG.md)