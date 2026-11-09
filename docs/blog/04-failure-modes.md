# 04 · 挂起、半截 JSON、版本漂移

## 当时业务痛点是什么

Agent 运行时最难查的三类故障：

1. **Tool 挂起**：下游工单 HTTP 卡住，Agent 整条链路阻塞，用户以为「AI 死了」。
2. **半截 JSON**：stdio 缓冲 / 日志污染 / 进程被杀，Client 读到残缺帧，报错含糊。
3. **版本漂移**：Server 升级了字段含义，Client 仍按旧 protocolVersion 解，间歇性诡异。

这些在支付夜忙时会被放大成「大面积超时」。

## 当时我怎么看这个问题

协议实验室必须**内置失败演练**，而不是等生产造数据。本仓 `failures.py` 提供三种 drill，Smoke 强制跑。

## 试过什么

1. **只设 HTTP 超时**：stdio 子进程挂起不一定走 HTTP；要在 Client 侧有总超时。
2. **解析失败就重试同一行**：半截帧重试无意义，需要帧边界恢复策略。
3. **忽略 protocolVersion**：短期省事，长期「为什么线上偶发缺字段」变成玄学。
4. **挂起时自动取消并换模型重说**：可能重复副作用（又回到幂等话题）。

## 为什么否决

否决「没有演练的超时配置」。配置是静的，演练证明路径通。  
否决「解析失败当业务失败」——应用 `-32700 parse error` 区分。

## 最终怎么解

### 挂起

`McpServer(hang_tools={"create_ops_ticket"}, hang_seconds=...)` 在 handler 前 `sleep`。真实系统应：

- Client 对 `tools/call` 设 deadline；
- 超时后标记工具错误，**不要**自动重放有副作用的 call；
- 对只读工具可有限重试。

### 半截 JSON

`handle_line` 对 `json.JSONDecodeError` 回 `-32700`。演练故意丢掉结尾 `}`。生产 stdio 还要处理：**粘包**（一行多个 JSON）与 **拆包**（一个 JSON 跨多行）——本仓约定 NDJSON 一行一帧，简单但要文档化。

### 版本漂移

Client 传 `2099-01-01`，Server 仍返回自己的 `PROTOCOL_VERSION`。Client 应比较并告警；不兼容则拒绝后续调用。本仓演示「Server 宣告自身版本」。

## 用到的具体 skill / 技巧清单

| Skill | 用法 |
|-------|------|
| **可注入 hang** | 单测不靠真下游 |
| **JSON-RPC 错误码** | parse / invalid / business 分离 |
| **NDJSON 约定** | 一行一帧 |
| **版本宣告** | initialize 返回 server protocolVersion |
| **副作用超时策略** | 超时 ≠ 自动重试 |
| **Smoke 绑 drill** | 防止演练代码腐坏 |

## 代码解析（按文件路径）

### `lab/src/mcp_lab/failures.py`

`drill_hang` / `drill_partial_json` / `drill_version_skew`。

### `lab/src/mcp_lab/server.py` → `handle_line`

分层 catch：`JSONDecodeError` → `-32700`；`ValueError`（版本字段等）→ `-32600`；`SchemaError` → `-32602`；`PermissionError` → `-320403`。

### `lab/scripts/smoke_check.py`

强制跑 partial JSON 与 version skew；再跑 unittest 与 demo。

## 线上 / 联调还会踩的坑

1. **超时后下游仍成功**：Client 已报错，工单却建了——需要幂等键或探活。
2. **错误码被吞成字符串**：上层应用用 `if "error" in text` 脆弱；保留结构化 error。
3. **多路复用同一 stdout**：两个 Client 写同一子进程必乱——一进程一会话。
4. **协议扩展字段**：老 Client 应忽略未知字段；Server 勿随便改现有字段语义，宁可新 method。
5. **部分成功**：batch tool 调用中一个挂起——本仓单 call 语义，生产 batch 要有部分失败模型。

## 收束

MCP 对业务的价值，是把 Agent 集成从「每个 SaaS 自说自话」拉回**可版本化的契约**。配合最小权限、脱敏、schema 与失败演练，才有资格接支付 / 风控 / 运营。本仓是离线形状实验室；接到真实 MCP SDK 时，把 `dispatch` 与护栏迁过去即可。
