# mcp-lab — Model Context Protocol for Real Agents

> Open lab on **MCP-shaped** tool/resource/prompt contracts: a tiny stdio-friendly server, a client that lists & calls tools, least-privilege + PII redaction, schema validation, and failure drills (hang / partial JSON / version skew). Pure Python stdlib — no API key.

**Author:** 马健文 / Evans Owen ([jianwen049-hub](https://github.com/jianwen049-hub))

| | |
|---|---|
| **Lab** | [`lab/`](./lab/) — protocol · server · client · security · failures · smoke |
| **Blog** | [`docs/blog/`](./docs/blog/) |
| **Bio** | [`PROFILE.md`](./PROFILE.md) |

## 中文速览

每个 SaaS 都自己发明一套「给 Agent 用的 tools」时，schema 漂移、鉴权边界不清、PII 随参数出域就会变成日常事故。MCP 想解决的是**稳定的工具/资源/提示契约与传输**。本仓用标准库把消息形状与安全护栏跑通，博客按支付/风控/运营集成现场写坑。

## Reading guide (EN)

```bash
cd lab
export PYTHONPATH=src
python3 scripts/smoke_check.py
python3 -m mcp_lab.cli demo
python3 -m unittest discover -s tests -v
```

## License

MIT — see [`LICENSE`](./LICENSE).
