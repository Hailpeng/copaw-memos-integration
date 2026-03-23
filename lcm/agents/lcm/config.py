# -*- coding: utf-8 -*-
"""LCM Configuration.

Configuration parameters for Lossless Context Management.
"""
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class LCMConfig:
    """Configuration for LCM (Lossless Context Management).
    
    Attributes:
        db_path: Path to SQLite database for persisting messages and summaries
        context_threshold: Fraction of context window that triggers compaction (0.0-1.0)
        fresh_tail_count: Number of recent messages protected from compaction
        leaf_min_fanout: Minimum raw messages per leaf summary
        condensed_min_fanout: Minimum summaries per condensed node
        condensed_min_fanout_hard: Relaxed fanout for forced compaction sweeps
        leaf_target_tokens: Target token count for leaf summaries
        condensed_target_tokens: Target token count for condensed summaries
        leaf_chunk_tokens: Max source tokens per leaf compaction chunk
        max_expand_tokens: Token cap for expansion queries
        summary_provider: Provider override for summarization (empty = use main model)
        summary_model: Model override for summarization (empty = use main model)
        expansion_provider: Secondary provider for LCM when main model is busy
        expansion_model: Secondary model for LCM when main model is busy
        enable_fts: Enable FTS5 full-text search
    """
    # Database
    db_path: str = ""
    
    # Compaction triggers
    context_threshold: float = 0.7
    fresh_tail_count: int = 32
    
    # DAG structure
    leaf_min_fanout: int = 8
    condensed_min_fanout: int = 4
    condensed_min_fanout_hard: int = 2
    
    # Summary targets
    leaf_target_tokens: int = 1200
    condensed_target_tokens: int = 2000
    leaf_chunk_tokens: int = 20000
    max_expand_tokens: int = 4000
    
    # Model settings
    summary_provider: str = ""
    summary_model: str = ""
    expansion_provider: str = ""
    expansion_model: str = ""
    
    # Search
    enable_fts: bool = True
    
    def __post_init__(self):
        """Set default db_path if not provided."""
        if not self.db_path:
            self.db_path = str(Path.home() / ".copaw" / "lcm.db")
    
    @classmethod
    def from_agent_config(cls, agent_config) -> "LCMConfig":
        """Create LCMConfig from agent configuration.
        
        Args:
            agent_config: AgentProfileConfig object
            
        Returns:
            LCMConfig instance
        """
        running = agent_config.running
        
        # Extract summary model from config if available
        summary_provider = ""
        summary_model = ""
        
        # Check for embedding config as a proxy for model config
        # In the future, this could be a dedicated LCM config section
        emb_config = running.embedding_config
        if emb_config and emb_config.base_url:
            # Use embedding provider for summaries (usually cheaper)
            pass
        
        # Read expansion model from environment variables
        # Format: LCM_EXPANSION_MODEL=provider/model (e.g., "aliyun-codingplan/glm-4.7")
        expansion_provider = ""
        expansion_model = ""
        expansion_env = os.environ.get("LCM_EXPANSION_MODEL", "")
        if expansion_env and "/" in expansion_env:
            parts = expansion_env.split("/", 1)
            expansion_provider = parts[0]
            expansion_model = parts[1]
        
        return cls(
            context_threshold=running.memory_compact_ratio,
            db_path=str(Path.home() / ".copaw" / "lcm.db"),
            expansion_provider=expansion_provider,
            expansion_model=expansion_model,
        )