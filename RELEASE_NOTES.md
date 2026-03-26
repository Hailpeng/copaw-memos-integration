# Release v1.4.0 - Copaw 更新检测

## 🆕 新功能

### 自动版本变化检测

现在 LCM 会在启动时自动检测 Copaw 是否已更新，提醒用户重新安装。

**效果**：
```
⚠️ Copaw version changed: 0.1.0.post1 → 0.1.0.post2
   LCM modules may have been overwritten.
   Please reinstall:
   cd copaw-memos-integration && python install_lcm.py
```

### 工作原理

1. **安装时**：记录当前 Copaw 版本到 `~/.copaw/lcm_installed_version.json`
2. **启动时**：检查当前 Copaw 版本是否与记录一致
3. **变化时**：打印警告，提醒用户重新安装

## 📥 安装/升级

```bash
git clone https://github.com/Hailpeng/copaw-memos-integration.git
cd copaw-memos-integration
python install_lcm.py
pip install reme==1.0.3
copaw restart
```

## 📋 完整更新日志

参见 [CHANGELOG.md](./CHANGELOG.md)