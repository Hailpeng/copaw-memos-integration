# -*- coding: utf-8 -*-
"""LCM Tools - Agent tools for accessing compressed history.

Provides three tools:
- lcm_grep: Search all history (messages and summaries)
- lcm_describe: Show DAG structure
- lcm_expand: Expand a summary to recover original messages
"""
import json
import logging
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .engine import LCMEngine

logger = logging.getLogger(__name__)


# Tool definitions for agent registration
LCM_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "lcm_grep",
            "description": "Search all conversation history including compressed/summarized content. Use this when you need to find specific information from past messages that may have been compressed.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query - keywords or phrases to find in history"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return",
                        "default": 10
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "lcm_describe",
            "description": "Show the structure of the conversation's DAG (Directed Acyclic Graph). Returns statistics about messages, summaries, and the compression hierarchy.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "lcm_expand",
            "description": "Expand a summary node to recover the original messages. Use this when you need full details from a compressed section of the conversation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "summary_id": {
                        "type": "string",
                        "description": "ID of the summary to expand (use lcm_describe to find summary IDs)"
                    }
                },
                "required": ["summary_id"]
            }
        }
    }
]


async def lcm_grep(
    engine: "LCMEngine",
    query: str,
    limit: int = 10,
) -> str:
    """Search all conversation history.
    
    Args:
        engine: LCM engine instance
        query: Search query
        limit: Maximum results
        
    Returns:
        Formatted search results
    """
    try:
        results = await engine.search(query, limit)
        
        output_parts = []
        
        # Format message results
        if results.get("messages"):
            output_parts.append("=== Messages ===")
            for i, msg in enumerate(results["messages"][:limit], 1):
                content = msg.get("content", "")
                if len(content) > 200:
                    content = content[:200] + "..."
                output_parts.append(
                    f"{i}. [{msg.get('role', '?')}] {content}"
                )
        
        # Format summary results
        if results.get("summaries"):
            output_parts.append("\n=== Summaries ===")
            for i, summary in enumerate(results["summaries"][:limit], 1):
                content = summary.get("content", "")
                if len(content) > 300:
                    content = content[:300] + "..."
                output_parts.append(
                    f"{i}. [Depth {summary.get('depth', '?')}] (ID: {summary.get('id', '?')[:8]})\n   {content}"
                )
        
        if not output_parts:
            return f"No results found for query: '{query}'"
        
        return "\n".join(output_parts)
        
    except Exception as e:
        logger.exception(f"lcm_grep failed: {e}")
        return f"Search failed: {str(e)}"


async def lcm_describe(engine: "LCMEngine") -> str:
    """Describe the current DAG structure.
    
    Args:
        engine: LCM engine instance
        
    Returns:
        Formatted DAG description
    """
    try:
        dag_info = await engine.describe_dag()
        
        stats = dag_info.get("stats", {})
        structure = dag_info.get("dag_structure", {})
        
        output_parts = [
            f"Conversation: {dag_info.get('conversation_id', '?')}",
            "",
            "=== Statistics ===",
            f"Total messages: {stats.get('total_messages', 0)}",
            f"Compacted messages: {stats.get('compacted_messages', 0)}",
            f"Total tokens: {stats.get('total_tokens', 0)}",
            f"Summaries: {stats.get('total_summaries', 0)}",
            f"Max depth: {stats.get('max_depth', 0)}",
        ]
        
        if structure:
            output_parts.append("\n=== DAG Structure ===")
            for depth in sorted(structure.keys(), reverse=True):
                nodes = structure[depth]
                depth_name = "Root" if depth == max(structure.keys()) else f"Depth {depth}"
                output_parts.append(f"\n{depth_name} ({len(nodes)} nodes):")
                for node in nodes:
                    output_parts.append(
                        f"  - [{node.get('id', '?')}] ~{node.get('tokens', '?')} tokens"
                    )
        
        return "\n".join(output_parts)
        
    except Exception as e:
        logger.exception(f"lcm_describe failed: {e}")
        return f"Failed to describe DAG: {str(e)}"


async def lcm_expand(
    engine: "LCMEngine",
    summary_id: str,
) -> str:
    """Expand a summary to get original messages.
    
    Args:
        engine: LCM engine instance
        summary_id: ID of summary to expand
        
    Returns:
        Expanded messages
    """
    try:
        messages = await engine.expand_summary(summary_id)
        
        if not messages:
            return f"No messages found for summary: {summary_id}"
        
        output_parts = [
            f"=== Expanded Summary {summary_id[:8]} ===",
            f"Total messages: {len(messages)}",
            "",
        ]
        
        for i, msg in enumerate(messages, 1):
            role = msg.get("role", "?")
            content = msg.get("content", "")
            if len(content) > 500:
                content = content[:500] + "..."
            output_parts.append(f"{i}. [{role.upper()}]: {content}")
        
        return "\n".join(output_parts)
        
    except Exception as e:
        logger.exception(f"lcm_expand failed: {e}")
        return f"Failed to expand summary: {str(e)}"


class LCMToolHandler:
    """Handler for LCM tool calls.
    
    Usage:
        handler = LCMToolHandler(engine)
        
        # In your tool handling code:
        if tool_name.startswith("lcm_"):
            result = await handler.handle(tool_name, arguments)
    """
    
    def __init__(self, engine: "LCMEngine"):
        """Initialize handler.
        
        Args:
            engine: LCM engine instance
        """
        self.engine = engine
    
    async def handle(self, tool_name: str, arguments: dict) -> str:
        """Handle a tool call.
        
        Args:
            tool_name: Name of the tool (lcm_grep, lcm_describe, lcm_expand)
            arguments: Tool arguments
            
        Returns:
            Tool result string
        """
        if tool_name == "lcm_grep":
            return await lcm_grep(
                self.engine,
                query=arguments.get("query", ""),
                limit=arguments.get("limit", 10),
            )
        elif tool_name == "lcm_describe":
            return await lcm_describe(self.engine)
        elif tool_name == "lcm_expand":
            return await lcm_expand(
                self.engine,
                summary_id=arguments.get("summary_id", ""),
            )
        else:
            return f"Unknown LCM tool: {tool_name}"
    
    @staticmethod
    def get_tool_definitions() -> list[dict]:
        """Get tool definitions for agent registration."""
        return LCM_TOOLS.copy()


def register_lcm_tools(tool_registry) -> None:
    """Register LCM tools with a tool registry.
    
    Args:
        tool_registry: Tool registry to register with
    """
    from agentscope.tool import ToolResponse
    
    # This would be called during agent initialization
    # to add LCM tools to the agent's available tools
    pass