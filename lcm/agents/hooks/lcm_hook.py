# -*- coding: utf-8 -*-
"""LCM Hook for Copaw agents.

Integrates LCM (Lossless Context Management) into Copaw's memory system.
This hook replaces the default MemoryCompactionHook with DAG-based compression.
"""
import logging
from typing import TYPE_CHECKING, Any, Optional

from agentscope.agent import ReActAgent
from agentscope.message import Msg, TextBlock

from copaw.config.config import load_agent_config
from copaw.agents.utils import get_copaw_token_counter
from copaw.agents.model_factory import create_model_and_formatter, create_model_by_slot

from ..lcm import LCMEngine, LCMConfig

if TYPE_CHECKING:
    from ..memory import MemoryManager

logger = logging.getLogger(__name__)


class LCMHook:
    """Hook for LCM-based context management.
    
    This hook:
    1. Ingests all messages into SQLite (never lost)
    2. Triggers DAG compaction when threshold is reached
    3. Provides tools for searching compressed history
    
    Usage:
        # In agent initialization:
        lcm_hook = LCMHook(memory_manager)
        agent.add_hook(lcm_hook)
    """
    
    def __init__(
        self,
        memory_manager: "MemoryManager",
        config: Optional[LCMConfig] = None,
    ):
        """Initialize LCM hook.
        
        Args:
            memory_manager: Memory manager instance
            config: Optional LCM configuration (uses defaults if not provided)
        """
        self.memory_manager = memory_manager
        self.agent_id = memory_manager.agent_id
        self._config = config
        self._engine: Optional[LCMEngine] = None
        self._initialized = False
    
    async def _ensure_initialized(self, agent: ReActAgent) -> None:
        """Ensure the LCM engine is initialized."""
        if self._initialized:
            return
        
        # Get configuration
        agent_config = load_agent_config(self.agent_id)
        
        if self._config is None:
            self._config = LCMConfig.from_agent_config(agent_config)
        
        # Get model for summarization using three-level priority:
        # 1. expansion_model (dedicated LCM model, avoids conflict with main agent)
        # 2. memory_manager.chat_model
        # 3. create_model_and_formatter (current session model)
        chat_model = None
        formatter = None
        
        # First try: Use dedicated expansion model (avoids conflict with main agent model)
        if self._config.expansion_provider and self._config.expansion_model:
            try:
                chat_model, formatter = create_model_by_slot(
                    self._config.expansion_provider,
                    self._config.expansion_model,
                )
                logger.info(
                    f"LCM using expansion model: "
                    f"{self._config.expansion_provider}/{self._config.expansion_model}"
                )
            except Exception as e:
                logger.warning(f"Failed to create expansion model: {e}")
        
        # Second try: Use memory_manager's chat_model
        if chat_model is None:
            chat_model = getattr(self.memory_manager, "chat_model", None)
            formatter = getattr(self.memory_manager, "formatter", None)
        
        # Third try: Create from agent config (uses current session model)
        if chat_model is None:
            try:
                chat_model, formatter = create_model_and_formatter(self.agent_id)
                logger.info("LCM using current session model for summarization")
            except Exception as e:
                logger.warning(f"Failed to create model for LCM: {e}")
        
        token_counter = get_copaw_token_counter(agent_config)
        
        # Get conversation ID from agent
        conversation_id = getattr(agent, "session_id", None)
        if not conversation_id:
            # Generate a conversation ID
            import uuid
            conversation_id = f"conv-{uuid.uuid4().hex[:8]}"
        
        # Create engine
        self._engine = LCMEngine(
            config=self._config,
            agent_id=self.agent_id,
            conversation_id=conversation_id,
            chat_model=chat_model,
            formatter=formatter,
            token_counter=token_counter,
        )
        
        await self._engine.initialize()
        self._initialized = True
        logger.info(f"LCM hook initialized for agent: {self.agent_id}")
    
    async def __call__(
        self,
        agent: ReActAgent,
        kwargs: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Pre-reasoning hook for LCM.
        
        This hook:
        1. Ingests new messages into SQLite
        2. Checks if compaction is needed
        3. Performs DAG compaction if threshold is reached
        
        Args:
            agent: The agent instance
            kwargs: Input arguments to the _reasoning method
            
        Returns:
            None (hook doesn't modify kwargs directly)
        """
        try:
            await self._ensure_initialized(agent)
            
            if not self._engine:
                return None
            
            # Get messages from agent memory
            memory = agent.memory
            messages = await memory.get_memory(prepend_summary=False)
            
            if not messages:
                return None
            
            # Ingest new messages
            await self._engine.ingest(messages)
            
            # Get token limit
            agent_config = load_agent_config(self.agent_id)
            max_tokens = agent_config.running.max_input_length
            
            # Check and compact
            compacted, did_compact = await self._engine.check_and_compact(
                messages,
                max_tokens,
            )
            
            if did_compact:
                await self._print_status_message(
                    agent,
                    "🔄 LCM Context compaction completed",
                )
                
                # Update agent memory with compacted messages
                # Clear old messages and add compacted ones
                try:
                    await memory.clear()
                    for msg in compacted:
                        await memory.add(msg)
                    logger.info(f"LCM updated memory: {len(messages)} -> {len(compacted)} messages")
                except Exception as update_error:
                    logger.error(f"Failed to update memory after compaction: {update_error}")
                    # Try alternative: update compressed summary
                    try:
                        summary_text = "\n".join([
                            f"[{m.role}]: {m.content if isinstance(m.content, str) else str(m.content)[:200]}"
                            for m in compacted[:5]  # Use first 5 as summary
                        ])
                        await memory.update_compressed_summary(summary_text)
                        logger.info(f"LCM updated compressed summary instead")
                    except Exception as summary_error:
                        logger.error(f"Failed to update compressed summary: {summary_error}")
            
            return None
            
        except Exception as e:
            logger.exception(f"LCM hook failed: {e}")
            return None
    
    @staticmethod
    async def _print_status_message(
        agent: ReActAgent,
        text: str,
    ) -> None:
        """Print a status message to the agent's output."""
        msg = Msg(
            name=agent.name,
            role="assistant",
            content=[{"type": "text", "text": text}],
        )
        await agent.print(msg)
    
    def get_tool_handler(self) -> Optional["LCMToolHandler"]:
        """Get the tool handler for LCM tools.
        
        Returns:
            LCMToolHandler if engine is initialized, None otherwise
        """
        if not self._engine:
            return None
        
        from ..lcm import LCMToolHandler
        return LCMToolHandler(self._engine)
    
    def get_tool_definitions(self) -> list[dict]:
        """Get LCM tool definitions for agent registration."""
        from ..lcm import LCMToolHandler
        return LCMToolHandler.get_tool_definitions()


# Factory function for creating LCM hooks
def create_lcm_hook(
    memory_manager: "MemoryManager",
    config: Optional[LCMConfig] = None,
) -> LCMHook:
    """Create an LCM hook.
    
    Args:
        memory_manager: Memory manager instance
        config: Optional LCM configuration
        
    Returns:
        LCMHook instance
    """
    return LCMHook(memory_manager, config)