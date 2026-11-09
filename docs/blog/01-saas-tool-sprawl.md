# 01 · 每个 SaaS 都自造 Agent Tools，为什么会痛

## 当时业务痛点是什么

做一个「支付 + 风控 + 运营」联合助手时，对接面很快变成动物园：

- 支付中台给了一套 OpenAPI，我们写了 `PaymentToolkit`；
- 风控给了 gRPC，我们又写了 `RiskFunctions`；
- 工单系统是 REST + 自定义「AI Action」JSON；
- 客服知识库又是另一套「plugin manifest」。

Agent 运行时要同时理解四套「工具描述方言」：字段叫 `parameters` 还是 `input_schema`？错误是 HTTP 404 还是 `isError`？鉴权是挂在工具参数里还是进程环境？

两周后的现场：

1. **改一个退款查询字段**，要动三份 adapter + 两份 prompt 说明；
2. **模型偶发把手机号塞进 tool args**，明文打到工单；
3. **同一业务能力多个名字**（`refund_query` / `lookupRefund` / `get_refund`），planner 选错；
4. **本地能跑、IDE 插件不能跑**——因为传输假设不同（HTTP vs stdio）。

## 当时我怎么看这个问题

问题不是「少写几个 adapter」，而是缺少**稳定的工具契约层**：

- 发现（list tools）
- 描述（JSON Schema）
- 调用（call + 结构化结果）
- 资源读取（只读知识 / 配置）
- 提示模板（prompts）
- 传输（stdio / HTTP+SSE…）

MCP 把这些收成一套协议形状。实验室不必声明「实现了完整 MCP 规范」，但**消息形状对齐**后，博客与代码才能谈清边界。

## 试过什么

1. **继续堆 adapter**：短期最快，长期 schema 漂移无解。
2. **强迫所有系统出同一份 OpenAPI 3**：政治成本高，且 OpenAPI 不覆盖「prompts」与「agent 资源」。
3. **只把工具写进 system prompt 文本**：无校验、无鉴权、不可发现。
4. **上某云的 proprietary plugin 格式**：绑死供应商，桌面 Agent / 开源 runtime 不通用。

## 为什么否决

否决「adapter 丛林」。支付域工具一旦涉及资金与 PII，**契约必须可版本化、可校验、可最小授权**。  
否决「prompt 即工具目录」——那是把类型系统交给模型幻觉。

## 最终怎么解

本仓 `tools_catalog.py` 用统一 `ToolSpec`：

- `name` / `description` / `input_schema` / `handler`
- 另有 `ResourceSpec`（SLA、拒绝码手册）与 `PromptSpec`（退款助手模板）

`protocol.py` 提供 JSON-RPC 2.0 风格的 request/response，以及实验室协议版本标签 `2024-11-05`。  
Server 暴露：`initialize`、`tools/list`、`tools/call`、`resources/list`、`resources/read`、`prompts/list`、`prompts/get`。

业务例子刻意贴近现场：

| Tool | 域 | 副作用 |
|------|----|--------|
| `lookup_refund` | 支付 | 只读 |
| `risk_score` | 风控 | 只读 |
| `create_ops_ticket` | 运营 | **有**副作用 → 默认不给退款助手权限 |

## 用到的具体 skill / 技巧清单

| Skill | 用法 |
|-------|------|
| **统一 ToolSpec** | 消灭三套方言 |
| **JSON Schema 进仓库** | 与 handler 同 PR 变更 |
| **Resources 与 Tools 分离** | 知识只读走 resource，动作走 tool |
| **Prompts 模板化** | 系统提示带参数，不靠复制粘贴 |
| **JSON-RPC id** | 请求响应可关联，便于追踪 |
| **能力宣告** | initialize 返回 capabilities |
| **副作用显式** | 工单工具默认不进只读角色 |

## 代码解析（按文件路径）

### `lab/src/mcp_lab/protocol.py`

`JsonRpcRequest` / `JsonRpcResponse` / `parse_message`。故意对 `jsonrpc != "2.0"` 抛错，方便演练版本问题。

### `lab/src/mcp_lab/tools_catalog.py`

种子数据含 `ORD-2024-881`（可退）与 `ORD-2024-999`（R-403 阻断）。Resource 返回 Markdown，便于 Agent 当上下文。

### `lab/src/mcp_lab/server.py` / `client.py`

Server 是状态机：未 `initialize` 拒绝业务方法。Client 封装 list/call/read/get_prompt，并把 tool 文本结果尝试 `json.loads`。

## 线上 / 联调还会踩的坑

1. **工具重名跨 server**：多 MCP server 同时挂载时，runtime 要做命名空间，否则 `risk_score` 冲突。
2. **描述写得像营销文案**：模型会过度调用；描述应写清「何时不要调用」。
3. **把写操作伪装成 lookup**：审计与权限模型会崩；命名就要暴露副作用。
4. **schema 只用文档不做运行时校验**：等于没有 schema。
5. **initialize 被跳过**：有的客户端重连只发 tools/list——本仓选择严格拒绝，逼连接生命周期正确。
