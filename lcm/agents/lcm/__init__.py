# -*- coding: utf-8 -*-
"""LCM - Lossless Context Management for Copaw.

This module provides a complete LCM implementation:
- SQLite-based message persistence (never lose data)
- DAG-based summarization (multi-level compression)
- Agent tools for searching and expanding compressed history

Key components:
- LCMEngine: Main orchestration class
- LCMConfig: Configuration parameters
- LCMDatabase: SQLite persistence layer
- DAGCompactor: Compression engine
- Tools: lcm_grep, lcm_describe, lcm_expand

Quick start:
    from copaw.agents.lcm import LCMEngine, LCMConfig
    
    config = LCMConfig(
        db_path="~/.copaw/lcm.db",
        context_threshold=0.7,
    )
    
    engine = LCMEngine(
        config=config,
        agent_id="default",
        conversation_id="session-123",
        chat_model=model,
    )
    
    await engine.initialize()
    await engine.ingest(messages)
    compacted = await engine.check_and_compact(messages, max_tokens=100000)
"""

from .config import LCMConfig
from .database import LCMDatabase
from .engine import LCMEngine
from .compactor import DAGCompactor
from .tools import (
    LCM_TOOLS,
    LCMToolHandler,
    lcm_grep,
    lcm_describe,
    lcm_expand,
    register_lcm_tools,
)

__all__ = [
    # Core
    "LCMEngine",
    "LCMConfig",
    "LCMDatabase",
    "DAGCompactor",
    # Tools
    "LCM_TOOLS",
    "LCMToolHandler",
    "lcm_grep",
    "lcm_describe",
    "lcm_expand",
    "register_lcm_tools",
]

__version__ = "0.1.0"