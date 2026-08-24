"""Optional Inspect (UK AISI) adapter. `pip install -e ".[inspect]"` then `inspect eval` this module."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from agentprobe.cases import Case, load_cases
from agentprobe.transform import apply_case


def dataset_records(
    cases: Sequence[Case] | None = None,
    *,
    strength: str = "base",
    convert: str = "none",
    benign_utility: bool = False,
) -> list[dict[str, Any]]:
    rows = cases if cases is not None else load_cases()
    out: list[dict[str, Any]] = []
    for case in rows:
        c = apply_case(case, strength=strength, convert=convert, benign_utility=benign_utility)
        out.append(
            {
                "id": c.id,
                "input": c.user_message(),
                "target": c.success.kind,
                "metadata": {
                    "category": c.category,
                    "delivery": c.delivery,
                    "placement": c.placement,
                    "inspired_by": c.inspired_by,
                },
            }
        )
    return out


def inspect_task(
    agent: str = "openai",
    model: str | None = None,
    *,
    strength: str = "base",
    convert: str = "none",
    defense: str = "",
    benign_utility: bool = False,
    category: str | None = None,
) -> Any:
    """Build an Inspect Task that runs AgentProbe's harness per sample."""
    try:
        from inspect_ai import Task
        from inspect_ai.dataset import MemoryDataset, Sample
        from inspect_ai.scorer import Score, accuracy, scorer
        from inspect_ai.solver import solver
    except ImportError as exc:
        raise ImportError("Inspect extra missing: pip install -e '.[inspect]'") from exc

    from agentprobe.adapters import build_agent
    from agentprobe.defense import parse_defenses
    from agentprobe.harness import run_case

    cases = [
        apply_case(c, strength=strength, convert=convert, benign_utility=benign_utility)
        for c in load_cases(category)
    ]
    by_id = {c.id: c for c in cases}
    defs = parse_defenses(defense)
    dataset = MemoryDataset(
        [
            Sample(
                id=c.id,
                input=c.user_message(),
                target=c.success.kind,
                metadata={"category": c.category},
            )
            for c in cases
        ]
    )

    @solver
    def agentprobe_solver():
        async def solve(state, generate):
            case = by_id[str(state.sample_id)]
            result = run_case(build_agent(agent, model), case, defense=defs)
            state.output.completion = result.text
            state.metadata["attack_succeeded"] = result.attack_succeeded
            state.metadata["utility_held"] = result.utility_held
            return state

        return solve

    @scorer(metrics=[accuracy()])
    def robust():
        async def score(state, target):
            safe = not bool(state.metadata.get("attack_succeeded"))
            return Score(value=1.0 if safe else 0.0)

        return score

    return Task(dataset=dataset, solver=agentprobe_solver(), scorer=robust())
