# Release v1.1.0 - Windows MCP 管道修复

## 🔧 重要修复

### Windows MCP 会话中断问题

**问题现象**：Windows 下每次对话都会在开发者控制台看到警告：
```
MCP client 'memos-api-mcp' session interrupted while listing tools; trying recovery
```

**根本原因**：
- `npx -y @memtensor/memos-api-mcp@latest` 每次会话启动新进程
- Windows 管道（pipe）在进程切换时断开
- 错误：`WinError 233 管道的另一端上无任何进程`

**解决方案**：
1. 全局安装 MCP 包：`npm install -g @memtensor/memos-api-mcp@latest`
2. 修改 `agent.json` 配置，使用全局命令路径

### 修改内容

**README.md 更新**：
- 新增「步骤 2：全局安装 MCP 包」章节
- 提供 Windows 和 Linux/macOS 两种配置方式
- Windows 用户必须使用全局安装

**配置对比**：

| 方式 | Windows | Linux/macOS |
|------|---------|-------------|
| 全局安装 | ✅ 推荐（必选） | ✅ 推荐 |
| npx 启动 | ❌ 会中断 | ⚠️ 可用 |

## 📦 安装升级

### 新用户安装

```bash
# 1. 全局安装 MCP
npm install -g @memtensor/memos-api-mcp@latest

# 2. 安装 LCM
git clone https://github.com/Hailpeng/copaw-memos-integration.git
cd copaw-memos-integration
pip install reme==1.0.3
python install_lcm.py
```

### 现有用户升级

```bash
# 1. 全局安装 MCP
npm install -g @memtensor/memos-api-mcp@latest

# 2. 更新仓库
cd copaw-memos-integration
git pull

# 3. 修改 agent.json（重要！）
# 将 command 改为全局路径，见 README.md
```

## 🔍 验证修复

重启 Copaw 后检查：

```bash
# Windows - 应看到单个 node 进程
tasklist | findstr node

# 日志不应再有 "session interrupted" 警告
```

## 📋 完整变更

- `README.md`: 新增 MCP 全局安装说明
- 修复 Windows 管道中断问题
- 优化安装流程文档

---

**完整文档**：见 [README.md](README.md)