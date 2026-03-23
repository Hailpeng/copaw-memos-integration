# -*- coding: utf-8 -*-
"""DAG Compactor for LCM.

Implements DAG-based summarization:
1. Leaf compaction: Summarize oldest messages into leaf summaries
2. Condensation: Combine multiple leaf summaries into higher-level nodes
"""
import asyncio
import logging
import uuid
from typing import TYPE_CHECKING, Optional

from agentscope.message import Msg, TextBlock

from .database import LCMDatabase
from .config import LCMConfig

if TYPE_CHECKING:
    from agentscope.model import ChatModelBase
    from agentscope.formatter import FormatterBase

logger = logging.getLogger(__name__)

# Summarization prompts
LEAF_SUMMARY_PROMPT = """Please summarize the following conversation segment. Capture:
1. Key decisions and conclusions
2. Important facts mentioned
3. Any pending tasks or questions

Keep the summary concise but informative. Target length: about {target_tokens} tokens.

Conversation:
{conversation}

Provide only the summary, no additional commentary."""

CONDENSED_SUMMARY_PROMPT = """Please combine and condense the following summaries into a single, higher-level summary.

Target length: about {target_tokens} tokens.

Summaries to combine:
{summaries}

Provide only the combined summary, no additional commentary."""


class DAGCompactor:
    r"""DAG-based compactor for LCM.
    
    Implements a two-level compaction strategy:
    1. Leaf compaction: Group raw messages into leaf summaries
    2. Condensation: Combine summaries into higher-level nodes
    
    The resulting DAG structure looks like:
    
    [Condensed-2] (depth=2)
       /        \
    [C-1a]     [C-1b] (depth=1)
     /|\        /|\
    [L1][L2]   [L3][L4] (depth=0, leaf summaries)
    |   |      |   |
    M1-M8 M9-M16 M17-M24 M25-M32 (original messages)
    """
    
    def __init__(
        self,
        db: LCMDatabase,
        config: LCMConfig,
        conversation_id: str,
        chat_model: "ChatModelBase",
        formatter: Optional["FormatterBase"] = None,
        token_counter=None,
    ):
        """Initialize compactor.
        
        Args:
            db: Database instance
            config: LCM configuration
            conversation_id: Conversation to compact
            chat_model: Model for summarization
            formatter: Formatter for model calls
            token_counter: Token counter utility
        """
        self.db = db
        self.config = config
        self.conversation_id = conversation_id
        self.chat_model = chat_model
        self.formatter = formatter
        self.token_counter = token_counter
    
    async def compact(
        self,
        messages: list[Msg],
        max_tokens: int,
    ) -> list[Msg]:
        """Perform compaction on messages.
        
        Args:
            messages: Current message list
            max_tokens: Maximum tokens allowed
            
        Returns:
            Compacted message list
        """
        # 1. Identify messages to compact (preserve fresh tail)
        fresh_count = self.config.fresh_tail_count
        if len(messages) <= fresh_count:
            logger.info("Not enough messages to compact")
            return messages
        
        messages_to_compact = messages[:-fresh_count]
        fresh_messages = messages[-fresh_count:]
        
        # 2. Perform leaf compaction
        summary = await self._compact_leaf(messages_to_compact)
        
        if not summary:
            logger.warning("Leaf compaction failed, returning original messages")
            return messages
        
        # 3. Check if condensation is needed
        await self._maybe_condense()
        
        # 4. Assemble result: summary + fresh messages
        result = []
        
        # Add summary as a system message
        summary_msg = Msg(
            name="system",
            role="system",
            content=[TextBlock(type="text", text=f"[Context Summary]\n{summary['content']}")],
            # Note: Msg doesn't accept 'id' parameter, summary id is stored in DB
        )
        result.append(summary_msg)
        
        # Add fresh messages
        result.extend(fresh_messages)
        
        return result
    
    async def _compact_leaf(self, messages: list[Msg]) -> Optional[dict]:
        """Create a leaf summary from messages.
        
        Args:
            messages: Messages to compact
            
        Returns:
            Summary dict or None on failure
        """
        # Group messages into chunks
        chunks = self._chunk_messages(messages, self.config.leaf_chunk_tokens)
        
        summaries_created = []
        
        for chunk in chunks:
            summary = await self._summarize_chunk(chunk, is_leaf=True)
            if summary:
                summaries_created.append(summary)
        
        if not summaries_created:
            return None
        
        # If only one summary, return it
        if len(summaries_created) == 1:
            return summaries_created[0]
        
        # Multiple summaries created, maybe condense them
        if len(summaries_created) >= self.config.condensed_min_fanout:
            condensed = await self._condense_summaries(summaries_created, depth=1)
            return condensed
        
        # Return the last summary (most recent)
        return summaries_created[-1]
    
    def _chunk_messages(
        self,
        messages: list[Msg],
        max_tokens: int,
    ) -> list[list[Msg]]:
        """Split messages into chunks by token count."""
        if not self.token_counter:
            # Simple chunking by count
            chunk_size = 8  # Default
            return [
                messages[i:i + chunk_size]
                for i in range(0, len(messages), chunk_size)
            ]
        
        chunks = []
        current_chunk = []
        current_tokens = 0
        
        for msg in messages:
            try:
                msg_tokens = asyncio.get_event_loop().run_until_complete(
                    self.token_counter.count(messages=[msg])
                )
            except Exception:
                msg_tokens = 500  # Estimate
            
            if current_tokens + msg_tokens > max_tokens and current_chunk:
                chunks.append(current_chunk)
                current_chunk = []
                current_tokens = 0
            
            current_chunk.append(msg)
            current_tokens += msg_tokens
        
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks
    
    async def _summarize_chunk(
        self,
        messages: list[Msg],
        is_leaf: bool = True,
    ) -> Optional[dict]:
        """Summarize a chunk of messages using LLM.
        
        Args:
            messages: Messages to summarize
            is_leaf: Whether this is a leaf summary
            
        Returns:
            Summary dict or None on failure
        """
        # Format conversation for summarization
        conversation_text = self._format_messages_for_summary(messages)
        
        target_tokens = (
            self.config.leaf_target_tokens if is_leaf
            else self.config.condensed_target_tokens
        )
        
        prompt = LEAF_SUMMARY_PROMPT.format(
            target_tokens=target_tokens,
            conversation=conversation_text,
        )
        
        try:
            # Call LLM for summarization
            summary_text = await self._call_llm(prompt)
            
            if not summary_text:
                return None
            
            # Create summary record
            summary_id = str(uuid.uuid4())
            message_ids = [m.id for m in messages if m.id]
            
            # Count tokens in summary
            summary_tokens = len(summary_text) // 4  # Rough estimate
            if self.token_counter:
                try:
                    summary_tokens = await self.token_counter.count(text=summary_text)
                except Exception:
                    pass
            
            # Save to database
            await self.db.create_summary(
                summary_id=summary_id,
                conversation_id=self.conversation_id,
                content=summary_text,
                depth=0 if is_leaf else 1,
                source_message_ids=message_ids,
                token_count=summary_tokens,
            )
            
            # Mark messages as compacted
            if message_ids:
                await self.db.mark_messages_compacted(message_ids, summary_id)
            
            logger.info(f"Created {'leaf' if is_leaf else 'condensed'} summary: {summary_id[:8]}")
            
            return {
                "id": summary_id,
                "content": summary_text,
                "token_count": summary_tokens,
                "depth": 0 if is_leaf else 1,
            }
            
        except Exception as e:
            logger.exception(f"Failed to summarize chunk: {e}")
            return None
    
    async def _condense_summaries(
        self,
        summaries: list[dict],
        depth: int = 1,
    ) -> Optional[dict]:
        """Combine multiple summaries into a higher-level summary.
        
        Args:
            summaries: Summaries to combine
            depth: Target depth for the new summary
            
        Returns:
            New condensed summary or None
        """
        if len(summaries) < self.config.condensed_min_fanout:
            return None
        
        summaries_text = "\n\n---\n\n".join(
            f"Summary {i+1}:\n{s['content']}"
            for i, s in enumerate(summaries)
        )
        
        prompt = CONDENSED_SUMMARY_PROMPT.format(
            target_tokens=self.config.condensed_target_tokens,
            summaries=summaries_text,
        )
        
        try:
            condensed_text = await self._call_llm(prompt)
            
            if not condensed_text:
                return None
            
            summary_id = str(uuid.uuid4())
            summary_ids = [s["id"] for s in summaries]
            
            summary_tokens = len(condensed_text) // 4
            
            await self.db.create_summary(
                summary_id=summary_id,
                conversation_id=self.conversation_id,
                content=condensed_text,
                depth=depth,
                source_summary_ids=summary_ids,
                token_count=summary_tokens,
            )
            
            # Update parent relationships
            for sid in summary_ids:
                # This would require an update method in database
                pass
            
            logger.info(f"Created condensed summary (depth={depth}): {summary_id[:8]}")
            
            return {
                "id": summary_id,
                "content": condensed_text,
                "token_count": summary_tokens,
                "depth": depth,
            }
            
        except Exception as e:
            logger.exception(f"Failed to condense summaries: {e}")
            return None
    
    async def _maybe_condense(self) -> None:
        """Check if condensation is needed and perform it."""
        # Get leaf summaries
        summaries = await self.db.get_summaries(self.conversation_id, depth=0)
        
        if len(summaries) >= self.config.condensed_min_fanout:
            # Get summaries without parents
            parentless = [s for s in summaries if not s.get("parent_id")]
            
            if len(parentless) >= self.config.condensed_min_fanout:
                await self._condense_summaries(parentless, depth=1)
    
    async def _call_llm(self, prompt: str) -> Optional[str]:
        """Call the LLM with a prompt.
        
        Args:
            prompt: Prompt to send
            
        Returns:
            Generated text or None
        """
        try:
            # Create a message for the model
            msg = Msg(
                name="user",
                role="user",
                content=[{"type": "text", "text": prompt}],
            )
            
            # Format if formatter available
            if self.formatter:
                formatted = self.formatter.format([msg])
            else:
                formatted = [{"role": "user", "content": prompt}]
            
            # Call model
            response = self.chat_model(formatted)
            
            # Extract text
            if hasattr(response, "content"):
                if isinstance(response.content, str):
                    return response.content
                elif isinstance(response.content, list):
                    texts = []
                    for block in response.content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            texts.append(block.get("text", ""))
                        elif isinstance(block, str):
                            texts.append(block)
                    return "\n".join(texts)
            
            return str(response)
            
        except Exception as e:
            logger.exception(f"LLM call failed: {e}")
            return None
    
    def _format_messages_for_summary(self, messages: list[Msg]) -> str:
        """Format messages for summarization prompt."""
        lines = []
        
        for msg in messages:
            role = msg.role.upper()
            content = ""
            
            if isinstance(msg.content, str):
                content = msg.content
            elif isinstance(msg.content, list):
                text_parts = []
                for block in msg.content:
                    # Handle TypedDict-style blocks
                    if isinstance(block, dict):
                        if block.get("type") == "text":
                            text_parts.append(block.get("text", ""))
                    else:
                        try:
                            if hasattr(block, 'type') and block.type == "text":
                                text_parts.append(block.text if hasattr(block, 'text') else str(block))
                        except Exception:
                            text_parts.append(str(block))
                content = "\n".join(text_parts)
            
            # Truncate very long content
            if len(content) > 2000:
                content = content[:2000] + "...[truncated]"
            
            lines.append(f"[{role}]: {content}")
        
        return "\n\n".join(lines)