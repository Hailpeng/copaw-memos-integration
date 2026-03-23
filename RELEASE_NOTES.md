# Release v0.12 - LCM 智能安装

## 一键安装

```bash
python install_lcm.py
```

**自动完成：**
- ✅ 检查当前安装状态
- ✅ 检测版本是否需要更新
- ✅ 只在必要时执行安装
- ✅ 显示详细状态信息

## 示例输出

**已是最新版本：**
```
LCM v0.12 安装程序
==============================
检测到已安装版本: v0.12
✅ LCM v0.12 已是最新版本，无需重新安装
```

**需要更新：**
```
检测到已安装版本: v0.11
⏫ 将从 v0.11 升级到 v0.12
[1/5] 安装 LCM 模块...
...
```

## 命令用法

```bash
python install_lcm.py          # 智能检查 + 安装
python install_lcm.py --force  # 强制重新安装
python install_lcm.py --uninstall  # 卸载
```

## ⚠️ Copaw 更新提示

`pip install -U copaw` 会覆盖 LCM，更新后请运行：

```bash
python install_lcm.py
copaw restart
```

## 包含 v0.11 的修复

- Token 计数 Bug 修复（完整计算所有消息块类型）
- 添加调试日志 `LCM token check: X tokens, threshold=Y`

---

**完整变更日志:** [CHANGELOG.md](CHANGELOG.md)