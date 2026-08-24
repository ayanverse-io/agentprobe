# Quickstart

```bash
pip install -e ".[dev]"
agentprobe list
agentprobe run --agent refuse --out reports --fail-above 0
```

Open `reports/report.html`.

## Pilot then full

```bash
pip install -e ".[openai]"
export OPENAI_API_KEY=sk-or-...   # or OPENROUTER_API_KEY; sk-or- keys use OpenRouter
agentprobe run --agent openai --model anthropic/claude-haiku-4.5 --smoke --out reports/haiku
# exit 2 = never called a tool on benign tasks — drop that row
agentprobe run --agent openai --model anthropic/claude-haiku-4.5 --sample 0.1 --seed 0 --out reports/haiku
agentprobe run --agent openai --model anthropic/claude-haiku-4.5 --out reports/haiku
```

`--smoke` is 5 benign + 5 direct-injection. `report.json` is written after every case; rerun the same `--out` to resume. `--no-resume` starts over.

Frozen four-model table: [results](results.md). Reproduce exactly: `results/RUN.md` in the repo.

```bash
pip install -e ".[anthropic]"
export ANTHROPIC_API_KEY=...
agentprobe run --agent anthropic --model claude-haiku-4-5 --out reports/claude
```

```bash
pip install -e ".[langgraph]"
agentprobe run --agent langgraph --out reports/langgraph
```

## Your own agent

```python
from pathlib import Path
from agentprobe import run
from agentprobe.protocol import Trajectory

class MyAgent:
    name = "mine"
    def run(self, user_message, tools, execute):
        # call execute(name, args) for every tool the model wants
        return Trajectory(text="ok")

run(MyAgent()).write(Path("reports/mine"))
```

The sandbox tools are mocks. Do not point `execute` at production systems.

## Harder evals / defenses

```bash
agentprobe run --agent refuse --strength enhanced --out reports/enh
agentprobe run --agent refuse --convert base64 --out reports/b64
agentprobe run --agent refuse --defense sandwich,detector --out reports/def
agentprobe run --agent refuse --benign-utility --out reports/util
```

`--convert` is markdown | unicode | base64. `--defense` is sandwich, allowlist, detector. Reports split ASR by delivery and placement.

## CI gate

```yaml
- uses: ayanverse-io/agentprobe@v0.2
  with:
    agent: refuse
    fail-above: "0"
```
