# -*- coding: utf-8 -*-
"""Agent hooks package.

This package provides hook implementations for CoPawAgent that follow
AgentScope's hook interface (any Callable).

Available Hooks:
    - BootstrapHook: First-time setup guidance
    - MemoryCompactionHook: Automatic context window management
    - MemosRecallHook: Automatic memory recall from MemOS Cloud
    - MemosAddHook: Automatic conversation capture to MemOS Cloud
"""

from .bootstrap import BootstrapHook
from .memory_compaction import MemoryCompactionHook
from .memos_recall import MemosRecallHook, MemosAddHook

__all__ = [
    "BootstrapHook",
    "MemoryCompactionHook",
    "MemosRecallHook",
    "MemosAddHook",
]
