# -*- coding: utf-8 -*-
# pylint: disable=too-many-branches
"""Memory Manager for CoPaw agents with MemOS Cloud integration.

Extends ReMeLight to provide memory management capabilities including:
- Memory compaction for long conversations via compact_memory()
- Memory summarization with file operation tools via summary_memory()
- In-memory memory retrieval via get_in_memory_memory()
- Configurable vector search and full-text search backends
- MemOS Cloud integration for cross-session persistent memory
"""
import asyncio
import json
import logging
import os
import platform
from pathlib import Path
from typing import Any, Optional

import httpx

from agentscope.formatter import FormatterBase
from agentscope.message import Msg, TextBlock
from agentscope.model import ChatModelBase
from agentscope.tool import Toolkit, ToolResponse
from copaw.agents.model_factory import create_model_and_formatter
from copaw.agents.tools import read_file, write_file, edit_file
from copaw.agents.utils import get_copaw_token_counter
from copaw.config.config import load_agent_config

logger = logging.getLogger(__name__)

# Try to import reme, log warning if it fails
try:
    from reme.reme_light import ReMeLight

    _REME_AVAILABLE = True

except ImportError as e:
    _REME_AVAILABLE = False
    logger.warning(f"reme package not installed. {e}")

    class ReMeLight:  # type: ignore
        """Placeholder when reme is unavailable."""

        async def start(self) -> None:
            """No-op start when reme is unavailable."""


class MemOSClient:
    """MemOS Cloud API client for memory operations.

    Provides semantic memory search and storage via MemOS Cloud API.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://memos.memtensor.cn/api/openmem/v1",
        user_id: str = "copaw-user",
        timeout: float = 10.0,
    ):
        """Initialize MemOS client.

        Args:
            api_key: MemOS API key (starts with 'mpg-')
            base_url: MemOS API base URL
            user_id: User identifier for memory isolation
            timeout: Request timeout in seconds
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.user_id = user_id
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    def _get_headers(self) -> dict:
        """Get authorization headers."""
        return {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": "application/json",
        }

    async def search(
        self,
        query: str,
        top_k: int = 10,
        threshold: float = 0.1,
        memory_limit: int = 10,
        preference_limit: int = 5,
        tool_memory_limit: int = 5,
        include_preference: bool = True,
        include_tool_memory: bool = True,
        knowledgebase_ids: Optional[list[str]] = None,
        conversation_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        relativity: float = 0.5,
    ) -> dict:
        """Search memories semantically with full MemOS API support.

        Args:
            query: Search query string
            top_k: Maximum number of results (deprecated, use memory_limit)
            threshold: Minimum similarity score
            memory_limit: Max memories to return
            preference_limit: Max preferences to return
            tool_memory_limit: Max tool memories to return
            include_preference: Whether to include preferences
            include_tool_memory: Whether to include tool memories
            knowledgebase_ids: List of knowledgebase IDs to search
            conversation_id: Filter by conversation ID
            agent_id: Filter by agent ID
            relativity: Relevance threshold (0-1)

        Returns:
            API response with memory_detail_list, preference_detail_list, tool_memory_detail_list
        """
        client = await self._get_client()
        payload = {
            "user_id": self.user_id,
            "query": query,
            "top_k": top_k,
            "threshold": threshold,
            "memory_limit_number": memory_limit,
            "preference_limit_number": preference_limit,
            "tool_memory_limit_number": tool_memory_limit,
            "include_preference": include_preference,
            "include_tool_memory": include_tool_memory,
            "relativity": relativity,
        }

        if knowledgebase_ids:
            payload["knowledgebase_ids"] = knowledgebase_ids
        if conversation_id:
            payload["conversation_id"] = conversation_id
        if agent_id:
            payload["agent_id"] = agent_id

        try:
            response = await client.post(
                f"{self.base_url}/search/memory",
                headers=self._get_headers(),
                json=payload,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"MemOS search failed: {e}")
            return {"code": -1, "message": str(e), "data": {}}
        except Exception as e:
            logger.error(f"MemOS search error: {e}")
            return {"code": -1, "message": str(e), "data": {}}

    async def add_message(
        self,
        content: str,
        role: str = "user",
        conversation_id: Optional[str] = None,
        source: str = "copaw",
        agent_id: Optional[str] = None,
        app_id: Optional[str] = None,
        tags: Optional[list[str]] = None,
        info: Optional[dict] = None,
        messages: Optional[list[dict]] = None,
        allow_public: bool = False,
        async_mode: bool = True,
    ) -> dict:
        """Add a memory message to MemOS with full API support.

        Args:
            content: Memory content to store (used if messages not provided)
            role: Message role (user/assistant)
            conversation_id: Optional conversation ID for grouping
            source: Source identifier
            agent_id: Agent identifier for filtering
            app_id: Application identifier
            tags: List of tags for categorization
            info: Additional metadata dict
            messages: Full messages array (overrides content/role)
            allow_public: Whether to allow public access
            async_mode: Whether to process asynchronously

        Returns:
            API response with task_id
        """
        client = await self._get_client()

        # Build payload
        payload = {
            "user_id": self.user_id,
            "source": source,
            "allow_public": allow_public,
            "async_mode": async_mode,
        }

        # Use messages array if provided, otherwise build from content/role
        if messages:
            payload["messages"] = messages
        else:
            payload["messages"] = [{"role": role, "content": content}]

        if conversation_id:
            payload["conversation_id"] = conversation_id
        if agent_id:
            payload["agent_id"] = agent_id
        if app_id:
            payload["app_id"] = app_id
        if tags:
            payload["tags"] = tags
        if info:
            payload["info"] = info

        try:
            response = await client.post(
                f"{self.base_url}/add/message",
                headers=self._get_headers(),
                json=payload,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"MemOS add_message failed: {e}")
            return {"code": -1, "message": str(e), "data": {}}
        except Exception as e:
            logger.error(f"MemOS add_message error: {e}")
            return {"code": -1, "message": str(e), "data": {}}

    async def add_feedback(
        self,
        feedback_content: str,
        conversation_id: Optional[str] = None,
        allow_knowledgebase_ids: Optional[list[str]] = None,
    ) -> dict:
        """Add natural language feedback to update memories.

        This allows users to correct or update memories using natural language
        without manually locating specific memory entries.

        Args:
            feedback_content: Natural language feedback content
            conversation_id: Optional conversation ID for context
            allow_knowledgebase_ids: List of knowledgebase IDs that can be modified

        Returns:
            API response
        """
        client = await self._get_client()
        payload = {
            "user_id": self.user_id,
            "feedback_content": feedback_content,
        }

        if conversation_id:
            payload["conversation_id"] = conversation_id
        if allow_knowledgebase_ids:
            payload["allow_knowledgebase_ids"] = allow_knowledgebase_ids

        try:
            response = await client.post(
                f"{self.base_url}/add/feedback",
                headers=self._get_headers(),
                json=payload,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"MemOS add_feedback failed: {e}")
            return {"code": -1, "message": str(e), "data": {}}
        except Exception as e:
            logger.error(f"MemOS add_feedback error: {e}")
            return {"code": -1, "message": str(e), "data": {}}

    async def add_multimodal_message(
        self,
        messages: list[dict],
        conversation_id: Optional[str] = None,
        source: str = "copaw",
        agent_id: Optional[str] = None,
        tags: Optional[list[str]] = None,
        async_mode: bool = True,
    ) -> dict:
        """Add messages with multimodal content (images, files).

        Supports:
        - Text content: {"type": "text", "text": "..."}
        - Image URL: {"type": "image_url", "image_url": {"url": "..."}}
        - Image Base64: {"type": "image_url", "image_url": {"url": "data:image/...;base64,..."}}
        - File URL: {"type": "file", "file": {"file_data": "url"}}
        - File Base64: {"type": "file", "file": {"file_data": "base64..."}}

        Args:
            messages: List of message dicts with multimodal content
            conversation_id: Optional conversation ID
            source: Source identifier
            agent_id: Agent identifier
            tags: List of tags
            async_mode: Whether to process asynchronously

        Returns:
            API response with task_id
        """
        client = await self._get_client()
        payload = {
            "user_id": self.user_id,
            "messages": messages,
            "source": source,
            "async_mode": async_mode,
        }

        if conversation_id:
            payload["conversation_id"] = conversation_id
        if agent_id:
            payload["agent_id"] = agent_id
        if tags:
            payload["tags"] = tags

        try:
            response = await client.post(
                f"{self.base_url}/add/message",
                headers=self._get_headers(),
                json=payload,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"MemOS add_multimodal_message failed: {e}")
            return {"code": -1, "message": str(e), "data": {}}
        except Exception as e:
            logger.error(f"MemOS add_multimodal_message error: {e}")
            return {"code": -1, "message": str(e), "data": {}}

    async def get_memory(
        self,
        memory_id: str,
    ) -> dict:
        """Get a specific memory by ID.

        Args:
            memory_id: The ID of the memory to retrieve

        Returns:
            API response with memory details
        """
        client = await self._get_client()
        payload = {
            "user_id": self.user_id,
            "memory_id": memory_id,
        }

        try:
            response = await client.post(
                f"{self.base_url}/get/memory",
                headers=self._get_headers(),
                json=payload,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"MemOS get_memory failed: {e}")
            return {"code": -1, "message": str(e), "data": {}}
        except Exception as e:
            logger.error(f"MemOS get_memory error: {e}")
            return {"code": -1, "message": str(e), "data": {}}

    async def delete_memory(
        self,
        memory_ids: list[str],
    ) -> dict:
        """Delete memories by IDs.

        Args:
            memory_ids: List of memory IDs to delete

        Returns:
            API response
        """
        client = await self._get_client()
        payload = {
            "user_id": self.user_id,
            "memory_ids": memory_ids,
        }

        try:
            response = await client.post(
                f"{self.base_url}/delete/memory",
                headers=self._get_headers(),
                json=payload,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"MemOS delete_memory failed: {e}")
            return {"code": -1, "message": str(e), "data": {}}
        except Exception as e:
            logger.error(f"MemOS delete_memory error: {e}")
            return {"code": -1, "message": str(e), "data": {}}

    async def get_message(
        self,
        message_id: str,
    ) -> dict:
        """Get a specific message by ID.

        Args:
            message_id: The ID of the message to retrieve

        Returns:
            API response with message details
        """
        client = await self._get_client()
        payload = {
            "user_id": self.user_id,
            "message_id": message_id,
        }

        try:
            response = await client.post(
                f"{self.base_url}/get/message",
                headers=self._get_headers(),
                json=payload,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"MemOS get_message failed: {e}")
            return {"code": -1, "message": str(e), "data": {}}
        except Exception as e:
            logger.error(f"MemOS get_message error: {e}")
            return {"code": -1, "message": str(e), "data": {}}

    async def get_task_status(
        self,
        task_id: str,
    ) -> dict:
        """Get the status of an async task (e.g., multimodal file processing).

        Args:
            task_id: The ID of the task to check

        Returns:
            API response with task status
        """
        client = await self._get_client()
        payload = {
            "user_id": self.user_id,
            "task_id": task_id,
        }

        try:
            response = await client.post(
                f"{self.base_url}/get/status",
                headers=self._get_headers(),
                json=payload,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"MemOS get_task_status failed: {e}")
            return {"code": -1, "message": str(e), "data": {}}
        except Exception as e:
            logger.error(f"MemOS get_task_status error: {e}")
            return {"code": -1, "message": str(e), "data": {}}

    async def create_knowledgebase(
        self,
        kb_name: str,
        description: str = "",
    ) -> dict:
        """Create a new knowledge base.

        Args:
            kb_name: Name of the knowledge base
            description: Optional description

        Returns:
            API response with knowledge base ID
        """
        client = await self._get_client()
        payload = {
            "user_id": self.user_id,
            "kb_name": kb_name,
        }
        if description:
            payload["description"] = description

        try:
            response = await client.post(
                f"{self.base_url}/knowledge/create",
                headers=self._get_headers(),
                json=payload,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"MemOS create_knowledgebase failed: {e}")
            return {"code": -1, "message": str(e), "data": {}}
        except Exception as e:
            logger.error(f"MemOS create_knowledgebase error: {e}")
            return {"code": -1, "message": str(e), "data": {}}

    async def remove_knowledgebase(
        self,
        kb_id: str,
    ) -> dict:
        """Remove a knowledge base.

        Args:
            kb_id: ID of the knowledge base to remove

        Returns:
            API response
        """
        client = await self._get_client()
        payload = {
            "user_id": self.user_id,
            "kb_id": kb_id,
        }

        try:
            response = await client.post(
                f"{self.base_url}/knowledge/remove",
                headers=self._get_headers(),
                json=payload,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"MemOS remove_knowledgebase failed: {e}")
            return {"code": -1, "message": str(e), "data": {}}
        except Exception as e:
            logger.error(f"MemOS remove_knowledgebase error: {e}")
            return {"code": -1, "message": str(e), "data": {}}

    async def add_knowledgebase_doc(
        self,
        kb_id: str,
        doc_data: str,
        doc_name: str = "",
        doc_type: str = "url",
    ) -> dict:
        """Add a document to a knowledge base.

        Args:
            kb_id: ID of the knowledge base
            doc_data: Document data (URL or base64 content)
            doc_name: Optional document name
            doc_type: "url" or "base64"

        Returns:
            API response with task ID
        """
        client = await self._get_client()
        payload = {
            "user_id": self.user_id,
            "kb_id": kb_id,
            "doc_data": doc_data,
            "doc_type": doc_type,
        }
        if doc_name:
            payload["doc_name"] = doc_name

        try:
            response = await client.post(
                f"{self.base_url}/knowledge/doc/add",
                headers=self._get_headers(),
                json=payload,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"MemOS add_knowledgebase_doc failed: {e}")
            return {"code": -1, "message": str(e), "data": {}}
        except Exception as e:
            logger.error(f"MemOS add_knowledgebase_doc error: {e}")
            return {"code": -1, "message": str(e), "data": {}}

    async def get_knowledgebase_docs(
        self,
        kb_id: str,
    ) -> dict:
        """Get documents in a knowledge base.

        Args:
            kb_id: ID of the knowledge base

        Returns:
            API response with document list
        """
        client = await self._get_client()
        payload = {
            "user_id": self.user_id,
            "kb_id": kb_id,
        }

        try:
            response = await client.post(
                f"{self.base_url}/knowledge/doc/get",
                headers=self._get_headers(),
                json=payload,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"MemOS get_knowledgebase_docs failed: {e}")
            return {"code": -1, "message": str(e), "data": {}}
        except Exception as e:
            logger.error(f"MemOS get_knowledgebase_docs error: {e}")
            return {"code": -1, "message": str(e), "data": {}}

    async def delete_knowledgebase_doc(
        self,
        kb_id: str,
        doc_ids: list[str],
    ) -> dict:
        """Delete documents from a knowledge base.

        Args:
            kb_id: ID of the knowledge base
            doc_ids: List of document IDs to delete

        Returns:
            API response
        """
        client = await self._get_client()
        payload = {
            "user_id": self.user_id,
            "kb_id": kb_id,
            "doc_ids": doc_ids,
        }

        try:
            response = await client.post(
                f"{self.base_url}/knowledge/doc/delete",
                headers=self._get_headers(),
                json=payload,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"MemOS delete_knowledgebase_doc failed: {e}")
            return {"code": -1, "message": str(e), "data": {}}
        except Exception as e:
            logger.error(f"MemOS delete_knowledgebase_doc error: {e}")
            return {"code": -1, "message": str(e), "data": {}}

    @staticmethod
    def load_config(working_dir: str) -> Optional[dict]:
        """Load MemOS configuration from config file or environment.

        Priority: config.json > environment variables

        Args:
            working_dir: Working directory to look for config

        Returns:
            Configuration dict or None if not configured
        """
        # Try to load from config file
        config_path = Path(working_dir) / "active_skills" / "memos-cloud" / "config.json"
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load MemOS config: {e}")

        # Try environment variables
        api_key = os.getenv("MEMOS_API_KEY", "")
        if api_key:
            return {
                "apiKey": api_key,
                "baseUrl": os.getenv(
                    "MEMOS_BASE_URL",
                    "https://memos.memtensor.cn/api/openmem/v1",
                ),
                "userId": os.getenv("MEMOS_USER_ID", "copaw-user"),
            }

        return None


class MemoryManager(ReMeLight):
    """Memory manager that extends ReMeLight for CoPaw agents with MemOS integration.

    This class provides memory management capabilities including:
    - Memory compaction for long conversations via compact_memory()
    - Memory summarization with file operation tools via summary_memory()
    - In-memory memory retrieval via get_in_memory_memory()
    - Configurable vector search and full-text search backends
    - MemOS Cloud integration for cross-session persistent memory
    """

    def __init__(
        self,
        working_dir: str,
        agent_id: str,
    ):
        """Initialize MemoryManager with ReMeLight configuration.

        Args:
            working_dir: Working directory path for memory storage
            agent_id: Agent ID for loading configuration

        Embedding Config:
            api_key, base_url, model_name: config > env var > default
            Other params: from embedding_config only

        Environment Variables:
            EMBEDDING_API_KEY: API key (fallback if not in config)
            EMBEDDING_BASE_URL: Base URL (fallback if not in config)
            EMBEDDING_MODEL_NAME: Model name (fallback if not in config)
            FTS_ENABLED: Enable full-text search (default: true)
            MEMORY_STORE_BACKEND: Memory backend
            - auto/local/chroma (default: auto)
            MEMOS_API_KEY: MemOS Cloud API key
            MEMOS_BASE_URL: MemOS API base URL
            MEMOS_USER_ID: MemOS user identifier

        Note:
            Vector search requires api_key, base_url, and model_name.
        """
        # Extract configuration from agent_config
        self.agent_id: str = agent_id
        self.working_dir: str = working_dir
        self._memos_client: Optional[MemOSClient] = None

        if not _REME_AVAILABLE:
            logger.warning(
                "reme package not available, memory features will be limited",
            )
            return

        # Get embedding config (supports hot-reload)
        emb_config = self.get_embedding_config()

        # Determine if vector search should be enabled based on configuration
        # Vector search requires base_url and model_name
        vector_enabled = bool(emb_config["base_url"]) and bool(
            emb_config["model_name"],
        )

        # Log embedding config (mask api_key for security)
        log_cfg = {
            **emb_config,
            "api_key": self.mask_key(emb_config["api_key"]),
        }
        logger.info(
            f"Embedding config: {log_cfg}, vector_enabled={vector_enabled}",
        )

        # Check if full-text search (FTS) is enabled via environment variable
        fts_enabled = os.environ.get("FTS_ENABLED", "true").lower() == "true"

        # Determine the memory store backend to use
        # "auto" selects based on platform
        # (local for Windows, chroma otherwise)
        memory_store_backend = os.environ.get("MEMORY_STORE_BACKEND", "auto")
        if memory_store_backend == "auto":
            memory_backend = (
                "local" if platform.system() == "Windows" else "chroma"
            )
        else:
            memory_backend = memory_store_backend

        # Initialize parent ReMeCopaw class
        super().__init__(
            working_dir=working_dir,
            default_embedding_model_config=emb_config,
            default_file_store_config={
                "backend": memory_backend,
                "store_name": "copaw",
                "vector_enabled": vector_enabled,
                "fts_enabled": fts_enabled,
            },
        )

        self.summary_toolkit = Toolkit()
        self.summary_toolkit.register_tool_function(read_file)
        self.summary_toolkit.register_tool_function(write_file)
        self.summary_toolkit.register_tool_function(edit_file)

        self.chat_model: ChatModelBase | None = None
        self.formatter: FormatterBase | None = None

        # Initialize MemOS client if configured
        self._init_memos_client()

    def _init_memos_client(self) -> None:
        """Initialize MemOS client from configuration."""
        config = MemOSClient.load_config(self.working_dir)
        if config and config.get("apiKey"):
            self._memos_client = MemOSClient(
                api_key=config["apiKey"],
                base_url=config.get("baseUrl", "https://memos.memtensor.cn/api/openmem/v1"),
                user_id=config.get("userId", "copaw-user"),
            )
            logger.info(f"MemOS Cloud client initialized for user: {config.get('userId', 'copaw-user')}")
        else:
            logger.info("MemOS Cloud not configured, using local memory only")

    @property
    def memos_enabled(self) -> bool:
        """Check if MemOS Cloud is enabled."""
        return self._memos_client is not None

    @staticmethod
    def mask_key(key: str) -> str:
        """Mask API key, showing first 5 chars and masking rest with *."""
        if not key:
            return ""
        if len(key) <= 5:
            return key
        return key[:5] + "*" * (len(key) - 5)

    def get_embedding_config(self) -> dict:
        """Get embedding config. Priority: config > env var > default."""
        cfg = load_agent_config(self.agent_id).running.embedding_config

        return {
            "backend": cfg.backend,
            "api_key": cfg.api_key or os.getenv("EMBEDDING_API_KEY", ""),
            "base_url": cfg.base_url or os.getenv("EMBEDDING_BASE_URL", ""),
            "model_name": cfg.model_name
            or os.getenv("EMBEDDING_MODEL_NAME", ""),
            "dimensions": cfg.dimensions,
            "enable_cache": cfg.enable_cache,
            "use_dimensions": cfg.use_dimensions,
            "max_cache_size": cfg.max_cache_size,
            "max_input_length": cfg.max_input_length,
            "max_batch_size": cfg.max_batch_size,
        }

    def prepare_model_formatter(self) -> None:
        """Prepare and initialize the chat model and formatter.

        Lazily initializes the chat_model and formatter attributes if they
        haven't been set yet. This method is called before compaction or
        summarization operations that require model access.

        Note:
            Logs a warning if the model and formatter are not already
            initialized, as this indicates a potential configuration issue.
        """
        if self.chat_model is None or self.formatter is None:
            logger.warning("Model and formatter not initialized.")
            chat_model, formatter = create_model_and_formatter(self.agent_id)
            if self.chat_model is None:
                self.chat_model = chat_model
            if self.formatter is None:
                self.formatter = formatter

    async def restart_embedding_model(self):
        """Restart the embedding model with current config."""
        emb_config = self.get_embedding_config()
        restart_config = {
            "embedding_models": {
                "default": emb_config,
            },
        }
        await self.restart(restart_config=restart_config)

    async def compact_memory(
        self,
        messages: list[Msg],
        previous_summary: str = "",
        **_kwargs,
    ) -> str:
        """Compact a list of messages into a condensed summary.

        Args:
            messages: List of Msg objects to compact
            previous_summary: Optional previous summary to incorporate
            **_kwargs: Additional keyword arguments (ignored)

        Returns:
            str: Condensed summary of the messages
        """
        self.prepare_model_formatter()

        agent_config = load_agent_config(self.agent_id)
        token_counter = get_copaw_token_counter(agent_config)

        result = await super().compact_memory(
            messages=messages,
            as_llm=self.chat_model,
            as_llm_formatter=self.formatter,
            as_token_counter=token_counter,
            language=agent_config.language,
            max_input_length=agent_config.running.max_input_length,
            compact_ratio=agent_config.running.memory_compact_ratio,
            previous_summary=previous_summary,
        )

        # Sync to MemOS Cloud
        if self._memos_client and result:
            await self._sync_to_memos(result, source="compact")

        return result

    async def summary_memory(self, messages: list[Msg], **_kwargs) -> str:
        """Generate a comprehensive summary of the given messages.

        Uses file operation tools (read_file, write_file, edit_file) to support
        the summarization process.

        Args:
            messages: List of Msg objects to summarize
            **_kwargs: Additional keyword arguments (ignored)

        Returns:
            str: Comprehensive summary of the messages
        """
        self.prepare_model_formatter()

        agent_config = load_agent_config(self.agent_id)
        token_counter = get_copaw_token_counter(agent_config)

        result = await super().summary_memory(
            messages=messages,
            as_llm=self.chat_model,
            as_llm_formatter=self.formatter,
            as_token_counter=token_counter,
            toolkit=self.summary_toolkit,
            language=agent_config.language,
            max_input_length=agent_config.running.max_input_length,
            compact_ratio=agent_config.running.memory_compact_ratio,
        )

        # Sync to MemOS Cloud
        if self._memos_client and result:
            await self._sync_to_memos(result, source="summary")

        return result

    async def _sync_to_memos(self, content: str, source: str = "copaw") -> None:
        """Sync memory content to MemOS Cloud.

        Args:
            content: Memory content to sync
            source: Source identifier
        """
        if not self._memos_client:
            return

        try:
            result = await self._memos_client.add_message(
                content=content,
                role="assistant",
                conversation_id=self.agent_id,
                source=source,
            )
            if result.get("code") == 0:
                logger.debug(f"Synced memory to MemOS: {result.get('data', {}).get('task_id', '')}")
            else:
                logger.warning(f"Failed to sync to MemOS: {result.get('message', 'unknown error')}")
        except Exception as e:
            logger.error(f"Error syncing to MemOS: {e}")

    async def memory_search(
        self,
        query: str,
        max_results: int = 5,
        min_score: float = 0.1,
    ) -> ToolResponse:
        """Search through stored memories for relevant content.

        Performs a hybrid search across:
        1. Local memory store (vector + full-text search)
        2. MemOS Cloud (semantic search, if configured)

        Results are merged with local results prioritized.

        Args:
            query: The search query string
            max_results: Maximum number of results to return (default: 5)
            min_score: Minimum relevance score threshold (default: 0.1)

        Returns:
            ToolResponse containing the search results as TextBlock content,
            or an error message if ReMe has not been started.
        """
        if not self._started:
            return ToolResponse(
                content=[
                    TextBlock(
                        type="text",
                        text="ReMe is not started, report github issue!",
                    ),
                ],
            )

        # Perform local search
        local_result = await super().memory_search(
            query=query,
            max_results=max_results,
            min_score=min_score,
        )

        # If MemOS is enabled, also search cloud
        if self._memos_client:
            try:
                cloud_result = await self._search_memos(query, max_results)
                local_result = self._merge_search_results(local_result, cloud_result)
            except Exception as e:
                logger.error(f"MemOS search failed: {e}")

        return local_result

    async def _search_memos(self, query: str, max_results: int = 5) -> list[dict]:
        """Search MemOS Cloud for memories.

        Args:
            query: Search query
            max_results: Maximum results to return

        Returns:
            List of memory items from MemOS
        """
        if not self._memos_client:
            return []

        result = await self._memos_client.search(
            query=query,
            top_k=max_results,
        )

        if result.get("code") == 0:
            data = result.get("data", {})
            # Combine all memory types
            memories = []
            for key in ["memory_detail_list", "preference_detail_list", "tool_memory_detail_list"]:
                memories.extend(data.get(key, []))
            return memories[:max_results]

        return []

    def _merge_search_results(
        self,
        local_result: ToolResponse,
        cloud_memories: list[dict],
    ) -> ToolResponse:
        """Merge local and cloud search results.

        Args:
            local_result: Local search result from ReMeLight
            cloud_memories: Cloud memories from MemOS

        Returns:
            Merged ToolResponse
        """
        if not cloud_memories:
            return local_result

        # Extract local text content
        local_text = ""
        for block in local_result.content or []:
            if isinstance(block, TextBlock):
                local_text = block.text or ""
                break

        # Format cloud memories
        cloud_text = "\n\n### MemOS Cloud Memories\n\n"
        for mem in cloud_memories:
            memory_value = mem.get("memory_value", mem.get("memory_value", ""))
            memory_key = mem.get("memory_key", "")
            confidence = mem.get("confidence", 0)
            if memory_value:
                cloud_text += f"**{memory_key}** (confidence: {confidence:.2f})\n"
                cloud_text += f"{memory_value}\n\n"

        # Combine results
        merged_text = local_text + cloud_text if local_text else cloud_text

        return ToolResponse(
            content=[TextBlock(type="text", text=merged_text)],
        )

    async def memory_add(
        self,
        content: str,
        role: str = "user",
        conversation_id: Optional[str] = None,
    ) -> dict:
        """Add a memory to MemOS Cloud.

        This is an explicit memory addition, typically called when user
        asks to "remember this" or when important information is identified.

        Args:
            content: Memory content to store
            role: Message role (user/assistant)
            conversation_id: Optional conversation ID

        Returns:
            API response from MemOS
        """
        if not self._memos_client:
            return {"code": -1, "message": "MemOS not configured"}

        result = await self._memos_client.add_message(
            content=content,
            role=role,
            conversation_id=conversation_id or self.agent_id,
            source="copaw-explicit",
        )

        if result.get("code") == 0:
            logger.info(f"Added memory to MemOS: {result.get('data', {}).get('task_id', '')}")

        return result

    def get_in_memory_memory(self, **_kwargs):
        """Retrieve in-memory memory content.

        Args:
            **_kwargs: Additional keyword arguments (passed to parent)

        Returns:
            The in-memory memory content with token counting support
        """
        agent_config = load_agent_config(self.agent_id)
        token_counter = get_copaw_token_counter(agent_config)

        return super().get_in_memory_memory(
            as_token_counter=token_counter,
        )

    async def close(self):
        """Clean up resources."""
        if self._memos_client:
            await self._memos_client.close()