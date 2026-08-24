from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from agentprobe.protocol import ExecuteFn, ToolCall, ToolSpec, Trajectory


@dataclass
class ModelTurn:
    text: str = ""
    tool_calls: tuple[ToolCall, ...] = ()


class Completer(Protocol):
    def complete(self, messages: list[dict[str, Any]], tools: list[ToolSpec]) -> ModelTurn: ...


def run_tool_loop(
    user_message: str,
    tools: list[ToolSpec],
    execute: ExecuteFn,
    completer: Completer,
    max_steps: int = 8,
) -> Trajectory:
    messages: list[dict[str, Any]] = [{"role": "user", "content": user_message}]
    calls: list[ToolCall] = []
    texts: list[str] = []
    for _ in range(max_steps):
        turn = completer.complete(messages, tools)
        if turn.text:
            texts.append(turn.text)
        if not turn.tool_calls:
            break
        results = []
        for call in turn.tool_calls:
            calls.append(call)
            results.append({"name": call.name, "result": execute(call.name, call.arguments)})
        messages.append(
            {
                "role": "assistant",
                "content": turn.text,
                "tool_calls": [{"name": c.name, "arguments": c.arguments} for c in turn.tool_calls],
            }
        )
        messages.append({"role": "tool", "results": results})
    return Trajectory(tuple(calls), "\n".join(texts))
