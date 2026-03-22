#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""LCM (Lossless Context Management) 安装脚本

将 LCM 模块安装到 Copaw 源码目录，实现无损上下文管理功能。

功能：
- SQLite 持久化所有消息（永不丢失）
- DAG 多层摘要结构
- FTS5 全文搜索
- Agent 工具：lcm_grep, lcm_describe, lcm_expand
"""
import os
import sys
import shutil
from pathlib import Path


def get_copaw_site_packages() -> Path:
    """获取 Copaw 的 site-packages 目录."""
    # 尝试常见的虚拟环境路径
    possible_paths = [
        Path.home() / ".copaw-env" / "lib" / "site-packages" / "copaw",
        Path("D:/PythonEnv/copaw-env/lib/site-packages/copaw"),
    ]
    
    # 也尝试从当前 Python 环境查找
    import copaw
    copaw_path = Path(copaw.__file__).parent
    if copaw_path.exists():
        return copaw_path
    
    for p in possible_paths:
        if p.exists():
            return p
    
    raise FileNotFoundError(
        "找不到 Copaw 安装目录。请确保 Copaw 已安装。"
    )


def install_lcm():
    """安装 LCM 模块到 Copaw."""
    print("=" * 60)
    print("LCM (Lossless Context Management) 安装程序")
    print("=" * 60)
    
    # 获取路径
    script_dir = Path(__file__).parent
    copaw_path = get_copaw_site_packages()
    
    print(f"\nCopaw 安装目录: {copaw_path}")
    
    # 目标路径
    lcm_src = script_dir / "lcm" / "agents" / "lcm"
    lcm_dst = copaw_path / "agents" / "lcm"
    hook_src = script_dir / "lcm" / "agents" / "hooks" / "lcm_hook.py"
    hook_dst = copaw_path / "agents" / "hooks" / "lcm_hook.py"
    
    # 备份原有文件
    backup_dir = copaw_path / "agents" / "lcm_backup"
    
    # 安装 LCM 模块
    print(f"\n[1/4] 安装 LCM 模块...")
    if lcm_dst.exists():
        print(f"  备份原有文件到: {backup_dir}")
        shutil.copytree(lcm_dst, backup_dir, dirs_exist_ok=True)
    
    lcm_dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(lcm_src, lcm_dst, dirs_exist_ok=True)
    print(f"  ✅ LCM 模块已安装到: {lcm_dst}")
    
    # 安装 Hook
    print(f"\n[2/4] 安装 LCM Hook...")
    hook_dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(hook_src, hook_dst)
    print(f"  ✅ LCM Hook 已安装到: {hook_dst}")
    
    # 更新 hooks/__init__.py
    print(f"\n[3/4] 更新 hooks/__init__.py...")
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
    print(f"\n[4/4] 配置 react_agent.py...")
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
    
    print("\n" + "=" * 60)
    print("✅ LCM 安装完成！")
    print("=" * 60)
    print("\n下一步：")
    print("1. 安装 reme 包: pip install reme==1.0.3")
    print("2. 重启 Copaw: copaw restart")
    print("3. 发送一条消息测试，日志应显示:")
    print("   'INFO: Registered LCM (Lossless Context Management) hook'")
    print("\n数据库位置: ~/.copaw/lcm.db")
    print("=" * 60)


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
    if len(sys.argv) > 1 and sys.argv[1] == "--uninstall":
        uninstall_lcm()
    else:
        install_lcm()