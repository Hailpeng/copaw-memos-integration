# -*- coding: utf-8 -*-
"""Memory tools for semantic search and storage in memory files."""
from agentscope.tool import ToolResponse
from agentscope.message import TextBlock


def create_memory_search_tool(memory_manager):
    """Create a memory_search tool function with bound memory_manager.

    Args:
        memory_manager: MemoryManager instance to use for searching

    Returns:
        An async function that can be registered as a tool
    """

    async def memory_search(
        query: str,
        max_results: int = 5,
        min_score: float = 0.1,
    ) -> ToolResponse:
        """
        Search MEMORY.md and memory/*.md files semantically.

        Use this tool before answering questions about prior work, decisions,
        dates, people, preferences, or todos. Returns top relevant snippets
        with file paths and line numbers.

        Args:
            query (`str`):
                The semantic search query to find relevant memory snippets.
            max_results (`int`, optional):
                Maximum number of search results to return. Defaults to 5.
            min_score (`float`, optional):
                Minimum similarity score for results. Defaults to 0.1.

        Returns:
            `ToolResponse`:
                Search results formatted with paths, line numbers, and content.
        """
        if memory_manager is None:
            return ToolResponse(
                content=[
                    TextBlock(
                        type="text",
                        text="Error: Memory manager is not enabled.",
                    ),
                ],
            )

        try:
            # memory_manager.memory_search already returns ToolResponse
            return await memory_manager.memory_search(
                query=query,
                max_results=max_results,
                min_score=min_score,
            )

        except Exception as e:
            return ToolResponse(
                content=[
                    TextBlock(
                        type="text",
                        text=f"Error: Memory search failed due to\n{e}",
                    ),
                ],
            )

    return memory_search


def create_memory_add_tool(memory_manager):
    """Create a memory_add tool function with bound memory_manager.

    Args:
        memory_manager: MemoryManager instance to use for adding memories

    Returns:
        An async function that can be registered as a tool
    """

    async def memory_add(
        content: str,
        role: str = "user",
    ) -> ToolResponse:
        """
        Add a memory to persistent cloud storage.

        Use this tool when you want to explicitly store important information
        that should be remembered across sessions. Examples:
        - User says "remember this" or "don't forget"
        - User shares personal preferences, habits, or work patterns
        - Important decisions or conclusions are made
        - Key project context or technical details are discovered

        Args:
            content (`str`):
                The memory content to store. Should be a clear, concise
                description of what should be remembered.
            role (`str`, optional):
                The role associated with this memory. Use "user" for
                user-provided information, "assistant" for agent insights.
                Defaults to "user".

        Returns:
            `ToolResponse`:
                Confirmation of memory storage or error message.
        """
        if memory_manager is None:
            return ToolResponse(
                content=[
                    TextBlock(
                        type="text",
                        text="Error: Memory manager is not enabled.",
                    ),
                ],
            )

        if not memory_manager.memos_enabled:
            return ToolResponse(
                content=[
                    TextBlock(
                        type="text",
                        text="Note: MemOS Cloud is not configured. Memory was not stored to cloud.\n"
                        "To enable cloud memory, configure active_skills/memos-cloud/config.json",
                    ),
                ],
            )

        try:
            result = await memory_manager.memory_add(
                content=content,
                role=role,
            )

            if result.get("code") == 0:
                task_id = result.get("data", {}).get("task_id", "")
                return ToolResponse(
                    content=[
                        TextBlock(
                            type="text",
                            text=f"✓ Memory stored successfully (task_id: {task_id})",
                        ),
                    ],
                )
            else:
                error_msg = result.get("message", "unknown error")
                return ToolResponse(
                    content=[
                        TextBlock(
                            type="text",
                            text=f"Failed to store memory: {error_msg}",
                        ),
                    ],
                )

        except Exception as e:
            return ToolResponse(
                content=[
                    TextBlock(
                        type="text",
                        text=f"Error: Memory add failed due to\n{e}",
                    ),
                ],
            )

    return memory_add


def create_memory_feedback_tool(memory_manager):
    """Create a memory_feedback tool function with bound memory_manager.

    Args:
        memory_manager: MemoryManager instance to use for feedback

    Returns:
        An async function that can be registered as a tool
    """

    async def memory_feedback(
        feedback: str,
    ) -> ToolResponse:
        """
        Provide natural language feedback to correct or update memories.

        Use this tool when the user wants to correct, update, or refine
        stored memories using natural language. The system will automatically
        locate and update relevant memories based on the feedback content.

        Examples:
        - User says "that's wrong, my name is X not Y"
        - User says "I changed my mind about X"
        - User says "update my preference for X to Y"

        Args:
            feedback (`str`):
                Natural language feedback describing what should be corrected
                or updated. Be specific about what needs to change.

        Returns:
            `ToolResponse`:
                Confirmation of feedback processing or error message.
        """
        if memory_manager is None:
            return ToolResponse(
                content=[
                    TextBlock(
                        type="text",
                        text="Error: Memory manager is not enabled.",
                    ),
                ],
            )

        if not memory_manager.memos_enabled:
            return ToolResponse(
                content=[
                    TextBlock(
                        type="text",
                        text="Note: MemOS Cloud is not configured. Feedback was not processed.\n"
                        "To enable cloud memory, configure active_skills/memos-cloud/config.json",
                    ),
                ],
            )

        try:
            client = memory_manager._memos_client
            if not client:
                return ToolResponse(
                    content=[
                        TextBlock(
                            type="text",
                            text="Error: MemOS client not initialized.",
                        ),
                    ],
                )

            result = await client.add_feedback(
                feedback_content=feedback,
                conversation_id=memory_manager.agent_id,
            )

            if result.get("code") == 0:
                return ToolResponse(
                    content=[
                        TextBlock(
                            type="text",
                            text=f"✓ Feedback processed successfully. Memories will be updated accordingly.",
                        ),
                    ],
                )
            else:
                error_msg = result.get("message", "unknown error")
                return ToolResponse(
                    content=[
                        TextBlock(
                            type="text",
                            text=f"Failed to process feedback: {error_msg}",
                        ),
                    ],
                )

        except Exception as e:
            return ToolResponse(
                content=[
                    TextBlock(
                        type="text",
                        text=f"Error: Memory feedback failed due to\n{e}",
                    ),
                ],
            )

    return memory_feedback


def create_memory_get_tool(memory_manager):
    """Create a memory_get tool function with bound memory_manager.

    Args:
        memory_manager: MemoryManager instance

    Returns:
        An async function that can be registered as a tool
    """

    async def memory_get(
        memory_id: str,
    ) -> ToolResponse:
        """
        Get a specific memory by ID from MemOS Cloud.

        Use this tool to retrieve the full content of a specific memory
        when you need to see the complete details of a remembered item.

        Args:
            memory_id (`str`):
                The ID of the memory to retrieve.

        Returns:
            `ToolResponse`:
                The memory content with metadata, or error message.
        """
        if memory_manager is None:
            return ToolResponse(
                content=[TextBlock(type="text", text="Error: Memory manager is not enabled.")],
            )

        if not memory_manager.memos_enabled:
            return ToolResponse(
                content=[TextBlock(type="text", text="Error: MemOS Cloud is not configured.")],
            )

        try:
            client = memory_manager._memos_client
            if not client:
                return ToolResponse(
                    content=[TextBlock(type="text", text="Error: MemOS client not initialized.")],
                )

            result = await client.get_memory(memory_id=memory_id)

            if result.get("code") == 0:
                data = result.get("data", {})
                return ToolResponse(
                    content=[TextBlock(type="text", text=f"✓ Memory retrieved:\n{data}")],
                )
            else:
                error_msg = result.get("message", "unknown error")
                return ToolResponse(
                    content=[TextBlock(type="text", text=f"Failed to get memory: {error_msg}")],
                )

        except Exception as e:
            return ToolResponse(
                content=[TextBlock(type="text", text=f"Error: Memory get failed due to\n{e}")],
            )

    return memory_get


def create_memory_delete_tool(memory_manager):
    """Create a memory_delete tool function with bound memory_manager.

    Args:
        memory_manager: MemoryManager instance

    Returns:
        An async function that can be registered as a tool
    """

    async def memory_delete(
        memory_ids: str,
    ) -> ToolResponse:
        """
        Delete memories from MemOS Cloud.

        Use this tool to remove outdated, incorrect, or unwanted memories.
        Multiple memory IDs can be provided as comma-separated values.

        Args:
            memory_ids (`str`):
                Comma-separated list of memory IDs to delete.

        Returns:
            `ToolResponse`:
                Confirmation of deletion or error message.
        """
        if memory_manager is None:
            return ToolResponse(
                content=[TextBlock(type="text", text="Error: Memory manager is not enabled.")],
            )

        if not memory_manager.memos_enabled:
            return ToolResponse(
                content=[TextBlock(type="text", text="Error: MemOS Cloud is not configured.")],
            )

        try:
            client = memory_manager._memos_client
            if not client:
                return ToolResponse(
                    content=[TextBlock(type="text", text="Error: MemOS client not initialized.")],
                )

            # Parse comma-separated IDs
            ids_list = [mid.strip() for mid in memory_ids.split(",") if mid.strip()]

            result = await client.delete_memory(memory_ids=ids_list)

            if result.get("code") == 0:
                return ToolResponse(
                    content=[TextBlock(type="text", text=f"✓ Deleted {len(ids_list)} memory(ies)")],
                )
            else:
                error_msg = result.get("message", "unknown error")
                return ToolResponse(
                    content=[TextBlock(type="text", text=f"Failed to delete memory: {error_msg}")],
                )

        except Exception as e:
            return ToolResponse(
                content=[TextBlock(type="text", text=f"Error: Memory delete failed due to\n{e}")],
            )

    return memory_delete


def create_task_status_tool(memory_manager):
    """Create a task_status tool function with bound memory_manager.

    Args:
        memory_manager: MemoryManager instance

    Returns:
        An async function that can be registered as a tool
    """

    async def task_status(
        task_id: str,
    ) -> ToolResponse:
        """
        Check the status of an async task in MemOS Cloud.

        Use this tool to check the processing status of multimodal files
        (images, documents) that were uploaded asynchronously.

        Args:
            task_id (`str`):
                The ID of the task to check.

        Returns:
            `ToolResponse`:
                Task status (pending, processing, completed, failed).
        """
        if memory_manager is None:
            return ToolResponse(
                content=[TextBlock(type="text", text="Error: Memory manager is not enabled.")],
            )

        if not memory_manager.memos_enabled:
            return ToolResponse(
                content=[TextBlock(type="text", text="Error: MemOS Cloud is not configured.")],
            )

        try:
            client = memory_manager._memos_client
            if not client:
                return ToolResponse(
                    content=[TextBlock(type="text", text="Error: MemOS client not initialized.")],
                )

            result = await client.get_task_status(task_id=task_id)

            if result.get("code") == 0:
                data = result.get("data", {})
                status = data.get("status", "unknown")
                return ToolResponse(
                    content=[TextBlock(type="text", text=f"Task status: {status}\n{data}")],
                )
            else:
                error_msg = result.get("message", "unknown error")
                return ToolResponse(
                    content=[TextBlock(type="text", text=f"Failed to get task status: {error_msg}")],
                )

        except Exception as e:
            return ToolResponse(
                content=[TextBlock(type="text", text=f"Error: Task status check failed due to\n{e}")],
            )

    return task_status


def create_knowledgebase_tools(memory_manager):
    """Create knowledge base management tools.

    Args:
        memory_manager: MemoryManager instance

    Returns:
        Dict of tool functions
    """

    async def knowledgebase_create(
        name: str,
        description: str = "",
    ) -> ToolResponse:
        """
        Create a new knowledge base in MemOS Cloud.

        Knowledge bases are used to organize and store domain-specific
        documents and information that can be searched during memory recall.

        Args:
            name (`str`):
                Name of the knowledge base.
            description (`str`, optional):
                Optional description of the knowledge base.

        Returns:
            `ToolResponse`:
                Knowledge base ID and confirmation.
        """
        if memory_manager is None or not memory_manager.memos_enabled:
            return ToolResponse(
                content=[TextBlock(type="text", text="Error: MemOS Cloud is not configured.")],
            )

        try:
            client = memory_manager._memos_client
            if not client:
                return ToolResponse(
                    content=[TextBlock(type="text", text="Error: MemOS client not initialized.")],
                )

            result = await client.create_knowledgebase(kb_name=name, description=description)

            if result.get("code") == 0:
                kb_id = result.get("data", {}).get("kb_id", "")
                return ToolResponse(
                    content=[TextBlock(type="text", text=f"✓ Knowledge base created: {kb_id}")],
                )
            else:
                return ToolResponse(
                    content=[TextBlock(type="text", text=f"Failed: {result.get('message', 'unknown error')}")],
                )

        except Exception as e:
            return ToolResponse(
                content=[TextBlock(type="text", text=f"Error: {e}")],
            )

    async def knowledgebase_remove(
        kb_id: str,
    ) -> ToolResponse:
        """
        Remove a knowledge base from MemOS Cloud.

        WARNING: This will delete all documents and memories in the knowledge base.

        Args:
            kb_id (`str`):
                ID of the knowledge base to remove.

        Returns:
            `ToolResponse`:
                Confirmation of removal.
        """
        if memory_manager is None or not memory_manager.memos_enabled:
            return ToolResponse(
                content=[TextBlock(type="text", text="Error: MemOS Cloud is not configured.")],
            )

        try:
            client = memory_manager._memos_client
            result = await client.remove_knowledgebase(kb_id=kb_id)

            if result.get("code") == 0:
                return ToolResponse(
                    content=[TextBlock(type="text", text=f"✓ Knowledge base removed: {kb_id}")],
                )
            else:
                return ToolResponse(
                    content=[TextBlock(type="text", text=f"Failed: {result.get('message', 'unknown error')}")],
                )

        except Exception as e:
            return ToolResponse(
                content=[TextBlock(type="text", text=f"Error: {e}")],
            )

    async def knowledgebase_doc_add(
        kb_id: str,
        doc_url: str,
        doc_name: str = "",
    ) -> ToolResponse:
        """
        Add a document to a knowledge base.

        Upload a document (PDF, DOCX, etc.) to a knowledge base for
        automatic extraction and indexing.

        Args:
            kb_id (`str`):
                ID of the knowledge base.
            doc_url (`str`):
                URL of the document to add.
            doc_name (`str`, optional):
                Optional name for the document.

        Returns:
            `ToolResponse`:
                Task ID for tracking the processing status.
        """
        if memory_manager is None or not memory_manager.memos_enabled:
            return ToolResponse(
                content=[TextBlock(type="text", text="Error: MemOS Cloud is not configured.")],
            )

        try:
            client = memory_manager._memos_client
            result = await client.add_knowledgebase_doc(
                kb_id=kb_id,
                doc_data=doc_url,
                doc_name=doc_name,
                doc_type="url",
            )

            if result.get("code") == 0:
                task_id = result.get("data", {}).get("task_id", "")
                return ToolResponse(
                    content=[TextBlock(type="text", text=f"✓ Document added. Task ID: {task_id}")],
                )
            else:
                return ToolResponse(
                    content=[TextBlock(type="text", text=f"Failed: {result.get('message', 'unknown error')}")],
                )

        except Exception as e:
            return ToolResponse(
                content=[TextBlock(type="text", text=f"Error: {e}")],
            )

    async def knowledgebase_doc_list(
        kb_id: str,
    ) -> ToolResponse:
        """
        List documents in a knowledge base.

        Args:
            kb_id (`str`):
                ID of the knowledge base.

        Returns:
            `ToolResponse`:
                List of documents with their IDs and names.
        """
        if memory_manager is None or not memory_manager.memos_enabled:
            return ToolResponse(
                content=[TextBlock(type="text", text="Error: MemOS Cloud is not configured.")],
            )

        try:
            client = memory_manager._memos_client
            result = await client.get_knowledgebase_docs(kb_id=kb_id)

            if result.get("code") == 0:
                docs = result.get("data", {}).get("documents", [])
                doc_list = "\n".join([f"- {d.get('doc_name', d.get('doc_id', 'unknown'))}" for d in docs])
                return ToolResponse(
                    content=[TextBlock(type="text", text=f"Documents in KB:\n{doc_list or 'No documents'}")],
                )
            else:
                return ToolResponse(
                    content=[TextBlock(type="text", text=f"Failed: {result.get('message', 'unknown error')}")],
                )

        except Exception as e:
            return ToolResponse(
                content=[TextBlock(type="text", text=f"Error: {e}")],
            )

    async def knowledgebase_doc_delete(
        kb_id: str,
        doc_ids: str,
    ) -> ToolResponse:
        """
        Delete documents from a knowledge base.

        Args:
            kb_id (`str`):
                ID of the knowledge base.
            doc_ids (`str`):
                Comma-separated list of document IDs to delete.

        Returns:
            `ToolResponse`:
                Confirmation of deletion.
        """
        if memory_manager is None or not memory_manager.memos_enabled:
            return ToolResponse(
                content=[TextBlock(type="text", text="Error: MemOS Cloud is not configured.")],
            )

        try:
            client = memory_manager._memos_client
            ids_list = [did.strip() for did in doc_ids.split(",") if did.strip()]

            result = await client.delete_knowledgebase_doc(kb_id=kb_id, doc_ids=ids_list)

            if result.get("code") == 0:
                return ToolResponse(
                    content=[TextBlock(type="text", text=f"✓ Deleted {len(ids_list)} document(s)")],
                )
            else:
                return ToolResponse(
                    content=[TextBlock(type="text", text=f"Failed: {result.get('message', 'unknown error')}")],
                )

        except Exception as e:
            return ToolResponse(
                content=[TextBlock(type="text", text=f"Error: {e}")],
            )

    return {
        "knowledgebase_create": knowledgebase_create,
        "knowledgebase_remove": knowledgebase_remove,
        "knowledgebase_doc_add": knowledgebase_doc_add,
        "knowledgebase_doc_list": knowledgebase_doc_list,
        "knowledgebase_doc_delete": knowledgebase_doc_delete,
    }