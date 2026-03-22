#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
MemOS Cloud 集成安装脚本
自动将 MemOS 集成到 Copaw 中
"""

import argparse
import logging
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s"
)
logger = logging.getLogger(__name__)

# 颜色输出
class Colors:
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BLUE = "\033[94m"
    RESET = "\033[0m"

def color_print(color: str, message: str):
    """彩色打印"""
    print(f"{color}{message}{Colors.RESET}")

def get_copaw_path() -> Path:
    """获取 Copaw 安装路径"""
    try:
        result = subprocess.run(
            [sys.executable, "-c", "import copaw; print(copaw.__path__[0])"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            return Path(result.stdout.strip())
    except Exception as e:
        logger.error(f"获取 Copaw 路径失败: {e}")
    return None

def get_copaw_workspace() -> Path:
    """获取 Copaw 工作空间路径"""
    home = Path.home()
    if platform.system() == "Windows":
        return home / ".copaw" / "workspaces" / "default"
    return home / ".copaw" / "workspaces" / "default"

def backup_file(src: Path, backup_dir: Path) -> bool:
    """备份文件"""
    try:
        if src.exists():
            backup_path = backup_dir / src.name
            shutil.copy2(src, backup_path)
            logger.info(f"已备份: {src.name}")
            return True
    except Exception as e:
        logger.error(f"备份失败 {src.name}: {e}")
    return False

def copy_file(src: Path, dst: Path, description: str = "") -> bool:
    """复制文件"""
    try:
        if not src.exists():
            logger.error(f"源文件不存在: {src}")
            return False
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        color_print(Colors.GREEN, f"✅ 已复制: {description or dst.name}")
        return True
    except Exception as e:
        color_print(Colors.RED, f"❌ 复制失败 {description or dst.name}: {e}")
        return False

def patch_file(filepath: Path, search: str, replace: str, description: str = "") -> bool:
    """打补丁"""
    try:
        if not filepath.exists():
            logger.error(f"文件不存在: {filepath}")
            return False
        
        content = filepath.read_text(encoding="utf-8")
        
        # 检查是否已存在
        if replace in content:
            color_print(Colors.BLUE, f"⏭️  已存在: {description or filepath.name}")
            return True
        
        if search not in content:
            color_print(Colors.YELLOW, f"⚠️  未找到插入点: {description or filepath.name}")
            return False
        
        new_content = content.replace(search, replace)
        filepath.write_text(new_content, encoding="utf-8")
        color_print(Colors.GREEN, f"✅ 已打补丁: {description or filepath.name}")
        return True
    except Exception as e:
        color_print(Colors.RED, f"❌ 打补丁失败 {description or filepath.name}: {e}")
        return False

def create_config(api_key: str = "", source_dir: Path = None) -> bool:
    """创建配置文件"""
    workspace = get_copaw_workspace()
    config_dir = workspace / "active_skills" / "memos-cloud"
    config_file = config_dir / "config.json"
    
    if config_file.exists():
        color_print(Colors.BLUE, "⏭️  配置文件已存在，跳过")
        return True
    
    config_dir.mkdir(parents=True, exist_ok=True)
    
    # 使用仓库中的默认配置文件
    import json
    default_config_path = source_dir / "config.json" if source_dir else None
    
    if default_config_path and default_config_path.exists():
        config_content = json.loads(default_config_path.read_text(encoding="utf-8"))
        if api_key:
            config_content["apiKey"] = api_key
    else:
        config_content = {
            "apiKey": api_key or "mpg-YOUR_API_KEY_HERE",
            "baseUrl": "https://memos.memtensor.cn/api/openmem/v1",
            "userId": "copaw-user",
            "recall": {
                "memoryLimit": 9,
                "preferenceLimit": 6,
                "toolMemoryLimit": 6,
                "includePreference": True,
                "includeToolMemory": True,
                "threshold": 0.45,
                "maxItemChars": 8000,
                "queryPrefix": "",
                "recallGlobal": True,
                "knowledgebaseIds": [],
                "tags": []
            },
            "add": {
                "captureStrategy": "last_turn",
                "includeAssistant": False,
                "throttleMs": 0,
                "maxMessageChars": 2000,
                "tags": [],
                "asyncMode": True,
                "multiAgentMode": False
            }
        }
    
    config_file.write_text(json.dumps(config_content, indent=2, ensure_ascii=False), encoding="utf-8")
    color_print(Colors.GREEN, f"✅ 已创建配置文件: {config_file}")
    
    if not api_key:
        color_print(Colors.YELLOW, "⚠️  请编辑配置文件，填入你的 API Key")
        color_print(Colors.YELLOW, f"   路径: {config_file}")
    
    return True

def install(source_dir: Path, copaw_path: Path, api_key: str = "") -> bool:
    """执行安装"""
    results = []
    
    # 1. 备份原文件
    color_print(Colors.BLUE, "\n📦 步骤 1: 备份原文件...")
    backup_dir = source_dir / "backup"
    backup_dir.mkdir(exist_ok=True)
    
    backup_file(copaw_path / "agents" / "hooks" / "memos_recall.py", backup_dir)
    backup_file(copaw_path / "agents" / "tools" / "memory_search.py", backup_dir)
    backup_file(copaw_path / "agents" / "memory" / "memory_manager.py", backup_dir)
    
    # 2. 复制源文件
    color_print(Colors.BLUE, "\n📦 步骤 2: 复制源文件...")
    
    src_files = [
        (source_dir / "src" / "hooks" / "memos_recall.py", copaw_path / "agents" / "hooks" / "memos_recall.py", "memos_recall.py"),
        (source_dir / "src" / "tools" / "memory_search.py", copaw_path / "agents" / "tools" / "memory_search.py", "memory_search.py"),
        (source_dir / "src" / "memory" / "memory_manager.py", copaw_path / "agents" / "memory" / "memory_manager.py", "memory_manager.py"),
    ]
    
    for src, dst, desc in src_files:
        results.append(copy_file(src, dst, desc))
    
    # 3. 修补 hooks/__init__.py
    color_print(Colors.BLUE, "\n🔧 步骤 3: 修补 hooks/__init__.py...")
    hooks_init = copaw_path / "agents" / "hooks" / "__init__.py"
    
    hooks_import = """from .memory_compaction import MemoryCompactionHook
from .memos_recall import MemosRecallHook, MemosAddHook"""
    
    hooks_all = '''"MemoryCompactionHook",
    "MemosRecallHook",
    "MemosAddHook",'''
    
    # 添加 import
    if "MemosRecallHook" not in hooks_init.read_text(encoding="utf-8"):
        results.append(patch_file(
            hooks_init,
            "from .memory_compaction import MemoryCompactionHook",
            hooks_import,
            "hooks/__init__.py import"
        ))
        
        # 添加到 __all__
        results.append(patch_file(
            hooks_init,
            '"MemoryCompactionHook",',
            hooks_all,
            "hooks/__init__.py __all__"
        ))
    else:
        color_print(Colors.BLUE, "⏭️  hooks/__init__.py 已包含 MemOS 导出")
    
    # 4. 修补 tools/__init__.py
    color_print(Colors.BLUE, "\n🔧 步骤 4: 修补 tools/__init__.py...")
    tools_init = copaw_path / "agents" / "tools" / "__init__.py"
    
    tools_import = """from .view_image import view_image
from .memory_search import (
    create_memory_search_tool,
    create_memory_add_tool,
    create_memory_feedback_tool,
    create_memory_get_tool,
    create_memory_delete_tool,
    create_task_status_tool,
    create_knowledgebase_tools,
)"""
    
    tools_all = '''"view_image",
    "create_memory_search_tool",
    "create_memory_add_tool",
    "create_memory_feedback_tool",
    "create_memory_get_tool",
    "create_memory_delete_tool",
    "create_task_status_tool",
    "create_knowledgebase_tools",'''
    
    if "create_memory_search_tool" not in tools_init.read_text(encoding="utf-8"):
        results.append(patch_file(
            tools_init,
            "from .view_image import view_image",
            tools_import,
            "tools/__init__.py import"
        ))
        
        results.append(patch_file(
            tools_init,
            '"view_image",',
            tools_all,
            "tools/__init__.py __all__"
        ))
    else:
        color_print(Colors.BLUE, "⏭️  tools/__init__.py 已包含 memory 工具导出")
    
    # 5. 修补 react_agent.py
    color_print(Colors.BLUE, "\n🔧 步骤 5: 修补 react_agent.py...")
    react_agent = copaw_path / "agents" / "react_agent.py"
    
    if "memos_recall_hook" in react_agent.read_text(encoding="utf-8"):
        color_print(Colors.BLUE, "⏭️  react_agent.py 已包含 MemOS hook 注册")
    else:
        color_print(Colors.YELLOW, "⚠️  请手动修补 react_agent.py")
        color_print(Colors.YELLOW, "   参考: src/patches/react_agent_patch.py")
        results.append(False)
    
    # 6. 创建配置文件
    color_print(Colors.BLUE, "\n📝 步骤 6: 创建配置文件...")
    create_config(api_key, source_dir)
    
    # 汇总
    color_print(Colors.BLUE, "\n" + "="*50)
    color_print(Colors.BLUE, "📊 安装结果")
    color_print(Colors.BLUE, "="*50)
    
    success = all(results)
    if success:
        color_print(Colors.GREEN, "\n🎉 MemOS 集成安装完成！")
        color_print(Colors.BLUE, "\n下一步:")
        color_print(Colors.BLUE, "  1. 编辑配置文件，填入你的 API Key")
        color_print(Colors.BLUE, "  2. 重启 Copaw")
    else:
        color_print(Colors.YELLOW, "\n⚠️  部分步骤失败，请检查日志")
    
    return success

def main():
    parser = argparse.ArgumentParser(description="MemOS Cloud 集成安装脚本")
    parser.add_argument("--api-key", default="", help="MemOS API Key")
    parser.add_argument("--copaw-path", default="", help="Copaw 安装路径")
    parser.add_argument("--dry-run", action="store_true", help="只检查不执行")
    args = parser.parse_args()
    
    color_print(Colors.BLUE, "="*50)
    color_print(Colors.BLUE, "🚀 MemOS Cloud 集成安装脚本")
    color_print(Colors.BLUE, "="*50)
    
    # 获取路径
    source_dir = Path(__file__).parent
    
    if args.copaw_path:
        copaw_path = Path(args.copaw_path)
    else:
        copaw_path = get_copaw_path()
    
    if not copaw_path:
        color_print(Colors.RED, "❌ 无法找到 Copaw 安装路径")
        color_print(Colors.YELLOW, "请使用 --copaw-path 参数指定路径")
        return 1
    
    color_print(Colors.BLUE, f"\nCopaw 路径: {copaw_path}")
    color_print(Colors.BLUE, f"源码路径: {source_dir}")
    
    if args.dry_run:
        color_print(Colors.YELLOW, "\n📋 Dry run 模式 - 只检查不执行")
        return 0
    
    success = install(source_dir, copaw_path, args.api_key)
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())