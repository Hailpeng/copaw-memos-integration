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
import re
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


def clean_file_content(filepath, patterns_to_remove, description=""):
    """清理文件中的特定内容"""
    if not filepath.exists():
        print(f"  ⚠️ 文件不存在: {filepath}")
        return False
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    for pattern in patterns_to_remove:
        if isinstance(pattern, str):
            if pattern in content:
                content = content.replace(pattern, '')
        else:  # regex
            content = re.sub(pattern, '', content, flags=re.DOTALL)
    
    if content != original_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"  ✅ 清理: {filepath} {description}")
        return True
    else:
        print(f"  ℹ️ 无需修改: {filepath} {description}")
        return False


def clean_memory_manager(copaw_path):
    """清理 memory_manager.py 中的 MemOS 相关代码"""
    filepath = copaw_path / "agents" / "memory" / "memory_manager.py"
    
    if not filepath.exists():
        print(f"  ⚠️ 文件不存在: {filepath}")
        return
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # 1. 删除 MemOSClient 类定义
    # 找到 class MemOSClient: 到下一个 class 或文件末尾
    pattern = r'class MemOSClient:.*?(?=\nclass |\Z)'
    content = re.sub(pattern, '', content, flags=re.DOTALL)
    
    # 2. 删除 _memos_client 相关
    content = re.sub(r'self\._memos_client: Optional\[MemOSClient\] = None\n', '', content)
    content = re.sub(r'self\._init_memos_client\(\)\n', '', content)
    
    # 3. 删除 _init_memos_client 方法
    pattern = r'    def _init_memos_client\(self\).*?(?=\n    def |\n    @|\Z)'
    content = re.sub(pattern, '', content, flags=re.DOTALL)
    
    # 4. 删除 memos_enabled 属性
    pattern = r'    @property\n    def memos_enabled\(self\).*?(?=\n    @|\n    def |\Z)'
    content = re.sub(pattern, '', content, flags=re.DOTALL)
    
    # 5. 删除 memory_add 方法
    pattern = r'    async def memory_add\(self,.*?(?=\n    async def |\n    def |\n    @|\Z)'
    content = re.sub(pattern, '', content, flags=re.DOTALL)
    
    # 6. 删除 memory_search 方法
    pattern = r'    async def memory_search\(self,.*?(?=\n    async def |\n    def |\n    @|\Z)'
    content = re.sub(pattern, '', content, flags=re.DOTALL)
    
    # 7. 删除 memory_feedback 方法
    pattern = r'    async def memory_feedback\(self,.*?(?=\n    async def |\n    def |\n    @|\Z)'
    content = re.sub(pattern, '', content, flags=re.DOTALL)
    
    # 8. 删除 memory_get 方法
    pattern = r'    async def memory_get\(self,.*?(?=\n    async def |\n    def |\n    @|\Z)'
    content = re.sub(pattern, '', content, flags=re.DOTALL)
    
    # 9. 删除 memory_delete 方法
    pattern = r'    async def memory_delete\(self,.*?(?=\n    async def |\n    def |\n    @|\Z)'
    content = re.sub(pattern, '', content, flags=re.DOTALL)
    
    # 10. 删除 MemOSClient 导入
    content = re.sub(r'from .*? import .*?MemOSClient.*?\n', '', content)
    content = re.sub(r', MemOSClient', '', content)
    
    # 11. 清理多余的空行
    content = re.sub(r'\n{4,}', '\n\n\n', content)
    
    if content != original_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"  ✅ 清理: {filepath}")
    else:
        print(f"  ℹ️ 无需修改: {filepath}")


def clean_react_agent(copaw_path):
    """清理 react_agent.py 中的 memory_add 工具注册"""
    filepath = copaw_path / "agents" / "react_agent.py"
    
    if not filepath.exists():
        print(f"  ⚠️ 文件不存在: {filepath}")
        return
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # 1. 删除 create_memory_add_tool 导入
    content = re.sub(r'from \.tools import \(.*?create_memory_add_tool.*?\)', 
                     lambda m: m.group(0).replace('create_memory_add_tool,\n', '').replace('create_memory_add_tool', ''),
                     content, flags=re.DOTALL)
    content = re.sub(r', create_memory_add_tool', '', content)
    
    # 2. 删除 memory_add 工具注册代码块
    # 查找并删除注册 memory_add 的代码
    patterns = [
        r'# Register memory_add.*?logger\.debug\("Registered memory_add tool"\)\n',
        r'if self\._enable_memory_manager and self\.memory_manager.*?create_memory_add_tool\(self\.memory_manager\).*?\n',
    ]
    
    for pattern in patterns:
        content = re.sub(pattern, '', content, flags=re.DOTALL)
    
    # 3. 删除 memos_enabled 检查
    content = re.sub(r'if self\.memory_manager\.memos_enabled:.*?\n', '', content)
    content = re.sub(r'and self\.memory_manager\.memos_enabled', '', content)
    
    if content != original_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"  ✅ 清理: {filepath}")
    else:
        print(f"  ℹ️ 无需修改: {filepath}")


def main():
    print("=" * 60)
    print("🗑️  MemOS 硬编码集成卸载脚本 v2.0")
    print("=" * 60)
    print()
    
    # 获取 Copaw 路径
    copaw_path = get_copaw_path()
    if not copaw_path:
        sys.exit(1)
    
    print(f"📍 Copaw 路径: {copaw_path}")
    print()
    
    # 1. 删除 memos_recall.py (如果存在)
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
            "from .memos_recall import MemosRecallHook",
        ],
        exports_to_remove=[
            "MemosRecallHook",
            "MemosAddHook",
        ]
    )
    
    # 3. 删除 memory_search.py (整个文件都是 MemOS 工具)
    print()
    print("📦 步骤 3: 删除 tools/memory_search.py")
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
            "from .memory_search import create_memory_add_tool",
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
    
    # 5. 清理 memory_manager.py
    print()
    print("📦 步骤 5: 清理 memory/memory_manager.py (移除 MemOSClient)")
    clean_memory_manager(copaw_path)
    
    # 6. 清理 react_agent.py
    print()
    print("📦 步骤 6: 清理 react_agent.py (移除 memory_add 注册)")
    clean_react_agent(copaw_path)
    
    # 7. 删除本地配置文件
    print()
    print("📦 步骤 7: 删除本地配置文件")
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
    print("2. 在 mcp.clients 中添加 memos 配置")
    print("3. 重启 Copaw: copaw restart")
    print()
    print("📖 详细说明: https://github.com/Hailpeng/copaw-memos-integration")
    print()


if __name__ == "__main__":
    main()