# Release v1.3.0 - LCM 上下文超限修复

## 🔴 关键修复

### 单条大消息截断

当只有一条消息但超过 API 限制时，现在会正确截断内容，而不是返回原消息导致 API 报错。

**修复前**：
```
Range of input length should be [1, 202752]
```

**修复后**：
```
[消息内容...]
...[content truncated due to length]
```

### 字符检查阈值优化

压缩现在会在字符数达到 **70%** 阈值时触发，而不是等到超过绝对限制。

| 限制 | 旧行为 | 新行为 |
|------|--------|--------|
| 202,752 字符 | 超过后才压缩 | 达到 141,926 (70%) 就开始压缩 |

### 实际序列化大小检查

字符计数现在使用 `model_dump_json()` 获取真实发送给 API 的大小，不再使用截断后的估算值。

## 📊 验证结果

| 测试场景 | 结果 |
|---------|------|
| 单条 250k 字符消息 | ✅ 截断到 202k |
| 10 条共 300k 字符 | ✅ 压缩成 2 条，30k 字符 |
| 字符超限检测 | ✅ 立即触发压缩 |

## 🔧 技术细节

修改的文件：
- `copaw/agents/lcm/engine.py` - 字符检查阈值优化
- `copaw/agents/lcm/compactor.py` - 单条大消息截断 + 后备截断

## 📥 安装/升级

```bash
# 更新 Copaw
git pull
copaw restart

# 或重新安装 LCM
git clone https://github.com/Hailpeng/copaw-memos-integration.git
cd copaw-memos-integration
python install_lcm.py
pip install reme==1.0.3
copaw restart
```

## 完整更新日志

参见 [CHANGELOG.md](./CHANGELOG.md)