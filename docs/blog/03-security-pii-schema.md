# 03 · 最小权限、PII 脱敏与 Schema 校验

## 当时业务痛点是什么

联调周发生两件「够写复盘」的事：

1. **退款助手角色**被产品临时要求「顺手建个工单」——开发把 `create_ops_ticket` 加进同一 tool 列表。结果模型在用户只是问「多久到账」时，也创建了十几张空工单。
2. **用户原话里的手机号**被模型原样塞进 `device_fingerprint` / 工单 title，落进运营系统明文检索。

这不是模型「变坏了」，是**权限面过大 + 出域前无脱敏 + schema 过宽**。

## 当时我怎么看这个问题

Agent 工具层的安全基线应接近后端微服务：

- **最小权限**：角色 allow-list，而不是「服务器有什么就暴露什么」；
- **出域脱敏**：PII 在离开模型沙箱 / 进入外部 handler 前处理；
- **强 schema**：required / additionalProperties:false，拒绝「顺手多传」；
- **失败显式**：权限与 schema 错误要有稳定错误码，供运行时改计划，而不是 500 糊成一团。

## 试过什么

1. **靠 prompt「不要创建工单」**：模型听话率随温度与厂商波动。
2. **在 handler 里 if 拒绝**：可以，但每个工具复制；且 list_tools 仍展示给模型，诱发幻觉调用。
3. **出域后由接收方脱敏**：工单系统若未做，就泄漏；且日志可能已落盘。
4. **schema 只校验类型不关 additionalProperties**：模型多传 `ssn` 也能进去。

## 为什么否决

否决「prompt 当授权」。授权是控制面，必须在 Client/Server 门闸强制。  
否决「list 全部工具但靠 handler 拒绝」作为唯一手段——仍污染模型可选动作集；本仓 **PermissionGate 在 call 时强制**，同时 demo 里给退款助手的 allow-list **根本不含**工单工具（list 仍可见全部是为了教学；生产应对不同连接做 filtered list）。

## 最终怎么解

### PermissionGate

```python
PermissionGate({"lookup_refund", "risk_score"}).check(name)
```

失败 → RPC error `-320403`。

### redact_obj / redact_text

手机号、身份证、邮箱、长数字卡号粗脱敏为 `[REDACTED_*]`。在 `call_tool` 里 **schema 通过之后、handler 之前** 执行，避免「校验用明文、执行也用明文」的疏漏；注意：若业务主键必须是手机号，应走单独的 tokenization，而不是一刀切——实验室演示默认红线。

### schema.validate

支持 object/string/integer/number/boolean/array 与 `required`、`additionalProperties: false`、`minLength`。失败 → `-32602`。

## 用到的具体 skill / 技巧清单

| Skill | 用法 |
|-------|------|
| **Allow-list 门闸** | 角色 → 可调工具集合 |
| **错误码稳定** | `-320403` 权限 / `-32602` 参数 |
| **调用前脱敏** | 防 PII 出域 |
| **additionalProperties:false** | 堵多传 |
| **minLength** | 空订单号直接打回 |
| **演示与生产差异写明** | list 过滤 vs call 门闸 |
| **脱敏不等于加密** | 合规仍要审计链路 |

## 代码解析（按文件路径）

### `lab/src/mcp_lab/security.py`

正则粗粒度， intentionally simple。生产应接专业 DLP，并按字段策略（订单号保留、手机号 token 化）。

### `lab/src/mcp_lab/schema.py`

`SchemaError` 独立异常，Server 映射到 JSON-RPC invalid params。

### `lab/src/mcp_lab/server.py` → `call_tool`

顺序：**permission → schema → redact → hang hook → handler**。顺序很重要：先授权再解析，避免无权限者用畸形 payload 探 schema；脱敏在校验后，保证类型正确再改写字符串。

### `lab/src/mcp_lab/cli.py`

demo 打印 `ticket_denied`，证明门闸生效。

## 线上 / 联调还会踩的坑

1. **list_tools 未按角色过滤**：模型看见不能调的工具，仍会尝试，徒增延迟与噪声——生产务必 filtered list。
2. **脱敏破坏指纹**：风控设备指纹若被改成带 `REDACTED` 的串，分数失真；应对「已知非 PII 字段」白名单跳过。
3. **日志中的 args**：门闸前若已打日志，仍泄漏；日志管线也要脱敏。
4. **schema 过严**：枚举没更新时，全线失败；要用契约测试锁住。
5. **把 API Key 放进 tool args**：应走 server 侧环境变量 / vault，永不进模型上下文。
6. **多租户**：allow-list 还要叠租户隔离，否则 A 商户工具打到 B 数据。
