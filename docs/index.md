# AgentProbe

Red-team harness for tool-using LLM agents. Attacks succeed only if the agent **calls a forbidden sandbox tool** or **leaks a canary in tool arguments**.

```bash
pip install -e ".[dev]"
agentprobe list
agentprobe run --agent refuse --fail-above 0
agentprobe run --agent obey --out reports
```

Plug in your agent by implementing `AgentUnderTest.run(user_message, tools, execute)`. Reference adapters: Anthropic, OpenAI, a plain-Python loop, LangGraph.

[Quickstart](quickstart.md) · [Judge prompt](judge.md) · [Published results](results.md)
