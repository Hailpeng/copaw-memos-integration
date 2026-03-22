#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
MemOS 硬编码集成卸载脚本

本脚本用于删除之前硬编码集成到 Copaw 源码中的 MemOS 相关代码。
运行后，请配置官方 MCP 方式。

官方文档: https://memos-docs.openmem.net/cn/mcp_agent/mcp/guide
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
        print("❌ 未找到 Copaw，请确认已安装")
        return None


def remove_file(filepath):
    """删除文件"""
    if filepath.exists():
        filepath.unlink()
        print(f"  ✅ 删除: {filepath}")
        return True
    return False


def restore_init_file(init_path, imports_to_remove, exports_to_remove):
    """恢复 __init__.py 文件"""
    if not init_path.exists():
        print(f"  ⚠️ 文件不存在: {init_path}")
        return False
    
    with open(init_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # 移除导入语句
    for imp in imports_to_remove:
        if imp in content:
            content = content.replace(imp + '\n', '')
            content = content.replace(imp, '')
    
    # 移除 __all__ 中的导出
    for exp in exports_to_remove:
        # 处理可能的格式
        content = content.replace(f'"{exp}", ', '')
        content = content.replace(f'"{exp}"', '')
        content = content.replace(f"'{exp}', ", '')
        content = content.replace(f"'{exp}'", '')
    
    if content != original_content:
        with open(init_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"  ✅ 恢复: {init_path}")
        return True
    else:
        print(f"  ℹ️ 无需修改: {init_path}")
        return False


def main():
    print("=" * 60)
    print("🗑️  MemOS 硬编码集成卸载脚本")
    print("=" * 60)
    print()
    
    # 获取 Copaw 路径
    copaw_path = get_copaw_path()
    if not copaw_path:
        sys.exit(1)
    
    print(f"📍 Copaw 路径: {copaw_path}")
    print()
    
    # 1. 删除 memos_recall.py
    print("📦 步骤 1: 删除 MemOS Hook 文件")
    hooks_dir = copaw_path / "agents" / "hooks"
    remove_file(hooks_dir / "memos_recall.py")
    
    # 2. 恢复 hooks/__init__.py
    print()
    print("📦 步骤 2: 恢复 hooks/__init__.py")
    restore_init_file(
        hooks_dir / "__init__.py",
        imports_to_remove=[
            "from .memos_recall import MemosRecallHook, MemosAddHook",
        ],
        exports_to_remove=[
            "MemosRecallHook",
            "MemosAddHook",
        ]
    )
    
    # 3. 删除 memory_search.py
    print()
    print("📦 步骤 3: 删除 memory_search.py")
    tools_dir = copaw_path / "agents" / "tools"
    remove_file(tools_dir / "memory_search.py")
    
    # 4. 恢复 tools/__init__.py
    print()
    print("📦 步骤 4: 恢复 tools/__init__.py")
    restore_init_file(
        tools_dir / "__init__.py",
        imports_to_remove=[
            "from .memory_search import (",
            "    create_memory_search_tool,",
            "    create_memory_add_tool,",
            "    create_memory_feedback_tool,",
            "    create_memory_get_tool,",
            "    create_memory_delete_tool,",
            "    create_task_status_tool,",
            "    create_knowledgebase_tools,",
            ")",
        ],
        exports_to_remove=[
            "create_memory_search_tool",
            "create_memory_add_tool",
            "create_memory_feedback_tool",
            "create_memory_get_tool",
            "create_memory_delete_tool",
            "create_task_status_tool",
            "create_knowledgebase_tools",
        ]
    )
    
    # 5. 恢复 memory_manager.py (移除 MemOSClient)
    print()
    print("📦 步骤 5: 恢复 memory/memory_manager.py")
    memory_manager_path = copaw_path / "agents" / "memory" / "memory_manager.py"
    if memory_manager_path.exists():
        print(f"  ℹ️ {memory_manager_path}")
        print(f"  ⚠️ 此文件可能包含 MemOSClient，建议重新安装 Copaw:")
        print(f"     pip install --force-reinstall copaw")
    
    # 6. 删除本地配置文件
    print()
    print("📦 步骤 6: 删除本地配置文件")
    workspace_dir = Path.home() / ".copaw" / "workspaces" / "default"
    
    dirs_to_remove = [
        workspace_dir / "active_skills" / "memos-cloud",
        workspace_dir / "customized_skills" / "memos-cloud",
        workspace_dir / "memos-backup",
        workspace_dir / "memos-integration",
        workspace_dir / "copaw-memos-integration",
        workspace_dir / "memos-integration-repo",
        workspace_dir / "release-repo",
    ]
    
    for d in dirs_to_remove:
        if d.exists():
            shutil.rmtree(d)
            print(f"  ✅ 删除目录: {d}")
    
    files_to_remove = [
        workspace_dir / "MEMOS_INTEGRATION_TASKS.md",
    ]
    
    for f in files_to_remove:
        remove_file(f)
    
    print()
    print("=" * 60)
    print("✅ 卸载完成！")
    print("=" * 60)
    print()
    print("📋 下一步：配置官方 MCP 方式")
    print()
    print("1. 编辑 ~/.copaw/workspaces/default/agent.json")
    print("2. 在 mcp.clients 中添加 memos 配置：")
    print()
    print('{')
    print('  "memos": {')
    print('    "name": "memos-api-mcp",')
    print('    "enabled": true,')
    print('    "transport": "stdio",')
    print('    "command": "npx",')
    print('    "args": ["-y", "@memtensor/memos-api-mcp@latest"],')
    print('    "env": {')
    print('      "MEMOS_API_KEY": "mpg-你的API密钥",')
    print('      "MEMOS_USER_ID": "你的用户标识",')
    print('      "MEMOS_CHANNEL": "MODELSCOPE"')
    print('    }')
    print('  }')
    print('}')
    print()
    print("3. 重启 Copaw: copaw restart")
    print()
    print("📖 官方文档: https://memos-docs.openmem.net/cn/mcp_agent/mcp/guide")
    print()


if __name__ == "__main__":
    main()