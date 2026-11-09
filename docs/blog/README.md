# 技术博客（中文深拆）

围绕 **MCP（Model Context Protocol）在 Agent 系统中的工具/资源/提示契约**：为什么每个 SaaS 自造 tools 会痛、stdio vs SSE、最小权限与 PII、失败演练。

| # | 标题 | 代码锚点 |
|---|------|----------|
| [01](./01-saas-tool-sprawl.md) | 每个 SaaS 都自造 Agent Tools，为什么会痛 | `tools_catalog.py` · `protocol.py` |
| [02](./02-server-client-transport.md) | Server/Client、Tools/Resources/Prompts 与传输取舍 | `server.py` · `client.py` · `transport.py` |
| [03](./03-security-pii-schema.md) | 最小权限、PII 脱敏与 Schema 校验 | `security.py` · `schema.py` |
| [04](./04-failure-modes.md) | 挂起、半截 JSON、版本漂移 | `failures.py` · `server.handle_line` |
