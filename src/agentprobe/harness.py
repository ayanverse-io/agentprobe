from __future__ import annotations

import random
import time
from pathlib import Path

from agentprobe.cases import Case, load_cases
from agentprobe.defense import apply_defense
from agentprobe.judge import attack_succeeded, over_refused, utility_held
from agentprobe.judge_llm import maybe_llm_judge
from agentprobe.protocol import AgentUnderTest, Trajectory
from agentprobe.report import CaseResult, Report, calls_as_dicts, load_report
from agentprobe.sandbox import Sandbox
from agentprobe.transform import apply_case

SMOKE_PER_CATEGORY = 5


def _label(
    agent: AgentUnderTest,
    strength: str,
    convert: str,
    defense: tuple[str, ...],
    benign_utility: bool,
) -> str:
    parts = [agent.name]
    if strength == "enhanced":
        parts.append("enh")
    if convert != "none":
        parts.append(convert)
    parts.extend(defense)
    if benign_utility:
        parts.append("util")
    return "+".join(parts)


def run_case(agent: AgentUnderTest, case: Case, defense: tuple[str, ...] = ()) -> CaseResult:
    box = Sandbox.from_case(case)
    tools, execute, msg = apply_defense(
        defense, case, box.specs(), box.execute, case.user_message()
    )
    t0 = time.perf_counter()
    traj = agent.run(msg, tools, execute)
    latency = time.perf_counter() - t0
    calls = tuple(box.calls) if box.calls else traj.tool_calls
    scored = Trajectory(calls, traj.text)
    hit = attack_succeeded(case, scored)
    llm = maybe_llm_judge(case, scored)
    if llm is not None:
        hit = llm
    held = utility_held(case, scored)
    return CaseResult(
        id=case.id,
        category=case.category,
        attack_succeeded=hit,
        latency_s=latency,
        text=traj.text,
        tool_calls=calls_as_dicts(calls),
        utility_held=held,
        over_refused=over_refused(case, scored, held),
        delivery=case.delivery,
        placement=case.placement,
    )


def smoke_case_ids() -> set[str]:
    cases = load_cases()
    ids: list[str] = []
    for cat in ("benign", "direct_injection"):
        ids.extend([c.id for c in cases if c.category == cat][:SMOKE_PER_CATEGORY])
    return set(ids)


def sample_case_ids(frac: float, seed: int = 0) -> set[str]:
    """Stratified sample so 10% is not 34 benign files in a row."""
    if not 0 < frac <= 1:
        raise ValueError("sample fraction must be in (0, 1]")
    rng = random.Random(seed)
    by_cat: dict[str, list[str]] = {}
    for case in load_cases():
        by_cat.setdefault(case.category, []).append(case.id)
    ids: list[str] = []
    for group in by_cat.values():
        n = min(len(group), max(1, round(len(group) * frac)))
        ids.extend(rng.sample(group, n))
    return set(ids)


def run(
    agent: AgentUnderTest,
    category: str | None = None,
    case_ids: set[str] | None = None,
    out: Path | None = None,
    resume: bool = True,
    strength: str = "base",
    convert: str = "none",
    defense: tuple[str, ...] = (),
    benign_utility: bool = False,
) -> Report:
    cases = [
        apply_case(c, strength=strength, convert=convert, benign_utility=benign_utility)
        for c in load_cases(category)
    ]
    if case_ids:
        stems = set(case_ids)
        cases = [c for c in cases if c.id in stems or c.id.split("#", 1)[0] in stems]
    label = _label(agent, strength, convert, defense, benign_utility)
    done: dict[str, CaseResult] = {}
    if out and resume:
        prev = load_report(out)
        if prev is not None:
            if prev.agent != label:
                raise ValueError(
                    f"resume mismatch: {prev.agent!r} vs {label!r} "
                    "(pass --no-resume or a new --out)"
                )
            done = {r.id: r for r in prev.results}
    results: list[CaseResult] = []
    for case in cases:
        if case.id in done:
            results.append(done[case.id])
            continue
        results.append(run_case(agent, case, defense=defense))
        if out:
            merged = {**done, **{r.id: r for r in results}}
            Report(agent=label, results=list(merged.values())).write(out)
    return Report(agent=label, results=results)
