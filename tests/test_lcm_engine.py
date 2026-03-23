import sys
import types
import importlib
import pytest

# Ensure the test can import the local Copaw LCM engine without relying on installed packages
sys.path.insert(0, "D:\\PythonEnv\\copaw-memos-integration")

# Stub agentscope package to satisfy engine imports
agentscope = types.ModuleType("agentscope")
message_mod = types.ModuleType("agentscope.message")
class Msg:
    def __init__(self, id=None, role="user", content=None, name=None):
        self.id = id or "mock-id"
        self.role = role
        self.content = content if content is not None else ""
        self.name = name
    def model_dump_json(self):
        return "{}"
message_mod.Msg = Msg
class TextBlock: pass
class ToolUseBlock: pass
class ToolResultBlock: pass
message_mod.TextBlock = TextBlock
message_mod.ToolUseBlock = ToolUseBlock
message_mod.ToolResultBlock = ToolResultBlock
agentscope.message = message_mod
import sys as _sys
_sys.modules["agentscope"] = agentscope
_sys.modules["agentscope.message"] = message_mod

# Import the engine after the stubs are in place
engine = importlib.import_module("lcm.agents.lcm.engine")

class DummyDB:
    def __init__(self, *args, **kwargs):
        self.initialized = False
        self.messages = []
    async def initialize(self):
        self.initialized = True
    async def get_or_create_conversation(self, conversation_id, agent_id):
        pass
    async def add_message(self, message_id, conversation_id, role, content, content_json, content_type, token_count, metadata=None):
        self.messages.append({
            "message_id": message_id,
            "conversation_id": conversation_id,
            "role": role,
            "content": content,
            "content_json": content_json,
            "content_type": content_type,
            "token_count": token_count,
            "metadata": metadata,
        })
    async def get_messages(self, conversation_id, limit, include_compacted):
        return []
    async def get_summaries(self, conversation_id):
        return []
    async def get_stats(self, conversation_id):
        return {}
    async def search_all(self, conversation_id, query, limit):
        return {}
    async def search_messages(self, conversation_id, query, limit):
        return []
    async def expand_summary(self, summary_id):
        return []

class DummyTokenCounter:
    async def count(self, messages=None, text=""):
        return max(1, len(str(text).split()))

def _setup_engine_with_db():
    engine.LCMDatabase = DummyDB

@pytest.mark.asyncio
async def test_ingest_serializes_blocks_and_counts_tokens():
    _setup_engine_with_db()
    class Cfg: pass
    cfg = Cfg()
    cfg.db_path = "/tmp/dummy-lcm.db"
    cfg.enable_fts = False
    cfg.context_threshold = 0.7
    cfg.fresh_tail_count = 32

    eng = engine.LCMEngine(cfg, "agent1", "conv1", token_counter=DummyTokenCounter())
    eng.db = DummyDB()

    class MsgObj: pass
    msg = MsgObj()
    msg.id = "m1"
    msg.role = "user"
    msg.name = "tester"
    msg.content = [
        {"type": "text", "text": "hello world"},
        {"type": "tool_use", "name": "echo", "input": {"a": "b"}},
        {"type": "tool_result", "content": "ok"},
    ]
    await eng.ingest([msg])

    assert len(eng.db.messages) == 1
    rec = eng.db.messages[0]
    assert "content" in rec
    assert "[Tool:" in rec["content"]
    assert rec["content_type"] == "tool"
    assert "token_count" in rec and rec["token_count"] > 0

@pytest.mark.asyncio
async def test_count_tokens_considers_tool_blocks():
    _setup_engine_with_db()
    class Cfg: pass
    cfg = Cfg()
    cfg.db_path = "/tmp/dummy-lcm2.db"
    cfg.enable_fts = False
    cfg.context_threshold = 0.7
    cfg.fresh_tail_count = 32

    eng = engine.LCMEngine(cfg, "agent1", "conv1", token_counter=DummyTokenCounter())
    eng.db = DummyDB()

    class MsgObj: pass
    msg = MsgObj()
    msg.id = "m2"
    msg.role = "user"
    msg.name = "tester2"
    msg.content = [
        {"type": "text", "text": "action start"},
        {"type": "tool_use", "name": "calc", "input": {"a": 1, "b": 2}},
        {"type": "tool_result", "content": "result"},
    ]
    await eng.ingest([msg])
    assert len(eng.db.messages) == 1
    assert eng.db.messages[0]["token_count"] > 0
