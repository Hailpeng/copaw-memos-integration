# -*- coding: utf-8 -*-
"""MemOS Recall Hook - Automatic memory recall before agent reasoning.

This hook automatically recalls relevant memories from MemOS Cloud
before each agent reasoning cycle, injecting them into the context.
"""
import asyncio
import logging
from typing import TYPE_CHECKING, Any, Optional

from agentscope.message import Msg, TextBlock

if TYPE_CHECKING:
    from ..memory.memory_manager import MemoryManager

logger = logging.getLogger(__name__)


class ConversationManager:
    """Manages conversation IDs with prefix/suffix and reset capabilities."""

    def __init__(
        self,
        prefix: str = "",
        suffix: str = "",
        suffix_mode: str = "none",  # "none" or "counter"
        reset_on_new: bool = True,
    ):
        """Initialize conversation manager.

        Args:
            prefix: Conversation ID prefix
            suffix: Conversation ID suffix
            suffix_mode: "none" for static suffix, "counter" for incrementing
            reset_on_new: Whether to reset counter on new session
        """
        self.prefix = prefix
        self.suffix = suffix
        self.suffix_mode = suffix_mode
        self.reset_on_new = reset_on_new
        self._counter = 0
        self._current_conversation_id = None

    def get_conversation_id(self, base_id: str) -> str:
        """Generate conversation ID with prefix/suffix.

        Args:
            base_id: Base conversation ID (usually session ID)

        Returns:
            Full conversation ID
        """
        parts = []

        if self.prefix:
            parts.append(self.prefix)

        parts.append(base_id)

        if self.suffix:
            if self.suffix_mode == "counter":
                parts.append(f"{self.suffix}{self._counter}")
            else:
                parts.append(self.suffix)

        self._current_conversation_id = "-".join(parts)
        return self._current_conversation_id

    def increment_counter(self):
        """Increment the conversation counter."""
        self._counter += 1

    def reset(self):
        """Reset the counter."""
        self._counter = 0
        self._current_conversation_id = None


class RecallFilter:
    """LLM-based recall filter for filtering low-relevance memories.

    Uses an OpenAI-compatible API to filter recalled memories
    based on relevance to the current query.
    """

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:11434/v1",
        api_key: str = "",
        model: str = "qwen2.5:7b",
        timeout_ms: int = 6000,
        retries: int = 0,
        candidate_limit: int = 30,
        max_item_chars: int = 500,
        fail_open: bool = True,
    ):
        """Initialize recall filter.

        Args:
            base_url: OpenAI-compatible API base URL
            api_key: API key (optional for local models)
            model: Model name for filtering
            timeout_ms: Request timeout in milliseconds
            retries: Number of retries on failure
            candidate_limit: Max candidates per category
            max_item_chars: Max chars per memory item
            fail_open: If True, return all candidates on filter failure
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout_ms = timeout_ms
        self.retries = retries
        self.candidate_limit = candidate_limit
        self.max_item_chars = max_item_chars
        self.fail_open = fail_open

    def _truncate_content(self, content: str) -> str:
        """Truncate content to max chars."""
        if len(content) > self.max_item_chars:
            return content[:self.max_item_chars] + "..."
        return content

    async def _call_llm(self, prompt: str) -> Optional[str]:
        """Call LLM API to filter memories.

        Args:
            prompt: The filter prompt

        Returns:
            LLM response or None on failure
        """
        import httpx

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
            "max_tokens": 1024,
        }

        timeout = self.timeout_ms / 1000.0

        for attempt in range(self.retries + 1):
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.post(
                        f"{self.base_url}/chat/completions",
                        headers=headers,
                        json=payload,
                    )
                    if response.status_code == 200:
                        data = response.json()
                        return data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    else:
                        logger.warning(f"Recall filter API error: {response.status_code}")
            except Exception as e:
                logger.warning(f"Recall filter call failed (attempt {attempt + 1}): {e}")
                if attempt < self.retries:
                    await asyncio.sleep(0.5)

        return None

    async def filter_memories(
        self,
        query: str,
        memories: list[dict],
        preferences: list[dict],
        tool_memories: list[dict],
    ) -> tuple[list[dict], list[dict], list[dict]]:
        """Filter memories based on relevance to query.

        Args:
            query: User query
            memories: List of memory items
            preferences: List of preference items
            tool_memories: List of tool memory items

        Returns:
            Tuple of (filtered_memories, filtered_preferences, filtered_tool_memories)
        """
        if not any([memories, preferences, tool_memories]):
            return [], [], []

        # Build filter prompt
        prompt_parts = [
            "You are a memory relevance filter. Given a user query and a list of memories,",
            "identify which memories are DIRECTLY relevant to answering the query.",
            "",
            f"User Query: {query}",
            "",
        ]

        # Add memories to filter
        all_items = []
        if memories:
            prompt_parts.append("### Memories:")
            for i, mem in enumerate(memories[:self.candidate_limit]):
                value = self._truncate_content(mem.get("memory_value", ""))
                prompt_parts.append(f"[M{i}] {value}")
                all_items.append(("memory", i, mem))

        if preferences:
            prompt_parts.append("\n### Preferences:")
            offset = len(all_items)
            for i, pref in enumerate(preferences[:self.candidate_limit]):
                value = self._truncate_content(pref.get("preference_value", pref.get("memory_value", "")))
                prompt_parts.append(f"[P{i}] {value}")
                all_items.append(("preference", i, pref))

        if tool_memories:
            prompt_parts.append("\n### Tool Memories:")
            offset = len(all_items)
            for i, tm in enumerate(tool_memories[:self.candidate_limit]):
                value = self._truncate_content(tm.get("tool_memory_value", tm.get("memory_value", "")))
                prompt_parts.append(f"[T{i}] {value}")
                all_items.append(("tool_memory", i, tm))

        prompt_parts.extend([
            "",
            "Reply with ONLY the IDs of relevant items (e.g., M0, P2, T1).",
            "Use comma separation. If none are relevant, reply 'none'.",
            "IDs:",
        ])

        prompt = "\n".join(prompt_parts)

        # Call LLM
        response = await self._call_llm(prompt)

        if response is None:
            # Fail open: return all candidates
            if self.fail_open:
                logger.info("Recall filter failed, returning all candidates (fail_open=True)")
                return memories[:self.candidate_limit], preferences[:self.candidate_limit], tool_memories[:self.candidate_limit]
            return [], [], []

        # Parse response
        response = response.strip().lower()
        if response == "none":
            return [], [], []

        kept_ids = set()
        for part in response.split(","):
            part = part.strip()
            if part:
                kept_ids.add(part.upper())

        # Filter items
        filtered_memories = []
        filtered_preferences = []
        filtered_tool_memories = []

        for item_type, idx, item in all_items:
            item_id = f"{item_type[0].upper()}{idx}"
            if item_id in kept_ids:
                if item_type == "memory":
                    filtered_memories.append(item)
                elif item_type == "preference":
                    filtered_preferences.append(item)
                elif item_type == "tool_memory":
                    filtered_tool_memories.append(item)

        logger.debug(f"Recall filter: {len(memories)} -> {len(filtered_memories)} memories, "
                    f"{len(preferences)} -> {len(filtered_preferences)} preferences, "
                    f"{len(tool_memories)} -> {len(filtered_tool_memories)} tool memories")

        return filtered_memories, filtered_preferences, filtered_tool_memories


class MemosRecallHook:
    """Hook for automatic memory recall from MemOS Cloud.

    This hook is called before each agent reasoning cycle (_reasoning method).
    It searches MemOS Cloud for relevant memories based on the user's query
    and injects them into the context as a system message.

    Features:
    - Automatic recall based on user query
    - Conversation-level and global memory support
    - Preference and tool memory extraction
    - Optional LLM-based recall filtering
    - Query prefix for better recall
    - Knowledge base filtering
    - Tags filtering
    - Conversation ID management with prefix/suffix
    - Max item chars to limit memory size
    """

    def __init__(
        self,
        memory_manager: "MemoryManager",
        memory_limit: int = 10,
        preference_limit: int = 5,
        tool_memory_limit: int = 5,
        include_preference: bool = True,
        include_tool_memory: bool = True,
        threshold: float = 0.1,
        max_item_chars: int = 8000,  # Max chars per memory item
        # Phase 1 features
        query_prefix: str = "",
        recall_global: bool = True,
        knowledgebase_ids: list[str] = None,
        tags: list[str] = None,
        # Recall filter
        recall_filter_enabled: bool = False,
        recall_filter_base_url: str = "http://127.0.0.1:11434/v1",
        recall_filter_api_key: str = "",
        recall_filter_model: str = "qwen2.5:7b",
        recall_filter_timeout_ms: int = 6000,
        recall_filter_retries: int = 0,
        recall_filter_candidate_limit: int = 30,
        recall_filter_max_item_chars: int = 500,
        recall_filter_fail_open: bool = True,
        # Phase 3: Conversation management
        conversation_id_prefix: str = "",
        conversation_id_suffix: str = "",
        conversation_suffix_mode: str = "none",
        reset_on_new: bool = True,
    ):
        """Initialize MemOS recall hook.

        Args:
            memory_manager: MemoryManager instance with MemOS client
            memory_limit: Max memories to recall
            preference_limit: Max preferences to recall
            tool_memory_limit: Max tool memories to recall
            include_preference: Whether to include preferences
            include_tool_memory: Whether to include tool memories
            threshold: Minimum similarity threshold
            max_item_chars: Max characters per memory item (default 8000)
            query_prefix: Prefix to add to search query
            recall_global: If True, search globally; if False, limit to conversation
            knowledgebase_ids: List of knowledge base IDs to filter
            tags: List of tags to filter
            recall_filter_enabled: Enable LLM-based recall filtering
            recall_filter_*: Recall filter configuration
            conversation_id_prefix: Prefix for conversation ID
            conversation_id_suffix: Suffix for conversation ID
            conversation_suffix_mode: "none" or "counter"
            reset_on_new: Whether to reset conversation counter on new session
        """
        self.memory_manager = memory_manager
        self.memory_limit = memory_limit
        self.preference_limit = preference_limit
        self.tool_memory_limit = tool_memory_limit
        self.include_preference = include_preference
        self.include_tool_memory = include_tool_memory
        self.threshold = threshold
        self.max_item_chars = max_item_chars
        self.query_prefix = query_prefix
        self.recall_global = recall_global
        self.knowledgebase_ids = knowledgebase_ids or []
        self.tags = tags or []
        self.recall_filter_enabled = recall_filter_enabled

        # Initialize recall filter if enabled
        self.recall_filter = None
        if recall_filter_enabled:
            self.recall_filter = RecallFilter(
                base_url=recall_filter_base_url,
                api_key=recall_filter_api_key,
                model=recall_filter_model,
                timeout_ms=recall_filter_timeout_ms,
                retries=recall_filter_retries,
                candidate_limit=recall_filter_candidate_limit,
                max_item_chars=recall_filter_max_item_chars,
                fail_open=recall_filter_fail_open,
            )

        # Initialize conversation manager
        self.conversation_manager = ConversationManager(
            prefix=conversation_id_prefix,
            suffix=conversation_id_suffix,
            suffix_mode=conversation_suffix_mode,
            reset_on_new=reset_on_new,
        )

    def _extract_user_query(self, messages: list[Msg]) -> Optional[str]:
        """Extract the latest user query from messages.

        Args:
            messages: List of messages

        Returns:
            User query string or None
        """
        for msg in reversed(messages):
            if msg.role == "user":
                content = msg.content
                if isinstance(content, str):
                    return content
                elif isinstance(content, list):
                    for block in content:
                        # TextBlock is a TypedDict, check by dict and type field
                        if isinstance(block, dict) and block.get("type") == "text":
                            return block.get("text", "")
        return None

    def _truncate_text(self, text: str) -> str:
        """Truncate text to max_item_chars.

        Args:
            text: Text to truncate

        Returns:
            Truncated text
        """
        if not text:
            return ""
        if len(text) > self.max_item_chars:
            return text[:self.max_item_chars] + "..."
        return text

    def _format_recall_context(
        self,
        memories: list[dict],
        preferences: list[dict],
        tool_memories: list[dict],
    ) -> str:
        """Format recalled memories into context string.

        Args:
            memories: List of memory items
            preferences: List of preference items
            tool_memories: List of tool memory items

        Returns:
            Formatted context string
        """
        parts = []

        if memories:
            parts.append("### 📝 Relevant Memories")
            for mem in memories[:self.memory_limit]:
                key = mem.get("memory_key", "")
                value = self._truncate_text(mem.get("memory_value", ""))
                confidence = mem.get("confidence", 0)
                if value:
                    parts.append(f"- **{key}** (confidence: {confidence:.2f})")
                    parts.append(f"  {value}")

        if preferences and self.include_preference:
            parts.append("\n### 👤 User Preferences")
            for pref in preferences[:self.preference_limit]:
                key = pref.get("preference_key", pref.get("memory_key", ""))
                value = self._truncate_text(pref.get("preference_value", pref.get("memory_value", "")))
                if value:
                    parts.append(f"- {key}: {value}")

        if tool_memories and self.include_tool_memory:
            parts.append("\n### 🔧 Tool Usage History")
            for tm in tool_memories[:self.tool_memory_limit]:
                value = self._truncate_text(tm.get("tool_memory_value", tm.get("memory_value", "")))
                if value:
                    parts.append(f"- {value}")

        if not parts:
            return ""

        return "\n".join(parts)

    async def __call__(
        self,
        agent,
        kwargs: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Pre-reasoning hook to recall memories from MemOS Cloud.

        Args:
            agent: The agent instance
            kwargs: Input arguments to the _reasoning method

        Returns:
            None (hook doesn't modify kwargs, but may add to memory)
        """
        if not self.memory_manager.memos_enabled:
            return None

        try:
            # Get messages from kwargs
            messages = kwargs.get("messages", [])
            if not messages:
                # Try to get from agent memory
                messages = await agent.memory.get_memory()

            # Extract user query
            query = self._extract_user_query(messages)
            if not query:
                return None

            # Add query prefix if configured
            if self.query_prefix:
                query = f"{self.query_prefix} {query}"

            # Search MemOS Cloud
            client = self.memory_manager._memos_client
            if not client:
                return None

            # Determine conversation_id based on recall_global setting
            conversation_id = None
            if not self.recall_global:
                conversation_id = self.memory_manager.agent_id

            # Get agent_id for multi-agent support
            agent_id = getattr(agent, 'agent_id', None)

            # Build search parameters
            search_params = {
                "query": query,
                "top_k": self.memory_limit * 2,
                "memory_limit": self.memory_limit,
                "preference_limit": self.preference_limit,
                "tool_memory_limit": self.tool_memory_limit,
                "include_preference": self.include_preference,
                "include_tool_memory": self.include_tool_memory,
                "conversation_id": conversation_id,
                "agent_id": agent_id,
                "threshold": self.threshold,
            }

            # Add knowledge base filter if configured
            if self.knowledgebase_ids:
                search_params["knowledgebase_ids"] = self.knowledgebase_ids

            # Add tags filter if configured
            if self.tags:
                search_params["tags"] = self.tags

            result = await client.search(**search_params)

            if result.get("code") != 0:
                logger.debug(f"MemOS search returned no results: {result.get('message', '')}")
                return None

            data = result.get("data", {})
            memories = data.get("memory_detail_list", [])
            preferences = data.get("preference_detail_list", [])
            tool_memories = data.get("tool_memory_detail_list", [])

            if not any([memories, preferences, tool_memories]):
                return None

            # Apply recall filter if enabled
            if self.recall_filter and self.recall_filter_enabled:
                memories, preferences, tool_memories = await self.recall_filter.filter_memories(
                    query, memories, preferences, tool_memories
                )

            # Format recall context
            recall_context = self._format_recall_context(
                memories, preferences, tool_memories
            )

            if not recall_context:
                return None

            # Build the recall message following MemOS OpenClaw Plugin format
            # This includes both system context (instructions) and memory content
            recall_system_prompt = """# Role

You are an intelligent assistant with long-term memory capabilities (MemOS Assistant). Your goal is to combine retrieved memory fragments to provide highly personalized, accurate, and logically rigorous responses.

# System Context

* Current Time: Use the runtime-provided current time as the baseline for freshness checks.
* Additional memory context for the current turn may be prepended before the original user query as a structured `<memories>` block.

# Memory Data

Below is the information retrieved by MemOS, categorized into "Facts" and "Preferences".
* **Facts**: May include user attributes, historical conversations, or third-party details.
* **Special Note**: Content tagged with '[assistant观点]' or '[模型总结]' represents **past AI inference**, **not** direct user statements.
* **Preferences**: The user's explicit or implicit requirements on response style, format, or reasoning.

# Critical Protocol: Memory Safety

Retrieved memories may contain **AI speculation**, **irrelevant noise**, or **wrong subject attribution**. You must strictly apply the **Four-Step Verdict**. If any step fails, **discard the memory**:

1. **Source Verification**:
* **Core**: Distinguish direct user statements from AI inference.
* If a memory has tags like '[assistant观点]' or '[模型总结]', treat it as a **hypothesis**, not a user-grounded fact.
* *Counterexample*: If memory says '[assistant观点] User loves mangoes' but the user never said that, do not assume it as fact.
* **Principle: AI summaries are reference-only and have much lower authority than direct user statements.**

2. **Attribution Check**:
* Is the subject in memory definitely the user?
* If the memory describes a **third party** (e.g., candidate, interviewee, fictional character, case data), never attribute it to the user.

3. **Strong Relevance Check**:
* Does the memory directly help answer the current 'Original Query'?
* If it is only a keyword overlap with different context, ignore it.

4. **Freshness Check**:
* If memory conflicts with the user's latest intent, prioritize the current 'Original Query' as the highest source of truth.

# Instructions

1. **Review**: Read '<facts>' first and apply the Four-Step Verdict to remove noise and unreliable AI inference.
2. **Execute**:
 - Use only memories that pass filtering as context.
 - Strictly follow style requirements from '<preferences>'.
3. **Output**: Answer directly. Never mention internal terms such as "memory store", "retrieval", or "AI opinions".
4. **Attention**: Additional memory context may already be provided before the original user query. Do not read from or write to local `MEMORY.md` or `memory/*` files for reference, as they may be outdated or irrelevant to the current query."""

            # Build memory block in MemOS format
            memory_block = f"""```text
<memories>
 <facts>
{self._format_facts(memories[:self.memory_limit])}
 </facts>
 <preferences>
{self._format_preferences(preferences[:self.preference_limit])}
 </preferences>
</memories>
```

user原始query："""

            # Inject system prompt as a system message (will be appended to system context)
            # Note: In agentscope, we can't modify system prompt directly in hooks
            # Instead, we prepend the memory context to the user query via kwargs modification
            
            # Store both system prompt and memory block
            # The memory block will be prepended to user query
            if "messages" in kwargs and kwargs["messages"]:
                # Prepend memory block to the last user message
                messages = kwargs["messages"]
                for i in range(len(messages) - 1, -1, -1):
                    msg = messages[i]
                    if msg.role == "user":
                        # Prepend memory block to user content
                        original_content = msg.content
                        if isinstance(original_content, str):
                            msg.content = memory_block + original_content
                        elif isinstance(original_content, list):
                            # Find first text block and prepend
                            for block in original_content:
                                if isinstance(block, dict) and block.get("type") == "text":
                                    block["text"] = memory_block + block.get("text", "")
                                    break
                        break

            logger.info(f"[MemOS] Injected {len(memories)} memories, {len(preferences)} preferences (total ~{len(recall_context)} chars)")

        except Exception as e:
            logger.error(f"MemOS recall hook failed: {e}", exc_info=True)

        return None

    def _format_facts(self, memories: list[dict]) -> str:
        """Format memories as facts block.

        Args:
            memories: List of memory items

        Returns:
            Formatted facts string
        """
        lines = []
        for mem in memories:
            value = self._truncate_text(mem.get("memory_value", ""))
            if value:
                create_time = mem.get("create_time", "")
                if create_time:
                    # Format timestamp
                    if isinstance(create_time, (int, float)):
                        from datetime import datetime
                        try:
                            dt = datetime.fromtimestamp(create_time / 1000)
                            time_str = dt.strftime("%Y-%m-%d %H:%M")
                        except:
                            time_str = ""
                    else:
                        time_str = str(create_time)
                    if time_str:
                        lines.append(f" -[{time_str}] {value}")
                    else:
                        lines.append(f" - {value}")
                else:
                    lines.append(f" - {value}")
        return "\n".join(lines)

    def _format_preferences(self, preferences: list[dict]) -> str:
        """Format preferences as preferences block.

        Args:
            preferences: List of preference items

        Returns:
            Formatted preferences string
        """
        lines = []
        for pref in preferences:
            value = self._truncate_text(pref.get("preference", pref.get("preference_value", "")))
            if value:
                pref_type = pref.get("preference_type", "")
                type_label = f" [{pref_type}]" if pref_type else ""
                lines.append(f" -{type_label} {value}")
        return "\n".join(lines)


class MemosAddHook:
    """Hook for automatic memory addition to MemOS Cloud.

    This hook is called after each agent response cycle.
    It captures the conversation and adds it to MemOS Cloud for
    future recall.

    Features:
    - Automatic capture of conversations
    - Last turn or full session capture strategies
    - Configurable throttling
    - Assistant response inclusion option
    - Tags support
    - Async mode
    - Multi-agent support
    """

    def __init__(
        self,
        memory_manager: "MemoryManager",
        capture_strategy: str = "last_turn",  # "last_turn" or "full_session"
        include_assistant: bool = False,
        throttle_ms: int = 0,  # Minimum time between captures
        max_message_chars: int = 2000,
        tags: list[str] = None,
        async_mode: bool = True,
        multi_agent_mode: bool = False,
    ):
        """Initialize MemOS add hook.

        Args:
            memory_manager: MemoryManager instance with MemOS client
            capture_strategy: "last_turn" or "full_session"
            include_assistant: Whether to include assistant responses
            throttle_ms: Minimum milliseconds between captures
            max_message_chars: Max characters per message
            tags: List of tags to add to stored messages
            async_mode: If True, store asynchronously without blocking
            multi_agent_mode: If True, capture agent_id for multi-agent isolation
        """
        self.memory_manager = memory_manager
        self.capture_strategy = capture_strategy
        self.include_assistant = include_assistant
        self.throttle_ms = throttle_ms
        self.max_message_chars = max_message_chars
        self.tags = tags or []
        self.async_mode = async_mode
        self.multi_agent_mode = multi_agent_mode
        self._last_capture_time = 0

    def _extract_messages(self, messages: list[Msg]) -> list[dict]:
        """Extract messages for MemOS storage with multimodal support.

        Supports:
        - Text content: {"type": "text", "text": "..."}
        - Image URL: {"type": "image_url", "image_url": {"url": "..."}}
        - Image Base64: {"type": "image_url", "image_url": {"url": "data:image/...;base64,..."}}
        - File URL: {"type": "file", "file": {"file_data": "url"}}
        - File Base64: {"type": "file", "file": {"file_data": "base64..."}}

        Args:
            messages: List of Msg objects

        Returns:
            List of {role, content} dicts with multimodal support
        """
        result = []

        if self.capture_strategy == "last_turn":
            # Find last user message and everything after
            last_user_idx = -1
            for i, msg in enumerate(reversed(messages)):
                if msg.role == "user":
                    last_user_idx = len(messages) - 1 - i
                    break

            if last_user_idx >= 0:
                messages = messages[last_user_idx:]

        for msg in messages:
            if msg.role not in ("user", "assistant"):
                continue

            if msg.role == "assistant" and not self.include_assistant:
                continue

            content = msg.content
            if isinstance(content, str):
                # Plain text content
                text = content
                if len(text) > self.max_message_chars:
                    text = text[:self.max_message_chars] + "..."
                if text.strip():
                    result.append({"role": msg.role, "content": text})
            elif isinstance(content, list):
                # Check if multimodal content
                has_multimodal = any(
                    isinstance(block, dict) and block.get("type") in ("image_url", "image", "file")
                    for block in content
                )

                if has_multimodal:
                    # Build multimodal content array
                    content_parts = []
                    for block in content:
                        if isinstance(block, dict):
                            block_type = block.get("type")
                            if block_type == "text":
                                text = block.get("text", "")
                                if len(text) > self.max_message_chars:
                                    text = text[:self.max_message_chars] + "..."
                                content_parts.append({"type": "text", "text": text})
                            elif block_type == "image_url":
                                # Image URL or base64
                                image_url = block.get("image_url", {})
                                url = image_url.get("url", "")
                                if url:
                                    content_parts.append({
                                        "type": "image_url",
                                        "image_url": {"url": url}
                                    })
                            elif block_type == "image":
                                # Image block from agentscope
                                url = block.get("url", "")
                                if url:
                                    content_parts.append({
                                        "type": "image_url",
                                        "image_url": {"url": url}
                                    })
                            elif block_type == "file":
                                # File block
                                file_data = block.get("file", {}).get("file_data", "")
                                if file_data:
                                    content_parts.append({
                                        "type": "file",
                                        "file": {"file_data": file_data}
                                    })

                    if content_parts:
                        result.append({"role": msg.role, "content": content_parts})
                else:
                    # Text-only content
                    texts = []
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            texts.append(block.get("text", ""))
                    text = "\n".join(texts)
                    if len(text) > self.max_message_chars:
                        text = text[:self.max_message_chars] + "..."
                    if text.strip():
                        result.append({"role": msg.role, "content": text})

        return result

    async def _add_to_memos(
        self,
        client,
        messages: list[dict],
        conversation_id: str,
        agent_id: Optional[str] = None,
    ):
        """Add messages to MemOS Cloud with multimodal support.

        Args:
            client: MemOS client
            messages: List of message dicts (may contain multimodal content)
            conversation_id: Conversation ID
            agent_id: Optional agent ID for multi-agent mode
        """
        # Check if any message has multimodal content
        has_multimodal = any(
            isinstance(msg.get("content"), list)
            for msg in messages
        )

        try:
            if has_multimodal:
                # Use multimodal API
                result = await client.add_multimodal_message(
                    messages=messages,
                    conversation_id=conversation_id,
                    source="copaw-auto",
                    agent_id=agent_id if self.multi_agent_mode else None,
                    tags=self.tags if self.tags else None,
                    async_mode=True,
                )
            else:
                # Use simple API for text-only
                for msg in messages:
                    params = {
                        "content": msg["content"],
                        "role": msg["role"],
                        "conversation_id": conversation_id,
                        "source": "copaw-auto",
                    }

                    if self.tags:
                        params["tags"] = self.tags

                    if self.multi_agent_mode and agent_id:
                        params["agent_id"] = agent_id

                    result = await client.add_message(**params)

            if result.get("code") == 0:
                task_id = result.get("data", {}).get("task_id", "")
                logger.debug(f"Added messages to MemOS: {task_id}")
            else:
                logger.warning(f"Failed to add to MemOS: {result.get('message', '')}")

        except Exception as e:
            logger.error(f"Failed to add messages to MemOS: {e}")

    async def __call__(
        self,
        agent,
        kwargs: dict[str, Any],
        output: Optional[Msg] = None,
    ) -> dict[str, Any] | None:
        """Post-response hook to add conversation to MemOS Cloud.

        Args:
            agent: The agent instance
            kwargs: Context from the response cycle
            output: The reply message from the agent (passed by post_reply hook)

        Returns:
            None
        """
        if not self.memory_manager.memos_enabled:
            return None

        try:
            import time

            # Check throttle
            current_time = int(time.time() * 1000)
            if self.throttle_ms > 0 and current_time - self._last_capture_time < self.throttle_ms:
                return None

            # Get messages from agent memory
            messages = await agent.memory.get_memory()
            if not messages:
                return None

            # Extract messages for storage
            memos_messages = self._extract_messages(messages)
            if not memos_messages:
                return None

            # Get MemOS client
            client = self.memory_manager._memos_client
            if not client:
                return None

            # Get conversation_id
            conversation_id = self.memory_manager.agent_id

            # Get agent_id for multi-agent mode
            agent_id = None
            if self.multi_agent_mode:
                agent_id = getattr(agent, 'agent_id', None)
                # Skip default "main" agent for backwards compatibility
                if agent_id == "main":
                    agent_id = None

            # Store messages
            if self.async_mode:
                # Fire and forget
                asyncio.create_task(
                    self._add_to_memos(client, memos_messages, conversation_id, agent_id)
                )
                self._last_capture_time = current_time
            else:
                # Synchronous
                await self._add_to_memos(client, memos_messages, conversation_id, agent_id)
                self._last_capture_time = current_time

        except Exception as e:
            logger.error(f"MemOS add hook failed: {e}", exc_info=True)

        return None