#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""LCM (Lossless Context Management) 安装脚本

将 LCM 模块安装到 Copaw 源码目录，实现无损上下文管理功能。

功能：
- SQLite 持久化所有消息（永不丢失）
- DAG 多层摘要结构
- FTS5 全文搜索
- Agent 工具：lcm_grep, lcm_describe, lcm_expand

⚠️ 重要提示：
- Copaw 更新（pip install -U copaw）会覆盖 LCM 模块
- 更新后请重新运行此脚本：python install_lcm.py
- 或使用 --check 检查是否需要重新安装
"""
import os
import sys
import shutil
from pathlib import Path

# LCM 版本号 - 与 CHANGELOG.md 保持同步
LCM_VERSION = "0.11"
LCM_VERSION_FILE = "lcm_version.txt"


def get_copaw_site_packages() -> Path:
    """获取 Copaw 的 site-packages 目录."""
    # 尝试常见的虚拟环境路径
    possible_paths = [
        Path.home() / ".copaw-env" / "lib" / "site-packages" / "copaw",
        Path("D:/PythonEnv/copaw-env/lib/site-packages/copaw"),
    ]
    
    # 也尝试从当前 Python 环境查找
    try:
        import copaw
        copaw_path = Path(copaw.__file__).parent
        if copaw_path.exists():
            return copaw_path
    except ImportError:
        pass
    
    for p in possible_paths:
        if p.exists():
            return p
    
    raise FileNotFoundError(
        "找不到 Copaw 安装目录。请确保 Copaw 已安装。"
    )


def get_installed_version(copaw_path: Path) -> str:
    """获取已安装的 LCM 版本."""
    version_file = copaw_path / "agents" / "lcm" / LCM_VERSION_FILE
    if version_file.exists():
        return version_file.read_text(encoding="utf-8").strip()
    return "0.0"


def check_lcm_installed(copaw_path: Path) -> bool:
    """检查 LCM 是否已安装."""
    lcm_dir = copaw_path / "agents" / "lcm"
    hook_file = copaw_path / "agents" / "hooks" / "lcm_hook.py"
    return lcm_dir.exists() and hook_file.exists()


def install_lcm():
    """安装 LCM 模块到 Copaw."""
    print("=" * 60)
    print(f"LCM v{LCM_VERSION} (Lossless Context Management) 安装程序")
    print("=" * 60)
    
    # 获取路径
    script_dir = Path(__file__).parent
    copaw_path = get_copaw_site_packages()
    
    print(f"\nCopaw 安装目录: {copaw_path}")
    
    # 检查是否已安装
    if check_lcm_installed(copaw_path):
        installed_version = get_installed_version(copaw_path)
        print(f"\n检测到已安装版本: v{installed_version}")
        
        if installed_version == LCM_VERSION:
            print(f"✅ LCM v{LCM_VERSION} 已是最新版本，无需重新安装")
            print("\n如需强制重新安装，请使用: python install_lcm.py --force")
            return
        else:
            print(f"⏫ 将从 v{installed_version} 升级到 v{LCM_VERSION}")
    
    # 目标路径
    lcm_src = script_dir / "lcm" / "agents" / "lcm"
    lcm_dst = copaw_path / "agents" / "lcm"
    hook_src = script_dir / "lcm" / "agents" / "hooks" / "lcm_hook.py"
    hook_dst = copaw_path / "agents" / "hooks" / "lcm_hook.py"
    
    # 备份原有文件
    backup_dir = copaw_path / "agents" / "lcm_backup"
    
    # 安装 LCM 模块
    print(f"\n[1/5] 安装 LCM 模块...")
    if lcm_dst.exists():
        print(f"  备份原有文件到: {backup_dir}")
        shutil.copytree(lcm_dst, backup_dir, dirs_exist_ok=True)
        shutil.rmtree(lcm_dst)
    
    lcm_dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(lcm_src, lcm_dst, dirs_exist_ok=True)
    
    # 写入版本文件
    version_file = lcm_dst / LCM_VERSION_FILE
    version_file.write_text(LCM_VERSION, encoding="utf-8")
    
    print(f"  ✅ LCM 模块已安装到: {lcm_dst}")
    
    # 安装 Hook
    print(f"\n[2/5] 安装 LCM Hook...")
    hook_dst.parent.mkdir(parents=True, exist_ok=True)
    if hook_dst.exists():
        hook_dst.unlink()
    shutil.copy2(hook_src, hook_dst)
    print(f"  ✅ LCM Hook 已安装到: {hook_dst}")
    
    # 更新 hooks/__init__.py
    print(f"\n[3/5] 更新 hooks/__init__.py...")
    hooks_init = copaw_path / "agents" / "hooks" / "__init__.py"
    
    if hooks_init.exists():
        content = hooks_init.read_text(encoding="utf-8")
        
        if "LCMHook" not in content:
            # 添加 LCMHook 导入
            new_import = "from .lcm_hook import LCMHook\n"
            new_export = '    "LCMHook",\n'
            
            # 找到导入位置
            if "from .memory_compaction import" in content:
                content = content.replace(
                    "from .memory_compaction import MemoryCompactionHook",
                    "from .memory_compaction import MemoryCompactionHook\n" + new_import
                )
            else:
                # 在文件开头添加导入
                content = new_import + content
            
            # 添加到 __all__
            if "__all__" in content:
                content = content.replace(
                    '"MemoryCompactionHook",\n]',
                    '"MemoryCompactionHook",\n' + new_export + "]"
                )
            
            hooks_init.write_text(content, encoding="utf-8")
            print(f"  ✅ 已更新: {hooks_init}")
        else:
            print(f"  ⏭️ LCMHook 已存在于 __init__.py")
    
    # 修改 react_agent.py 以启用 LCM
    print(f"\n[4/5] 配置 react_agent.py...")
    react_agent = copaw_path / "agents" / "react_agent.py"
    
    if react_agent.exists():
        content = react_agent.read_text(encoding="utf-8")
        
        # 检查是否已经配置
        if "Registered LCM (Lossless Context Management) hook" in content:
            print(f"  ⏭️ LCM 已在 react_agent.py 中配置")
        else:
            # 找到 bootstrap hook 注册后的位置
            marker = 'logger.info("Registered bootstrap hook")'
            if marker in content:
                lcm_code = '''

        # LCM (Lossless Context Management) hook - DAG-based compression
        # Replaces the old MemoryCompactionHook with better compression
        if self._enable_memory_manager and self.memory_manager is not None:
            from .hooks import LCMHook
            lcm_hook = LCMHook(
                memory_manager=self.memory_manager,
            )
            self.register_instance_hook(
                hook_type="pre_reasoning",
                hook_name="lcm_hook",
                hook=lcm_hook.__call__,
            )
            logger.info("Registered LCM (Lossless Context Management) hook")
        else:
            logger.info(f"LCM hook not registered: enable_memory_manager={self._enable_memory_manager}, memory_manager={self.memory_manager is not None}")
'''
                content = content.replace(marker, marker + lcm_code)
                react_agent.write_text(content, encoding="utf-8")
                print(f"  ✅ 已配置: {react_agent}")
            else:
                print(f"  ⚠️ 无法找到插入位置，请手动配置")
    
    # 安装 reme 依赖
    print(f"\n[5/5] 检查 reme 依赖...")
    try:
        import reme
        print(f"  ✅ reme 已安装")
    except ImportError:
        print(f"  ⚠️ reme 未安装，正在安装...")
        os.system("pip install reme==1.0.3")
    
    print("\n" + "=" * 60)
    print(f"✅ LCM v{LCM_VERSION} 安装完成！")
    print("=" * 60)
    print("\n下一步：")
    print("1. 重启 Copaw: copaw restart")
    print("2. 发送一条消息测试，日志应显示:")
    print("   'INFO: Registered LCM (Lossless Context Management) hook'")
    print("   'INFO: LCM token check: X tokens, threshold=70000'")
    print("\n数据库位置: ~/.copaw/lcm.db")
    print("\n⚠️ 注意：Copaw 更新后需要重新运行此脚本")
    print("=" * 60)


def check_installation():
    """检查 LCM 安装状态."""
    print("=" * 60)
    print("LCM 安装状态检查")
    print("=" * 60)
    
    try:
        copaw_path = get_copaw_site_packages()
        print(f"\nCopaw 安装目录: {copaw_path}")
    except FileNotFoundError as e:
        print(f"\n❌ {e}")
        return
    
    # 检查各个组件
    checks = [
        ("LCM 模块", copaw_path / "agents" / "lcm"),
        ("LCM Hook", copaw_path / "agents" / "hooks" / "lcm_hook.py"),
        ("reme 依赖", None),  # 特殊处理
    ]
    
    all_ok = True
    for name, path in checks:
        if name == "reme 依赖":
            try:
                import reme
                print(f"✅ {name}: 已安装")
            except ImportError:
                print(f"❌ {name}: 未安装 (pip install reme==1.0.3)")
                all_ok = False
        elif path and path.exists():
            print(f"✅ {name}: {path}")
        else:
            print(f"❌ {name}: 未安装")
            all_ok = False
    
    # 版本检查
    if check_lcm_installed(copaw_path):
        installed_version = get_installed_version(copaw_path)
        print(f"\n已安装版本: v{installed_version}")
        print(f"最新版本: v{LCM_VERSION}")
        
        if installed_version != LCM_VERSION:
            print(f"⚠️ 需要更新！请运行: python install_lcm.py")
            all_ok = False
    
    if all_ok:
        print("\n✅ LCM 安装完整，可以正常使用")
    else:
        print("\n❌ LCM 安装不完整，请运行: python install_lcm.py")


def uninstall_lcm():
    """卸载 LCM 模块."""
    print("=" * 60)
    print("LCM 卸载程序")
    print("=" * 60)
    
    copaw_path = get_copaw_site_packages()
    
    # 删除 LCM 模块
    lcm_dst = copaw_path / "agents" / "lcm"
    if lcm_dst.exists():
        shutil.rmtree(lcm_dst)
        print(f"✅ 已删除: {lcm_dst}")
    
    # 删除 Hook
    hook_dst = copaw_path / "agents" / "hooks" / "lcm_hook.py"
    if hook_dst.exists():
        hook_dst.unlink()
        print(f"✅ 已删除: {hook_dst}")
    
    # 恢复备份
    backup_dir = copaw_path / "agents" / "lcm_backup"
    if backup_dir.exists():
        shutil.copytree(backup_dir, lcm_dst, dirs_exist_ok=True)
        shutil.rmtree(backup_dir)
        print(f"✅ 已从备份恢复")
    
    print("\n✅ LCM 已卸载")
    print("请重启 Copaw: copaw restart")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg == "--uninstall":
            uninstall_lcm()
        elif arg == "--check":
            check_installation()
        elif arg == "--force":
            # 强制重新安装
            copaw_path = get_copaw_site_packages()
            lcm_dst = copaw_path / "agents" / "lcm"
            if lcm_dst.exists():
                shutil.rmtree(lcm_dst)
            install_lcm()
        else:
            print(f"未知参数: {arg}")
            print("用法:")
            print("  python install_lcm.py          # 安装/更新 LCM")
            print("  python install_lcm.py --check  # 检查安装状态")
            print("  python install_lcm.py --force  # 强制重新安装")
            print("  python install_lcm.py --uninstall  # 卸载 LCM")
    else:
        install_lcm()