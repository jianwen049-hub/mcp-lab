"""Transport notes: in-proc vs stdio vs SSE tradeoffs (lab implements in-proc + stdio helper)."""
from __future__ import annotations

import sys
from typing import TextIO

from .server import McpServer


def stdio_serve(server: McpServer, stdin: TextIO | None = None, stdout: TextIO | None = None) -> None:
    """Read newline-delimited JSON requests from stdin, write responses to stdout."""
    inn = stdin or sys.stdin
    out = stdout or sys.stdout
    for line in inn:
        line = line.strip()
        if not line:
            continue
        resp = server.handle_line(line)
        out.write(resp + "\n")
        out.flush()


def tradeoffs() -> dict[str, str]:
    return {
        "inproc": "同进程 handler 调用：单测最快，无序列化损耗；无跨语言边界。",
        "stdio": "子进程 + 换行 JSON：IDE / 桌面 Agent 常见；要处理好缓冲与崩溃回收。",
        "sse": "远程 HTTP+SSE：易穿越网关，需鉴权、心跳、半开连接治理；本仓不实现完整 HTTP。",
    }
