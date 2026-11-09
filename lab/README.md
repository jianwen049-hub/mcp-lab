# lab — MCP-shaped offline Python package

| Module | Role |
|--------|------|
| `protocol.py` | JSON-RPC-ish request/response + version label |
| `schema.py` | minimal JSON Schema validator |
| `security.py` | PII redaction + allow-list permission gate |
| `tools_catalog.py` | tools / resources / prompts (payment·risk·ops) |
| `server.py` | `initialize` / `tools/*` / `resources/*` / `prompts/*` |
| `client.py` | list + call + read |
| `transport.py` | stdio helper + tradeoff notes |
| `failures.py` | hang / partial JSON / version skew drills |

```bash
export PYTHONPATH=src
python3 scripts/smoke_check.py
python3 -m mcp_lab.cli demo
```
