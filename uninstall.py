#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Copaw 记忆架构卸载脚本

本脚本用于完全卸载本项目安装的所有组件：
1. MemOS MCP 配置
2. LCM 模块和数据库
3. 相关脚本和配置文件

运行后，Copaw 将恢复到原始状态。
"""

import os
import sys
import shutil
from pathlib import Path


def get_copaw_path():
    """获取 Copaw 安装路径"""
    try:
        import copaw
        return Path(copaw.__path__[0])
    except ImportError:
        print("[X] 未找到 Copaw，请确认已安装")
        return None


def remove_file(filepath, show_msg=True):
    """删除文件"""
    if filepath.exists():
        filepath.unlink()
        if show_msg:
            print(f"  [OK] 删除: {filepath}")
        return True
    return False


def remove_dir(dirpath, show_msg=True):
    """删除目录"""
    if dirpath.exists():
        shutil.rmtree(dirpath)
        if show_msg:
            print(f"  [OK] 删除目录: {dirpath}")
        return True
    return False


def update_agent_json():
    """更新 agent.json 配置"""
    import json
    
    agent_json_path = Path.home() / ".copaw" / "workspaces" / "default" / "agent.json"
    
    if not agent_json_path.exists():
        print(f"  [!] 文件不存在: {agent_json_path}")
        return
    
    try:
        with open(agent_json_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        modified = False
        
        # 1. 删除 MCP memos 配置
        if 'mcp' in config and 'clients' in config.get('mcp', {}):
            if 'memos' in config['mcp']['clients']:
                del config['mcp']['clients']['memos']
                print("  [OK] 删除 MCP memos 配置")
                modified = True
        
        # 2. 从 system_prompt_files 中删除 LCM_DESIGN.md
        if 'system_prompt_files' in config:
            if 'LCM_DESIGN.md' in config['system_prompt_files']:
                config['system_prompt_files'].remove('LCM_DESIGN.md')
                print("  [OK] 从 system_prompt_files 删除 LCM_DESIGN.md")
                modified = True
        
        # 3. 恢复 running 配置为默认值
        if 'running' in config:
            defaults = {
                'max_input_length': 80000,
                'memory_compact_ratio': 0.8,
                'memory_reserve_ratio': 0.2
            }
            
            for key, value in defaults.items():
                if key in config['running']:
                    config['running'][key] = value
                    modified = True
                    print(f"  [OK] 恢复 {key} = {value}")
        
        if modified:
            with open(agent_json_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            print(f"  [OK] 更新配置: {agent_json_path}")
        else:
            print(f"  [i] 配置无需修改")
    
    except Exception as e:
        print(f"  [X] 更新配置失败: {e}")


def uninstall_lcm(copaw_path):
    """卸载 LCM 模块"""
    print()
    print("=" * 60)
    print("[*] 卸载 LCM 模块")
    print("=" * 60)
    
    # 1. 删除 LCM 模块目录
    lcm_dir = copaw_path / "agents" / "lcm"
    if remove_dir(lcm_dir):
        print("  [OK] 删除 LCM 模块目录")
    
    # 2. 删除 LCM Hook
    lcm_hook = copaw_path / "agents" / "hooks" / "lcm_hook.py"
    remove_file(lcm_hook)
    
    # 3. 删除 LCM Hook 备份
    lcm_hook_bak = copaw_path / "agents" / "hooks" / "lcm_hook.py.bak"
    remove_file(lcm_hook_bak)
    
    # 4. 删除 __pycache__ 中的编译文件
    pycache = copaw_path / "agents" / "hooks" / "__pycache__"
    if pycache.exists():
        for f in pycache.glob("*lcm*"):
            remove_file(f)
    
    print("  [OK] LCM 模块卸载完成")


def uninstall_memos():
    """卸载 MemOS 相关文件"""
    print()
    print("=" * 60)
    print("[*] 卸载 MemOS 相关文件")
    print("=" * 60)
    
    workspace_dir = Path.home() / ".copaw" / "workspaces" / "default"
    
    # 删除 MemOS 相关目录
    dirs_to_remove = [
        workspace_dir / "active_skills" / "memos-cloud",
        workspace_dir / "customized_skills" / "memos-cloud",
        workspace_dir / "memos-backup",
        workspace_dir / "memos-integration",
        workspace_dir / "copaw-memos-integration",
    ]
    
    for d in dirs_to_remove:
        remove_dir(d)
    
    print("  [OK] MemOS 文件清理完成")


def clean_local_files():
    """清理本地配置文件"""
    print()
    print("=" * 60)
    print("[*] 清理本地配置文件")
    print("=" * 60)
    
    # 删除工作区根目录的文件
    copaw_root = Path.home() / ".copaw"
    files_to_remove = [
        copaw_root / "lcm.db",
        copaw_root / "lcm_installed_version.json",
        copaw_root / "memory_lancedb_readme.md",
        copaw_root / "check_lcm_data.py",
        copaw_root / "recover_lcm_memories.py",
    ]
    
    for f in files_to_remove:
        remove_file(f)
    
    # 删除工作区中的测试脚本
    workspace_dir = Path.home() / ".copaw" / "workspaces" / "default"
    test_scripts = [
        "check_lcm.py",
        "check_lcm_deps.py",
        "check_lcm_detail.py",
        "test_lcm.py",
        "test_lcm_compress.py",
        "LCM_DESIGN.md",
    ]
    
    for script in test_scripts:
        remove_file(workspace_dir / script)
    
    # 删除 memory 目录中的 LCM 相关文件
    memory_dir = Path.home() / ".copaw" / "memory"
    if memory_dir.exists():
        for f in memory_dir.glob("*lcm*"):
            remove_file(f)
    
    print("  [OK] 本地文件清理完成")


def main():
    print("=" * 60)
    print("[DELETE] Copaw 记忆架构卸载脚本 v3.0")
    print("=" * 60)
    print()
    print("[!] 此脚本将卸载以下组件：")
    print("  - LCM 模块 (本地上下文管理)")
    print("  - MemOS 配置 (云端记忆)")
    print("  - 所有相关配置文件和数据库")
    print()
    
    confirm = input("确定要继续吗？(y/N): ").strip().lower()
    if confirm != 'y':
        print("[i] 已取消卸载")
        return
    
    print()
    
    # 获取 Copaw 路径
    copaw_path = get_copaw_path()
    if not copaw_path:
        sys.exit(1)
    
    print(f"[-] Copaw 路径: {copaw_path}")
    
    # 执行卸载步骤
    uninstall_lcm(copaw_path)
    uninstall_memos()
    clean_local_files()
    
    # 更新 agent.json
    print()
    print("=" * 60)
    print("[*] 更新 agent.json 配置")
    print("=" * 60)
    update_agent_json()
    
    # 完成
    print()
    print("=" * 60)
    print("[OK] 卸载完成！")
    print("=" * 60)
    print()
    print("[!] 下一步操作：")
    print("  1. 重启 Copaw: copaw restart")
    print("  2. 验证日志中不再出现 LCM 或 MCP 相关信息")
    print()
    print("[?] 如需恢复 Copaw 官方上下文管理，无需额外配置")
    print("    Copaw 内置的 MemoryCompactionHook 会自动生效")
    print()


if __name__ == "__main__":
    main()
