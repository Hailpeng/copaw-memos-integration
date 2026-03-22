#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
MemOS Cloud 恢复脚本 v2.0
在 Copaw 更新后自动恢复 MemOS 集成

策略：
1. 优先打补丁（保留 Copaw 新功能）
2. 补丁失败则完整覆盖（确保功能可用）

使用方法:
    python restore_memos.py [--copaw-path PATH] [--force]

默认:
    --copaw-path: 自动检测 Copaw 安装路径
    --force: 强制完整覆盖（不尝试打补丁）
"""

import argparse
import logging
import re
import shutil
import sys
from pathlib import Path
from typing import Optional

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


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
    except Exception:
        pass
    return None


def restore_file(src: Path, dst: Path, description: str = "") -> bool:
    """完整复制文件"""
    try:
        if not src.exists():
            logger.warning(f"源文件不存在: {src}")
            return False
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        logger.info(f"✅ 已恢复: {description or dst.name}")
        return True
    except Exception as e:
        logger.error(f"❌ 恢复失败 {description or dst.name}: {e}")
        return False


def check_memos_in_file(filepath: Path, check_strings: list) -> bool:
    """检查文件是否已包含 MemOS 相关内容"""
    try:
        if not filepath.exists():
            return False
        content = filepath.read_text(encoding="utf-8")
        return all(s in content for s in check_strings)
    except Exception:
        return False


def patch_hooks_init(filepath: Path) -> bool:
    """打补丁: hooks/__init__.py"""
    try:
        content = filepath.read_text(encoding="utf-8")
        
        if "MemosRecallHook" in content and "MemosAddHook" in content:
            logger.info("⏭️  hooks/__init__.py 已包含 MemOS 导出，跳过")
            return True
        
        # 添加 import
        import_pattern = "from .memory_compaction import MemoryCompactionHook"
        import_add = """from .memory_compaction import MemoryCompactionHook
from .memos_recall import MemosRecallHook, MemosAddHook"""
        
        if import_pattern in content:
            content = content.replace(import_pattern, import_add)
            logger.info("✅ 已添加 MemOS import")
        else:
            logger.warning("⚠️  未找到 import 插入点")
            return False
        
        # 添加到 __all__
        all_pattern = '"MemoryCompactionHook",'
        all_add = '''"MemoryCompactionHook",
    "MemosRecallHook",
    "MemosAddHook",'''
        
        if all_pattern in content:
            content = content.replace(all_pattern, all_add)
            logger.info("✅ 已添加 MemOS 到 __all__")
        else:
            logger.warning("⚠️  未找到 __all__ 插入点")
            return False
        
        filepath.write_text(content, encoding="utf-8")
        return True
        
    except Exception as e:
        logger.error(f"❌ 打补丁失败: {e}")
        return False


def patch_tools_init(filepath: Path) -> bool:
    """打补丁: tools/__init__.py"""
    try:
        content = filepath.read_text(encoding="utf-8")
        
        if "create_memory_search_tool" in content and "create_knowledgebase_tools" in content:
            logger.info("⏭️  tools/__init__.py 已包含 memory 工具导出，跳过")
            return True
        
        # 添加 import
        import_pattern = "from .view_image import view_image"
        import_add = """from .view_image import view_image
from .memory_search import (
    create_memory_search_tool,
    create_memory_add_tool,
    create_memory_feedback_tool,
    create_memory_get_tool,
    create_memory_delete_tool,
    create_task_status_tool,
    create_knowledgebase_tools,
)"""
        
        if import_pattern in content:
            content = content.replace(import_pattern, import_add)
            logger.info("✅ 已添加 memory tools import")
        else:
            logger.warning("⚠️  未找到 import 插入点")
            return False
        
        # 添加到 __all__
        all_pattern = '"view_image",'
        all_add = '''"view_image",
    "create_memory_search_tool",
    "create_memory_add_tool",
    "create_memory_feedback_tool",
    "create_memory_get_tool",
    "create_memory_delete_tool",
    "create_task_status_tool",
    "create_knowledgebase_tools",'''
        
        if all_pattern in content:
            content = content.replace(all_pattern, all_add)
            logger.info("✅ 已添加 memory tools 到 __all__")
        else:
            logger.warning("⚠️  未找到 __all__ 插入点")
            return False
        
        filepath.write_text(content, encoding="utf-8")
        return True
        
    except Exception as e:
        logger.error(f"❌ 打补丁失败: {e}")
        return False


def patch_react_agent(filepath: Path, patch_file: Path) -> bool:
    """打补丁: react_agent.py"""
    try:
        content = filepath.read_text(encoding="utf-8")
        
        if "memos_recall_hook" in content and "MemosRecallHook" in content:
            logger.info("⏭️  react_agent.py 已包含 MemOS hook 注册，跳过")
            return True
        
        # 从补丁文件读取 MemOS 相关代码
        patch_content = patch_file.read_text(encoding="utf-8")
        
        # 查找 MemOS hook 注册代码
        memos_pattern = r'(# MemOS recall hook.*?)(?=\n        def |\nclass |\Z)'
        match = re.search(memos_pattern, patch_content, re.DOTALL)
        
        if not match:
            logger.warning("⚠️  未在补丁文件中找到 MemOS hook 代码")
            return False
        
        memos_code = match.group(1)
        
        # 查找插入点
        bootstrap_pattern = r'logger\.debug\("Registered bootstrap hook"\)'
        if not re.search(bootstrap_pattern, content):
            logger.warning("⚠️  未找到 bootstrap_hook 插入点")
            return False
        
        # 插入代码
        new_content = re.sub(
            bootstrap_pattern,
            'logger.debug("Registered bootstrap hook")\n' + memos_code,
            content
        )
        filepath.write_text(new_content, encoding="utf-8")
        logger.info("✅ 已添加 MemOS hooks 注册")
        return True
        
    except Exception as e:
        logger.error(f"❌ 打补丁失败: {e}")
        return False


def smart_restore(
    backup_file: Path,
    copaw_relative: str,
    copaw_path: Path,
    patch_func,
    force_full: bool = False,
) -> tuple:
    """智能恢复：优先打补丁，失败则完整覆盖"""
    dst = copaw_path / copaw_relative
    
    if not backup_file.exists():
        return False, "backup_missing"
    
    if force_full:
        if restore_file(backup_file, dst, backup_file.name):
            return True, "full"
        return False, "full_failed"
    
    if check_memos_in_file(dst, ["memos", "MemOS"]):
        return True, "already_present"
    
    if patch_func and patch_func(dst):
        return True, "patch"
    
    logger.warning(f"⚠️  补丁失败，尝试完整覆盖: {backup_file.name}")
    if restore_file(backup_file, dst, backup_file.name):
        return True, "full_fallback"
    
    return False, "all_failed"


def main():
    parser = argparse.ArgumentParser(description="MemOS Cloud 恢复脚本 v2.0")
    parser.add_argument(
        "--copaw-path",
        default=None,
        help="Copaw 安装路径 (默认: 自动检测)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="强制完整覆盖（不尝试打补丁）"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只检查不执行"
    )
    args = parser.parse_args()
    
    # 获取路径
    if args.copaw_path:
        copaw_path = Path(args.copaw_path)
    else:
        copaw_path = get_copaw_path()
    
    backup_dir = Path(__file__).parent / "src"
    patches_dir = backup_dir / "patches"
    
    logger.info("="*60)
    logger.info("🚀 MemOS Cloud 恢复脚本 v2.0")
    logger.info("="*60)
    logger.info(f"Copaw 路径: {copaw_path}")
    logger.info(f"备份路径: {backup_dir}")
    logger.info(f"模式: {'强制覆盖' if args.force else '智能恢复'}")
    logger.info("")
    
    if not copaw_path:
        logger.error("❌ 无法找到 Copaw 安装路径")
        return 1
    
    if not backup_dir.exists():
        logger.error(f"❌ 备份路径不存在: {backup_dir}")
        return 1
    
    # Dry run 模式
    if args.dry_run:
        logger.info("📋 Dry run 模式 - 只检查不执行")
        logger.info("")
        
        for backup_file in backup_dir.rglob("*.py"):
            logger.info(f"  备份: {backup_file.relative_to(backup_dir)}")
        
        return 0
    
    results = []
    
    # 完整覆盖文件
    logger.info("="*60)
    logger.info("📦 步骤 1: 恢复核心文件（完整覆盖）")
    logger.info("="*60)
    
    full_restore_files = [
        ("hooks/memos_recall.py", "agents/hooks/memos_recall.py"),
        ("tools/memory_search.py", "agents/tools/memory_search.py"),
        ("memory/memory_manager.py", "agents/memory/memory_manager.py"),
    ]
    
    for backup_rel, copaw_rel in full_restore_files:
        src = backup_dir / backup_rel
        dst = copaw_path / copaw_rel
        success = restore_file(src, dst, backup_rel)
        results.append((backup_rel, "full" if success else "failed"))
    
    # 打补丁文件
    logger.info("")
    logger.info("="*60)
    logger.info("🔧 步骤 2: 恢复补丁文件（智能恢复）")
    logger.info("="*60)
    
    patch_funcs = {
        "hooks/__init__.py": patch_hooks_init,
        "tools/__init__.py": patch_tools_init,
    }
    
    patch_files = [
        ("patches/hooks_init_example.py", "agents/hooks/__init__.py"),
        ("patches/tools_init_example.py", "agents/tools/__init__.py"),
    ]
    
    for backup_rel, copaw_rel in patch_files:
        backup_file = backup_dir / backup_rel
        patch_func = patch_funcs.get(Path(copaw_rel).name)
        success, method = smart_restore(
            backup_file,
            copaw_rel,
            copaw_path,
            patch_func,
            force_full=args.force,
        )
        results.append((copaw_rel, method if success else "failed"))
    
    # react_agent.py
    logger.info("")
    logger.info("="*60)
    logger.info("🤖 步骤 3: 恢复 react_agent.py")
    logger.info("="*60)
    
    react_agent_backup = patches_dir / "react_agent_patch.py"
    react_agent_dst = copaw_path / "agents" / "react_agent.py"
    
    success, method = smart_restore(
        react_agent_backup,
        "agents/react_agent.py",
        copaw_path,
        lambda f: patch_react_agent(f, react_agent_backup),
        force_full=args.force,
    )
    results.append(("react_agent.py", method if success else "failed"))
    
    # 汇总
    logger.info("")
    logger.info("="*60)
    logger.info("📊 恢复结果汇总")
    logger.info("="*60)
    
    all_success = True
    for name, method in results:
        if method == "failed":
            status = "❌ 失败"
            all_success = False
        elif method == "already_present":
            status = "⏭️  已存在"
        elif method == "patch":
            status = "✅ 打补丁"
        elif method == "full":
            status = "✅ 完整覆盖"
        elif method == "full_fallback":
            status = "⚠️  补丁失败→完整覆盖"
        else:
            status = f"✅ {method}"
        
        logger.info(f"  {name}: {status}")
    
    logger.info("")
    if all_success:
        logger.info("🎉 所有恢复操作完成!")
        return 0
    else:
        logger.error("⚠️  部分恢复操作失败，请检查日志")
        return 1


if __name__ == "__main__":
    exit(main())