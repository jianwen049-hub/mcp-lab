# 02 · Server/Client、Tools/Resources/Prompts 与传输取舍

## 当时业务痛点是什么

同一个工具目录，在三种环境行为不一致：

- 单测里：直接 Python import handler；
- 桌面 Agent：拉起子进程，stdin/stdout 换行 JSON；
- 线上网关：HTTP + 流式事件。

如果不把 **协议消息** 与 **传输** 拆开，就会出现「单测绿、IDE 红、网关超时」的经典三重奏。

## 当时我怎么看这个问题

MCP 心智模型：

```
Agent Runtime (Client)
        │  JSON-RPC-ish messages
        ▼
MCP Server (tools/resources/prompts)
        │
   handlers / readers / renderers
```

传输只是管道：

- **in-proc**：`client(handler=server.handle_line)` —— 本仓单测默认；
- **stdio**：子进程，一行一个 JSON；
- **SSE/HTTP**：远程，需鉴权与心跳（本仓只文档化取舍，不实现完整 HTTP）。

## 试过什么

1. **Client 直接 import handler**：快，但跨语言 / 跨进程为零。
2. **只做 HTTP REST `/tools/call`**：桌面 IDE 插件生态不买账；本地调试要端口与证书。
3. **WebSocket 双向**：强，但运维与代理更重。
4. **把 resource 也做成 tool「read_file」**：权限模型变糊——读知识与写工单混在同一允许列表。

## 为什么否决

否决「Client 绑死某一种传输」。协议消息稳定后，传输可替换。  
否决「万物皆 tool」。Resources / Prompts 有独立 list/get，是为了**最小权限与缓存策略**（资源可 ETag，工具调用不可乱缓存）。

## 最终怎么解

### 生命周期

1. `initialize`（互换 protocolVersion / capabilities / serverInfo）
2. `tools/list` · `resources/list` · `prompts/list`
3. `tools/call` / `resources/read` / `prompts/get`
4. （可选）`ping`

### stdio

`transport.stdio_serve`：逐行 `handle_line`，写回一行响应。注意：**stdout 只能留协议**，日志打 stderr，否则 IDE 解析炸。

### 取舍表（代码里 `tradeoffs()`）

| 传输 | 适合 | 代价 |
|------|------|------|
| in-proc | 单测 / 同语言嵌入 | 无隔离 |
| stdio | 本地 IDE、桌面 Agent | 缓冲、崩溃回收、半截行 |
| SSE | 远程多租户 | 鉴权、心跳、网关缓冲 |

## 用到的具体 skill / 技巧清单

| Skill | 用法 |
|-------|------|
| **消息与传输分离** | `handle_line(str)->str` 作为界 |
| **initialize 握手** | 版本与能力协商 |
| **三类原语** | tools / resources / prompts |
| **stdio 一行一帧** | 简单、易抓包 |
| **日志走 stderr** | 保护 stdout 协议 |
| **Client 解包 content** | text → JSON 习惯 |

## 代码解析（按文件路径）

### `lab/src/mcp_lab/server.py`

`dispatch` 按 method 分支；`call_tool` 串起权限 → schema → 脱敏 → 可选 hang → handler。

### `lab/src/mcp_lab/client.py`

`McpClient.request` 统一抛 `RuntimeError` 带上 RPC code/message，CLI 与测试好看懂。

### `lab/src/mcp_lab/transport.py`

`stdio_serve` + `tradeoffs()`。博客读者若要接真实 MCP SDK，可把 `handle_line` 背后的 dispatch 迁过去。

### `lab/src/mcp_lab/cli.py`

`demo`：最小权限门闸 + 一次完整 list/call/read/prompt + 故意触发工单拒绝。

## 线上 / 联调还会踩的坑

1. **Python print 污染 stdout**：子进程模式立刻 JSON parse fail。
2. **全缓冲**：管道下 stdout block；`flush()` 或 `PYTHONUNBUFFERED=1`。
3. **SSE 网关缓冲**：与 Spring AI 篇同一坑，打字/事件会黏成一块。
4. **超大 resource**：一次 read 几 MB Markdown 会撑爆上下文；要做分页或切片 resource。
5. **prompts/get 缺参**：应 schema 失败，而不是渲染出「订单：None」。
