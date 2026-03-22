## 🐛 Bug Fixes

- **修复 `subprocess` 导入缺失**: `restore_memos.py` 中的 `get_copaw_path()` 函数使用了 `subprocess.run()`，但缺少 `import subprocess`，导致运行时报错 `NameError: name 'subprocess' is not defined`