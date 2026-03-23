# -*- coding: utf-8 -*-
"""LCM Engine - Main engine for Lossless Context Management.

Orchestrates message persistence, DAG compaction, and context assembly.
"""
import asyncio
import logging
import uuid
from typing import TYPE_CHECKING, Optional

from agentscope.message import Msg

from .config import LCMConfig
from .database import LCMDatabase

if TYPE_CHECKING:
    from agentscope.model import ChatModelBase
    from agentscope.formatter import FormatterBase

logger = logging.getLogger(__name__)


class LCMEngine:
    """Main engine for Lossless Context Management.
    
    This engine provides:
    - Message persistence to SQLite (never lost)
    - DAG-based summarization (multi-level)
    - Context assembly for model calls
    - Search and expansion tools for agents
    
    Usage:
        engine = LCMEngine(config, agent_id, conversation_id)
        
        # Ingest messages
        await engine.ingest(messages)
        
        # Check and compact if needed
        compacted_messages = await engine.check_and_compact(messages)
        
        # Assemble context for model
        context = await engine.assemble_context(max_tokens)
        
        # Search history
        results = await engine.search("query")
    """
    
    def __init__(
        self,
        config: LCMConfig,
        agent_id: str,
        conversation_id: str,
        chat_model: Optional["ChatModelBase"] = None,
        formatter: Optional["FormatterBase"] = None,
        token_counter=None,
    ):
        """Initialize LCM engine.
        
        Args:
            config: LCM configuration
            agent_id: Agent identifier
            conversation_id: Conversation/session identifier
            chat_model: Model for summarization (optional, will be set later)
            formatter: Formatter for model calls (optional)
            token_counter: Token counter utility
        """
        self.config = config
        self.agent_id = agent_id
        self.conversation_id = conversation_id
        self.chat_model = chat_model
        self.formatter = formatter
        self.token_counter = token_counter
        
        # Initialize database
        self.db = LCMDatabase(config.db_path, config.enable_fts)
        
        # Compaction state
        self._compaction_lock = asyncio.Lock()
        self._last_compaction_tokens = 0
    
    def _blocks_to_text(self, blocks: list) -> str:
        """Serialize blocks to a plain text representation for token counting."""
        text_parts = []
        if isinstance(blocks, list):
            for block in blocks:
                if isinstance(block, dict):
                    block_type = block.get("type", "")
                    if block_type == "text":
                        text_parts.append(block.get("text", ""))
                    elif block_type == "tool_use":
                        tool_name = block.get("name", "?")
                        tool_args = block.get("input", {})
                        args_str = str(tool_args)[:1000]
                        text_parts.append(f"[Tool: {tool_name}] {args_str}")
                    elif block_type == "tool_result":
                        result = block.get("content", "")
                        if isinstance(result, str) and len(result) > 2000:
                            result = result[:2000] + "...[truncated]"
                        text_parts.append(f"[ToolResult] {result}")
                else:
                    text_parts.append(str(block))
        else:
            text_parts.append(str(blocks))
        return " ".join(text_parts)
    
    async def initialize(self) -> None:
        """Initialize the engine (create database tables, etc.)."""
        await self.db.initialize()
        await self.db.get_or_create_conversation(self.conversation_id, self.agent_id)
        logger.info(f"LCM engine initialized for conversation: {self.conversation_id}")
    
    async def ingest(self, messages: list[Msg]) -> None:
        """Ingest messages into the database.
        
        This should be called for every new message in the conversation.
        Messages are persisted with their full content.
        
        Args:
            messages: List of Msg objects to ingest
        """
        await self.initialize()
        
        for msg in messages:
            await self._ingest_message(msg)
        
        logger.debug(f"Ingested {len(messages)} messages into LCM")
    
    async def _ingest_message(self, msg: Msg) -> None:
        """Ingest a single message, serializing content blocks for storage and token estimation."""
        msg_id = msg.id or str(uuid.uuid4())
        try:
            content = self._blocks_to_text(msg.content)
            content_type = "tool" if ("[Tool:" in content or "[ToolResult]" in content) else "text"
            content_json = msg.model_dump_json() if hasattr(msg, 'model_dump_json') else str(msg.content)
        except Exception:
            # Fallback to legacy path on error
            content = "" if not isinstance(msg.content, str) else msg.content
            content_type = "text"
            content_json = msg.model_dump_json() if hasattr(msg, 'model_dump_json') else str(msg.content)
        # Estimate token count
        token_count = 0
        if self.token_counter:
            try:
                token_count = await self.token_counter.count(messages=[], text=content)
            except Exception:
                token_count = len(content) // 4
        await self.db.add_message(
            message_id=msg_id,
            conversation_id=self.conversation_id,
            role=msg.role,
            content=content,
            content_json=content_json,
            content_type=content_type,
            token_count=token_count,
            metadata={"name": msg.name} if msg.name else None,
        )
    
    async def _count_messages_tokens(self, messages: list[Msg]) -> int:
        """Count tokens in a list of messages.
        
        Args:
            messages: Messages to count
             
        Returns:
            Total token count
        """
        total = 0
        for msg in messages:
            try:
                if isinstance(msg.content, str):
                    text = msg.content
                else:
                    text = self._blocks_to_text(msg.content)
            except Exception:
                text = str(msg.content)
            if self.token_counter:
                try:
                    count = await self.token_counter.count(messages=[], text=text)
                    total += count
                except Exception:
                    total += len(text) // 4
            else:
                total += len(text) // 4
        return total
    
    async def check_and_compact(
        self,
        messages: list[Msg],
        max_tokens: int,
    ) -> tuple[list[Msg], bool]:
        """Check if compaction is needed and perform it.
        
        Args:
            messages: Current message list
            max_tokens: Maximum tokens allowed
            
        Returns:
            Tuple of (possibly compacted messages, whether compaction occurred)
        """
        await self.initialize()
        
        # Count tokens
        if not self.token_counter:
            logger.warning("LCM: No token_counter available, skipping compaction check")
            return messages, False
        
        try:
            # Token counter may accept messages or text parameter
            total_tokens = await self._count_messages_tokens(messages)
        except Exception as e:
            logger.warning(f"Failed to count tokens: {e}")
            return messages, False
        
        threshold = int(max_tokens * self.config.context_threshold)
        
        # Force compression if input exceeds max_input_chars
        full_text = ""
        try:
            for m in messages:
                full_text += self._blocks_to_text(m.content) + " "
        except Exception:
            full_text = ""
        char_len = len(full_text)
        max_chars = getattr(self.config, "max_input_chars", 202752)
        if char_len > max_chars:
            logger.info(f"LCM: input length {char_len} exceeds max_input_chars {max_chars}, forcing compression")
            async with self._compaction_lock:
                return await self._do_compaction(messages, max_tokens)
        
        # Log token count for debugging
        logger.info(f"LCM token check: {total_tokens} tokens, threshold={threshold}, max={max_tokens}")
        
        if total_tokens < threshold:
            logger.debug(f"No compaction needed: {total_tokens} < {threshold}")
            return messages, False
        
        async with self._compaction_lock:
            logger.info(f"Starting compaction: {total_tokens} tokens >= {threshold} threshold")
            return await self._do_compaction(messages, max_tokens)
    
    async def _do_compaction(
        self,
        messages: list[Msg],
        max_tokens: int,
    ) -> tuple[list[Msg], bool]:
        """Perform the actual compaction."""
        from .compactor import DAGCompactor
        
        if not self.chat_model:
            logger.warning("No chat model available for compaction")
            return messages, False
        
        compactor = DAGCompactor(
            db=self.db,
            config=self.config,
            conversation_id=self.conversation_id,
            chat_model=self.chat_model,
            formatter=self.formatter,
            token_counter=self.token_counter,
        )
        
        try:
            compacted_messages = await compactor.compact(messages, max_tokens)
            logger.info(f"Compaction complete: {len(messages)} -> {len(compacted_messages)} messages")
            return compacted_messages, True
        except Exception as e:
            logger.exception(f"Compaction failed: {e}")
            return messages, False
    
    async def assemble_context(
        self,
        max_tokens: int,
        prepend_summary: bool = True,
    ) -> tuple[list[Msg], str]:
        """Assemble context for model call.
        
        Combines summaries (if any) with recent raw messages.
        
        Args:
            max_tokens: Maximum tokens for context
            prepend_summary: Whether to include summary at the start
            
        Returns:
            Tuple of (messages, summary_text)
        """
        await self.initialize()
        
        # Get recent messages (fresh tail)
        fresh_messages = await self.db.get_messages(
            conversation_id=self.conversation_id,
            limit=self.config.fresh_tail_count,
            include_compacted=False,
        )
        
        # Get summaries
        summaries = await self.db.get_summaries(self.conversation_id)
        
        summary_text = ""
        if summaries and prepend_summary:
            # Get the highest-level summaries (condensed)
            max_depth = max(s["depth"] for s in summaries) if summaries else 0
            top_summaries = [s for s in summaries if s["depth"] == max_depth]
            
            if top_summaries:
                summary_parts = []
                for s in sorted(top_summaries, key=lambda x: x["created_at"]):
                    summary_parts.append(s["content"])
                summary_text = "\n\n".join(summary_parts)
        
        # Convert to Msg objects
        messages = []
        
        # Add summary as system message if present
        if summary_text:
            from agentscope.message import Msg
            summary_msg = Msg(
                name="system",
                role="system",
                content=[{"type": "text", "text": f"[Previous Context Summary]\n{summary_text}"}],
            )
            messages.append(summary_msg)
        
        # Add fresh messages
        for msg_data in fresh_messages:
            from agentscope.message import Msg
            
            # Try to reconstruct from JSON if available
            content = msg_data.get("content", "")
            content_json = msg_data.get("content_json")
            
            if content_json:
                try:
                    # Parse and use the full content
                    parsed = __import__("json").loads(content_json)
                    # For simplicity, just use the text content
                    if isinstance(parsed, list):
                        texts = []
                        for block in parsed:
                            if isinstance(block, dict) and block.get("type") == "text":
                                texts.append(block.get("text", ""))
                        content = "\n".join(texts)
                except Exception:
                    pass
            
            msg = Msg(
                id=msg_data["id"],
                name=msg_data.get("metadata", {}).get("name", "") if msg_data.get("metadata") else "",
                role=msg_data["role"],
                content=[{"type": "text", "text": content}],
            )
            messages.append(msg)
        
        return messages, summary_text
    
    # ==================== Search & Expansion ====================
    
    async def search(self, query: str, limit: int = 10) -> dict:
        """Search all history (messages and summaries).
        
        Args:
            query: Search query
            limit: Maximum results per category
            
        Returns:
            Dict with 'messages' and 'summaries' lists
        """
        await self.initialize()
        return await self.db.search_all(self.conversation_id, query, limit)
    
    async def grep_messages(self, query: str, limit: int = 10) -> list[dict]:
        """Search messages by content.
        
        Args:
            query: Search query
            limit: Maximum results
            
        Returns:
            List of matching messages
        """
        await self.initialize()
        return await self.db.search_messages(self.conversation_id, query, limit)
    
    async def describe_dag(self) -> dict:
        """Get a description of the current DAG structure.
        
        Returns:
            Dict with DAG statistics and structure info
        """
        await self.initialize()
        
        stats = await self.db.get_stats(self.conversation_id)
        summaries = await self.db.get_summaries(self.conversation_id)
        
        # Group by depth
        by_depth = {}
        for s in summaries:
            depth = s["depth"]
            if depth not in by_depth:
                by_depth[depth] = []
            by_depth[depth].append({
                "id": s["id"][:8],
                "tokens": s["token_count"],
                "created": s["created_at"],
            })
        
        return {
            "conversation_id": self.conversation_id,
            "stats": stats,
            "dag_structure": by_depth,
        }
    
    async def expand_summary(self, summary_id: str) -> list[dict]:
        """Expand a summary to get all original messages.
        
        Args:
            summary_id: ID of the summary to expand
            
        Returns:
            List of original messages
        """
        await self.initialize()
        return await self.db.expand_summary(summary_id)
    
    async def expand_message(self, message_id: str) -> Optional[dict]:
        """Get a specific message by ID.
        
        Args:
            message_id: Message ID
            
        Returns:
            Message dict or None
        """
        # This would need a new database method, for now return None
        return None
    
    # ==================== Utilities ====================
    
    def set_model(
        self,
        chat_model: "ChatModelBase",
        formatter: "FormatterBase",
        token_counter=None,
    ) -> None:
        """Set the model for summarization."""
        self.chat_model = chat_model
        self.formatter = formatter
        self.token_counter = token_counter
    
    async def close(self) -> None:
        """Close database connections."""
        # Database handles its own connections
        pass
