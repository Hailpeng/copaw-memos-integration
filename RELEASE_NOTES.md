# v0.09 - LCM 无损上下文管理

## 新功能

### 🔧 LCM (Lossless Context Management) 模块

实现完整的本地上下文管理，解决长对话丢失消息的问题：

- **SQLite 持久化** - 所有消息存储到 `~/.copaw/lcm.db`，永不丢失
- **DAG 多层摘要** - 智能压缩结构，保护最近 32 条消息
- **FTS5 全文搜索** - 支持中文搜索历史
- **Agent 工具** - `lcm_grep`, `lcm_describe`, `lcm_expand`
- **阈值触发** - 上下文达到 70% 时自动压缩

### 📦 一键安装脚本

```bash
git clone https://github.com/Hailpeng/copaw-memos-integration.git
cd copaw-memos-integration
python install_lcm.py
```

## 架构说明

| 组件 | 存储位置 | 用途 |
|------|----------|------|
| MemOS MCP | 云端 | 跨会话长期记忆 |
| LCM 模块 | 本地 SQLite | 会话内上下文管理 |

## 文件结构

```
lcm/
├── agents/
│   ├── lcm/
│   │   ├── __init__.py    # 导出接口
│   │   ├── config.py      # 配置类
│   │   ├── database.py    # SQLite 持久化
│   │   ├── engine.py      # 主引擎
│   │   ├── compactor.py   # DAG 压缩
│   │   └── tools.py       # Agent 工具
│   └── hooks/
│       └── lcm_hook.py    # 集成 Hook
└── install_lcm.py         # 安装脚本
```

## 参考项目

- [lossless-claw](https://github.com/Martian-Engineering/lossless-claw) (3.2k stars)