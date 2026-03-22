# -*- coding: utf-8 -*-
"""LCM Database Layer.

SQLite-based persistence for messages and DAG summaries.
Provides lossless storage with full-text search capabilities.
"""
import asyncio
import json
import logging
import sqlite3
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# SQL schema version
SCHEMA_VERSION = 1

SCHEMA = """
-- Conversations table
CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    message_count INTEGER DEFAULT 0,
    summary_count INTEGER DEFAULT 0
);

-- Messages table (original messages, never deleted)
CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT,
    content_json TEXT,  -- JSON for complex content (tool_use, tool_result)
    content_type TEXT DEFAULT 'text',
    token_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_compacted BOOLEAN DEFAULT FALSE,
    summary_id TEXT,
    metadata TEXT,  -- JSON for additional metadata
    FOREIGN KEY (conversation_id) REFERENCES conversations(id),
    FOREIGN KEY (summary_id) REFERENCES summaries(id)
);

-- Summaries table (DAG structure)
CREATE TABLE IF NOT EXISTS summaries (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    parent_id TEXT,
    depth INTEGER DEFAULT 0,
    content TEXT NOT NULL,
    token_count INTEGER DEFAULT 0,
    source_message_ids TEXT,  -- JSON array
    source_summary_ids TEXT,  -- JSON array
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id),
    FOREIGN KEY (parent_id) REFERENCES summaries(id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_messages_created ON messages(created_at);
CREATE INDEX IF NOT EXISTS idx_messages_compacted ON messages(is_compacted);
CREATE INDEX IF NOT EXISTS idx_summaries_conversation ON summaries(conversation_id);
CREATE INDEX IF NOT EXISTS idx_summaries_depth ON summaries(depth);
CREATE INDEX IF NOT EXISTS idx_summaries_parent ON summaries(parent_id);

-- Schema version table
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

FTS_SCHEMA = """
-- FTS5 full-text search (optional but recommended)
CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
    content,
    content='messages',
    content_rowid='rowid',
    tokenize='unicode61'
);

-- Triggers to keep FTS in sync
CREATE TRIGGER IF NOT EXISTS messages_ai AFTER INSERT ON messages BEGIN
    INSERT INTO messages_fts(rowid, content) VALUES (new.rowid, new.content);
END;

CREATE TRIGGER IF NOT EXISTS messages_ad AFTER DELETE ON messages BEGIN
    INSERT INTO messages_fts(messages_fts, rowid, content) VALUES('delete', old.rowid, old.content);
END;

CREATE TRIGGER IF NOT EXISTS messages_au AFTER UPDATE ON messages BEGIN
    INSERT INTO messages_fts(messages_fts, rowid, content) VALUES('delete', old.rowid, old.content);
    INSERT INTO messages_fts(rowid, content) VALUES (new.rowid, new.content);
END;
"""


class LCMDatabase:
    """SQLite database manager for LCM.
    
    Provides async interface for:
    - Conversation management
    - Message persistence and retrieval
    - Summary DAG storage
    - Full-text search
    """
    
    def __init__(self, db_path: str, enable_fts: bool = True):
        """Initialize database manager.
        
        Args:
            db_path: Path to SQLite database file
            enable_fts: Whether to enable FTS5 full-text search
        """
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.enable_fts = enable_fts
        self._lock = asyncio.Lock()
        self._initialized = False
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection with proper settings."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=30000")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn
    
    async def initialize(self) -> None:
        """Initialize database schema."""
        if self._initialized:
            return
        
        async with self._lock:
            if self._initialized:
                return
            
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._init_sync)
            self._initialized = True
            logger.info(f"LCM database initialized at {self.db_path}")
    
    def _init_sync(self) -> None:
        """Synchronous schema initialization."""
        conn = self._get_connection()
        try:
            conn.executescript(SCHEMA)
            
            if self.enable_fts:
                try:
                    conn.executescript(FTS_SCHEMA)
                except sqlite3.OperationalError as e:
                    logger.warning(f"FTS5 not available: {e}")
            
            # Check schema version
            cursor = conn.execute(
                "SELECT version FROM schema_version ORDER BY version DESC LIMIT 1"
            )
            row = cursor.fetchone()
            
            if not row:
                conn.execute(
                    "INSERT INTO schema_version (version) VALUES (?)",
                    (SCHEMA_VERSION,)
                )
            
            conn.commit()
        finally:
            conn.close()
    
    # ==================== Conversation Operations ====================
    
    async def create_conversation(
        self,
        conversation_id: str,
        agent_id: str,
    ) -> None:
        """Create a new conversation."""
        await self.initialize()
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            self._create_conversation_sync,
            conversation_id,
            agent_id,
        )
    
    def _create_conversation_sync(self, conv_id: str, agent_id: str) -> None:
        conn = self._get_connection()
        try:
            conn.execute(
                """INSERT OR IGNORE INTO conversations (id, agent_id)
                   VALUES (?, ?)""",
                (conv_id, agent_id),
            )
            conn.commit()
        finally:
            conn.close()
    
    async def get_or_create_conversation(
        self,
        conversation_id: str,
        agent_id: str,
    ) -> str:
        """Get or create a conversation, return its ID."""
        await self.create_conversation(conversation_id, agent_id)
        return conversation_id
    
    # ==================== Message Operations ====================
    
    async def add_message(
        self,
        message_id: str,
        conversation_id: str,
        role: str,
        content: str,
        content_json: Optional[str] = None,
        content_type: str = "text",
        token_count: int = 0,
        metadata: Optional[dict] = None,
    ) -> None:
        """Add a message to the database."""
        await self.initialize()
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            self._add_message_sync,
            message_id,
            conversation_id,
            role,
            content,
            content_json,
            content_type,
            token_count,
            metadata,
        )
    
    def _add_message_sync(
        self,
        msg_id: str,
        conv_id: str,
        role: str,
        content: str,
        content_json: Optional[str],
        content_type: str,
        token_count: int,
        metadata: Optional[dict],
    ) -> None:
        conn = self._get_connection()
        try:
            conn.execute(
                """INSERT OR REPLACE INTO messages
                   (id, conversation_id, role, content, content_json, content_type, token_count, metadata)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    msg_id,
                    conv_id,
                    role,
                    content,
                    content_json,
                    content_type,
                    token_count,
                    json.dumps(metadata) if metadata else None,
                ),
            )
            conn.execute(
                "UPDATE conversations SET message_count = message_count + 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (conv_id,),
            )
            conn.commit()
        finally:
            conn.close()
    
    async def get_messages(
        self,
        conversation_id: str,
        limit: Optional[int] = None,
        offset: int = 0,
        include_compacted: bool = True,
    ) -> list[dict]:
        """Get messages from a conversation."""
        await self.initialize()
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._get_messages_sync,
            conversation_id,
            limit,
            offset,
            include_compacted,
        )
    
    def _get_messages_sync(
        self,
        conv_id: str,
        limit: Optional[int],
        offset: int,
        include_compacted: bool,
    ) -> list[dict]:
        conn = self._get_connection()
        try:
            if include_compacted:
                query = """SELECT * FROM messages 
                           WHERE conversation_id = ? 
                           ORDER BY created_at ASC"""
            else:
                query = """SELECT * FROM messages 
                           WHERE conversation_id = ? AND is_compacted = FALSE
                           ORDER BY created_at ASC"""
            
            if limit:
                query += f" LIMIT {limit} OFFSET {offset}"
            
            cursor = conn.execute(query, (conv_id,))
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()
    
    async def mark_messages_compacted(
        self,
        message_ids: list[str],
        summary_id: str,
    ) -> int:
        """Mark messages as compacted under a summary."""
        await self.initialize()
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._mark_messages_compacted_sync,
            message_ids,
            summary_id,
        )
    
    def _mark_messages_compacted_sync(
        self,
        msg_ids: list[str],
        summary_id: str,
    ) -> int:
        conn = self._get_connection()
        try:
            placeholders = ",".join("?" * len(msg_ids))
            cursor = conn.execute(
                f"""UPDATE messages 
                    SET is_compacted = TRUE, summary_id = ?
                    WHERE id IN ({placeholders})""",
                [summary_id] + msg_ids,
            )
            conn.commit()
            return cursor.rowcount
        finally:
            conn.close()
    
    # ==================== Summary Operations ====================
    
    async def create_summary(
        self,
        summary_id: str,
        conversation_id: str,
        content: str,
        depth: int = 0,
        parent_id: Optional[str] = None,
        source_message_ids: Optional[list[str]] = None,
        source_summary_ids: Optional[list[str]] = None,
        token_count: int = 0,
    ) -> None:
        """Create a summary node in the DAG."""
        await self.initialize()
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            self._create_summary_sync,
            summary_id,
            conversation_id,
            content,
            depth,
            parent_id,
            source_message_ids,
            source_summary_ids,
            token_count,
        )
    
    def _create_summary_sync(
        self,
        summary_id: str,
        conv_id: str,
        content: str,
        depth: int,
        parent_id: Optional[str],
        source_message_ids: Optional[list[str]],
        source_summary_ids: Optional[list[str]],
        token_count: int,
    ) -> None:
        conn = self._get_connection()
        try:
            conn.execute(
                """INSERT INTO summaries
                   (id, conversation_id, parent_id, depth, content, token_count, source_message_ids, source_summary_ids)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    summary_id,
                    conv_id,
                    parent_id,
                    depth,
                    content,
                    token_count,
                    json.dumps(source_message_ids) if source_message_ids else None,
                    json.dumps(source_summary_ids) if source_summary_ids else None,
                ),
            )
            conn.execute(
                "UPDATE conversations SET summary_count = summary_count + 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (conv_id,),
            )
            conn.commit()
        finally:
            conn.close()
    
    async def get_summaries(
        self,
        conversation_id: str,
        depth: Optional[int] = None,
    ) -> list[dict]:
        """Get summaries for a conversation."""
        await self.initialize()
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._get_summaries_sync,
            conversation_id,
            depth,
        )
    
    def _get_summaries_sync(self, conv_id: str, depth: Optional[int]) -> list[dict]:
        conn = self._get_connection()
        try:
            if depth is not None:
                cursor = conn.execute(
                    "SELECT * FROM summaries WHERE conversation_id = ? AND depth = ? ORDER BY created_at",
                    (conv_id, depth),
                )
            else:
                cursor = conn.execute(
                    "SELECT * FROM summaries WHERE conversation_id = ? ORDER BY depth, created_at",
                    (conv_id,),
                )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()
    
    async def get_summary(self, summary_id: str) -> Optional[dict]:
        """Get a specific summary by ID."""
        await self.initialize()
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._get_summary_sync,
            summary_id,
        )
    
    def _get_summary_sync(self, summary_id: str) -> Optional[dict]:
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "SELECT * FROM summaries WHERE id = ?",
                (summary_id,),
            )
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()
    
    # ==================== Search Operations ====================
    
    async def search_messages(
        self,
        conversation_id: str,
        query: str,
        limit: int = 10,
    ) -> list[dict]:
        """Search messages using FTS5 or LIKE fallback."""
        await self.initialize()
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._search_messages_sync,
            conversation_id,
            query,
            limit,
        )
    
    def _search_messages_sync(self, conv_id: str, query: str, limit: int) -> list[dict]:
        conn = self._get_connection()
        try:
            # Try FTS5 first
            if self.enable_fts:
                try:
                    # Escape special FTS characters
                    fts_query = query.replace("'", "''")
                    cursor = conn.execute(
                        """SELECT m.* FROM messages m
                           JOIN messages_fts fts ON m.rowid = fts.rowid
                           WHERE fts.messages_fts MATCH ? AND m.conversation_id = ?
                           ORDER BY m.created_at DESC
                           LIMIT ?""",
                        (fts_query, conv_id, limit),
                    )
                    return [dict(row) for row in cursor.fetchall()]
                except sqlite3.OperationalError:
                    pass  # Fall back to LIKE
            
            # LIKE fallback
            like_query = f"%{query}%"
            cursor = conn.execute(
                """SELECT * FROM messages 
                   WHERE conversation_id = ? AND content LIKE ?
                   ORDER BY created_at DESC
                   LIMIT ?""",
                (conv_id, like_query, limit),
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()
    
    async def search_all(
        self,
        conversation_id: str,
        query: str,
        limit: int = 10,
    ) -> dict:
        """Search both messages and summaries."""
        await self.initialize()
        
        messages = await self.search_messages(conversation_id, query, limit)
        
        # Also search summaries
        loop = asyncio.get_event_loop()
        summaries = await loop.run_in_executor(
            None,
            self._search_summaries_sync,
            conversation_id,
            query,
            limit,
        )
        
        return {
            "messages": messages,
            "summaries": summaries,
        }
    
    def _search_summaries_sync(self, conv_id: str, query: str, limit: int) -> list[dict]:
        conn = self._get_connection()
        try:
            like_query = f"%{query}%"
            cursor = conn.execute(
                """SELECT * FROM summaries 
                   WHERE conversation_id = ? AND content LIKE ?
                   ORDER BY created_at DESC
                   LIMIT ?""",
                (conv_id, like_query, limit),
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()
    
    # ==================== Statistics ====================
    
    async def get_stats(self, conversation_id: str) -> dict:
        """Get statistics for a conversation."""
        await self.initialize()
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._get_stats_sync,
            conversation_id,
        )
    
    def _get_stats_sync(self, conv_id: str) -> dict:
        conn = self._get_connection()
        try:
            # Message stats
            msg_cursor = conn.execute(
                """SELECT 
                    COUNT(*) as total_messages,
                    SUM(token_count) as total_tokens,
                    SUM(CASE WHEN is_compacted THEN 1 ELSE 0 END) as compacted_messages
                   FROM messages WHERE conversation_id = ?""",
                (conv_id,),
            )
            msg_stats = dict(msg_cursor.fetchone())
            
            # Summary stats
            sum_cursor = conn.execute(
                """SELECT 
                    COUNT(*) as total_summaries,
                    MAX(depth) as max_depth,
                    SUM(token_count) as summary_tokens
                   FROM summaries WHERE conversation_id = ?""",
                (conv_id,),
            )
            sum_stats = dict(sum_cursor.fetchone())
            
            return {
                **msg_stats,
                **sum_stats,
            }
        finally:
            conn.close()
    
    # ==================== Expansion ====================
    
    async def expand_summary(self, summary_id: str) -> list[dict]:
        """Expand a summary to get all original messages."""
        await self.initialize()
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._expand_summary_sync,
            summary_id,
        )
    
    def _expand_summary_sync(self, summary_id: str) -> list[dict]:
        """Recursively expand summary to get all messages."""
        conn = self._get_connection()
        try:
            summary = self._get_summary_sync(summary_id)
            if not summary:
                return []
            
            messages = []
            
            # Get direct messages
            source_msg_ids = json.loads(summary.get("source_message_ids") or "[]")
            if source_msg_ids:
                placeholders = ",".join("?" * len(source_msg_ids))
                cursor = conn.execute(
                    f"SELECT * FROM messages WHERE id IN ({placeholders}) ORDER BY created_at",
                    source_msg_ids,
                )
                messages.extend([dict(row) for row in cursor.fetchall()])
            
            # Recursively expand child summaries
            source_sum_ids = json.loads(summary.get("source_summary_ids") or "[]")
            for child_id in source_sum_ids:
                child_messages = self._expand_summary_sync(child_id)
                messages.extend(child_messages)
            
            return messages
        finally:
            conn.close()
    
    # ==================== Cleanup ====================
    
    async def delete_conversation(self, conversation_id: str) -> None:
        """Delete a conversation and all its data."""
        await self.initialize()
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            self._delete_conversation_sync,
            conversation_id,
        )
    
    def _delete_conversation_sync(self, conv_id: str) -> None:
        conn = self._get_connection()
        try:
            conn.execute("DELETE FROM summaries WHERE conversation_id = ?", (conv_id,))
            conn.execute("DELETE FROM messages WHERE conversation_id = ?", (conv_id,))
            conn.execute("DELETE FROM conversations WHERE id = ?", (conv_id,))
            conn.commit()
        finally:
            conn.close()