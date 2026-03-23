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
- 安装前会自动清理旧的硬编码 MemOS 集成
- Copaw 更新（pip install -U copaw）会覆盖 LCM 模块
- 更新后请重新运行此脚本：python install_lcm.py
- 或使用 --check 检查是否需要重新安装
"""
import os
import sys
import re
import shutil
from pathlib import Path

# LCM 版本号 - 与 CHANGELOG.md 保持同步
LCM_VERSION = "0.14"
LCM_VERSION_FILE = "lcm_version.txt"


def clean_legacy_memos_integration(copaw_path: Path):
    """清理旧的硬编码 MemOS 集成代码
    
    迁移到 MCP 方式后，需要删除内置的 memory_add 等工具。
    这些代码会与 MCP 工具冲突。
    """
    print("\n🔍 检查旧的 MemOS 硬编码集成...")
    
    # 检查是否需要清理
    memory_manager = copaw_path / "agents" / "memory" / "memory_manager.py"
    memory_search = copaw_path / "agents" / "tools" / "memory_search.py"
    
    needs_cleanup = False
    
    if memory_manager.exists():
        content = memory_manager.read_text(encoding="utf-8")
        if "MemOSClient" in content or "memos_enabled" in content:
            needs_cleanup = True
            print("  ⚠️ 发现 MemOSClient 类 (memory_manager.py)")
    
    if memory_search.exists():
        content = memory_search.read_text(encoding="utf-8")
        if "memory_add" in content or "memos_enabled" in content:
            needs_cleanup = True
            print("  ⚠️ 发现 memory_add 工具 (memory_search.py)")
    
    if not needs_cleanup:
        print("  ✅ 无需清理，未发现旧的 MemOS 集成")
        return
    
    print("\n🧹 开始清理旧的 MemOS 集成...")
    
    # 1. 删除 memory_search.py (整个文件都是 MemOS 工具)
    tools_dir = copaw_path / "agents" / "tools"
    if memory_search.exists():
        memory_search.unlink()
        print(f"  ✅ 删除: {memory_search}")
    
    # 2. 清理 tools/__init__.py
    tools_init = tools_dir / "__init__.py"
    if tools_init.exists():
        content = tools_init.read_text(encoding="utf-8")
        # 移除 memory_search 相关导入
        patterns = [
            r'from \.memory_search import \(.*?\)\n',
            r'from \.memory_search import.*?\n',
            r'"create_memory_search_tool",?\s*',
            r'"create_memory_add_tool",?\s*',
            r'"create_memory_feedback_tool",?\s*',
            r'"create_memory_get_tool",?\s*',
            r'"create_memory_delete_tool",?\s*',
        ]
        for p in patterns:
            content = re.sub(p, '', content, flags=re.DOTALL)
        tools_init.write_text(content, encoding="utf-8")
        print(f"  ✅ 清理: {tools_init}")
    
    # 3. 清理 memory_manager.py
    if memory_manager.exists():
        content = memory_manager.read_text(encoding="utf-8")
        original = content
        
        # 删除 MemOSClient 类
        content = re.sub(r'class MemOSClient:.*?(?=\nclass |\Z)', '', content, flags=re.DOTALL)
        
        # 删除 _memos_client 相关
        content = re.sub(r'self\._memos_client: Optional\[MemOSClient\] = None\n', '', content)
        content = re.sub(r'self\._init_memos_client\(\)\n', '', content)
        
        # 删除 _init_memos_client 方法
        content = re.sub(r'    def _init_memos_client\(self\).*?(?=\n    def |\n    @property|\Z)', '', content, flags=re.DOTALL)
        
        # 删除 memos_enabled 属性
        content = re.sub(r'    @property\n    def memos_enabled\(self\).*?(?=\n    @property|\n    def |\Z)', '', content, flags=re.DOTALL)
        
        # 删除 memory_add 等方法
        for method in ['memory_add', 'memory_search', 'memory_feedback', 'memory_get', 'memory_delete']:
            content = re.sub(rf'    async def {method}\(self,.*?(?=\n    async def |\n    def |\n    @property|\Z)', '', content, flags=re.DOTALL)
        
        # 删除 MemOSClient 导入
        content = re.sub(r'from .*? import .*?MemOSClient.*?\n', '', content)
        content = re.sub(r', MemOSClient', '', content)
        
        # 清理多余空行
        content = re.sub(r'\n{4,}', '\n\n\n', content)
        
        if content != original:
            memory_manager.write_text(content, encoding="utf-8")
            print(f"  ✅ 清理: {memory_manager}")
    
    # 4. 清理 react_agent.py
    react_agent = copaw_path / "agents" / "react_agent.py"
    if react_agent.exists():
        content = react_agent.read_text(encoding="utf-8")
        original = content
        
        # 删除 create_memory_add_tool 导入
        content = re.sub(r', create_memory_add_tool', '', content)
        content = re.sub(r'create_memory_add_tool,\n', '', content)
        
        # 删除 memory_add 工具注册
        content = re.sub(r'# Register memory_add.*?logger\.debug\("Registered memory_add tool"\)\n', '', content, flags=re.DOTALL)
        content = re.sub(r'if self\._enable_memory_manager and self\.memory_manager.*?create_memory_add_tool.*?\n', '', content, flags=re.DOTALL)
        content = re.sub(r'and self\.memory_manager\.memos_enabled', '', content)
        
        if content != original:
            react_agent.write_text(content, encoding="utf-8")
            print(f"  ✅ 清理: {react_agent}")
    
    print("  ✅ 旧的 MemOS 集成已清理")


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
    
    # 步骤 0: 清理旧的 MemOS 硬编码集成
    clean_legacy_memos_integration(copaw_path)
    
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
    print(f"\n[1/6] 安装 LCM 模块...")
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
    print(f"\n[2/6] 安装 LCM Hook...")
    hook_dst.parent.mkdir(parents=True, exist_ok=True)
    if hook_dst.exists():
        hook_dst.unlink()
    shutil.copy2(hook_src, hook_dst)
    print(f"  ✅ LCM Hook 已安装到: {hook_dst}")
    
    # 更新 hooks/__init__.py
    print(f"\n[3/6] 更新 hooks/__init__.py...")
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
    
    # 更新 model_factory.py 添加 create_model_by_slot
    print(f"\n[4/6] 更新 model_factory.py...")
    model_factory = copaw_path / "agents" / "model_factory.py"
    model_factory_ext = script_dir / "lcm" / "agents" / "model_factory.py"
    
    if model_factory.exists():
        content = model_factory.read_text(encoding="utf-8")
        
        if "create_model_by_slot" not in content:
            # 读取扩展代码
            if model_factory_ext.exists():
                ext_content = model_factory_ext.read_text(encoding="utf-8")
                # 提取函数定义
                import re
                func_match = re.search(
                    r'(def create_model_by_slot\([^)]+\)[^}]+return wrapped_model, formatter)',
                    ext_content,
                    re.DOTALL
                )
                if func_match:
                    func_code = func_match.group(1)
                    # 在 __all__ 之前添加函数
                    if "__all__" in content:
                        all_match = re.search(r'__all__\s*=\s*\[', content)
                        if all_match:
                            insert_pos = all_match.start()
                            new_content = content[:insert_pos] + func_code + "\n\n\n" + content[insert_pos:]
                            # 更新 __all__
                            new_content = new_content.replace(
                                '"create_model_and_formatter",\n]',
                                '"create_model_and_formatter",\n    "create_model_by_slot",\n]'
                            )
                            model_factory.write_text(new_content, encoding="utf-8")
                            print(f"  ✅ 已添加 create_model_by_slot 到: {model_factory}")
                    else:
                        # 追加到文件末尾
                        content += "\n\n\n" + func_code
                        model_factory.write_text(content, encoding="utf-8")
                        print(f"  ✅ 已添加 create_model_by_slot 到: {model_factory}")
            else:
                print(f"  ⚠️ model_factory.py 扩展文件不存在")
        else:
            print(f"  ⏭️ create_model_by_slot 已存在于 model_factory.py")
    
    # 修改 react_agent.py 以启用 LCM
    print(f"\n[5/6] 配置 react_agent.py...")
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
    print(f"\n[6/6] 检查 reme 依赖...")
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
            print("  python install_lcm.py          # 检查并安装/更新 LCM")
            print("  python install_lcm.py --force  # 强制重新安装")
            print("  python install_lcm.py --uninstall  # 卸载 LCM")
    else:
        # 默认行为：检查 + 安装（智能模式）
        install_lcm()