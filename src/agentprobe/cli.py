from __future__ import annotations

import argparse
import sys
from pathlib import Path

from agentprobe.adapters import build_agent
from agentprobe.cases import load_cases
from agentprobe.defense import parse_defenses
from agentprobe.harness import run, sample_case_ids, smoke_case_ids
from agentprobe.report import load_report


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="agentprobe")
    sub = p.add_subparsers(dest="cmd")
    sub.add_parser("list", help="show corpus counts")
    run_p = sub.add_parser("run", help="run the corpus against an agent")
    run_p.add_argument("--agent", default="refuse", help="refuse|obey|anthropic|openai|minimal|langgraph")
    run_p.add_argument("--model", default=None)
    run_p.add_argument("--category", default=None)
    run_p.add_argument("--out", default="reports")
    run_p.add_argument("--fail-above", type=float, default=None, help="exit 1 if ASR exceeds this")
    run_p.add_argument(
        "--smoke",
        action="store_true",
        help="5 benign + 5 direct_injection; exit 2 if benign never calls a tool",
    )
    run_p.add_argument("--no-resume", action="store_true", help="ignore report.json in --out and start over")
    run_p.add_argument(
        "--sample",
        type=float,
        default=None,
        metavar="FRAC",
        help="stratified fraction of the corpus (e.g. 0.1); not a full run",
    )
    run_p.add_argument("--seed", type=int, default=0, help="RNG seed for --sample")
    run_p.add_argument("--strength", choices=["base", "enhanced"], default="base")
    run_p.add_argument(
        "--convert",
        choices=["none", "markdown", "unicode", "base64"],
        default="none",
        help="obfuscate payloads (markdown comment, zero-width chars, or base64)",
    )
    run_p.add_argument(
        "--defense",
        default="",
        help="sandwich, allowlist, detector (comma-separated)",
    )
    run_p.add_argument(
        "--benign-utility",
        action="store_true",
        help="strip attack payloads; score whether the original task still runs",
    )
    args = p.parse_args(argv)

    if args.cmd in (None, "list"):
        cases = load_cases()
        print(f"{len(cases)} cases")
        for category in sorted({c.category for c in cases}):
            n = sum(1 for c in cases if c.category == category)
            print(f"  {category}: {n}")
        return 0

    if args.smoke and args.category:
        print("--smoke and --category cannot be combined", file=sys.stderr)
        return 1
    if args.smoke and args.sample is not None:
        print("--smoke and --sample cannot be combined", file=sys.stderr)
        return 1

    agent = build_agent(args.agent, args.model)
    out = Path(args.out)
    if args.smoke:
        case_ids = smoke_case_ids()
    elif args.sample is not None:
        try:
            case_ids = sample_case_ids(args.sample, args.seed)
        except ValueError as exc:
            print(exc, file=sys.stderr)
            return 1
        print(f"sample {args.sample:g} seed={args.seed}: {len(case_ids)} cases")
    else:
        case_ids = None
    prev = None if args.no_resume else load_report(out)
    if prev is not None:
        want = case_ids or {c.id for c in load_cases(args.category)}
        n_skip = len(want & {r.id for r in prev.results})
        if n_skip:
            print(f"resume: skipping {n_skip} cases already in {out}/report.json")
    try:
        defenses = parse_defenses(args.defense)
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 1
    try:
        report = run(
            agent,
            category=args.category,
            case_ids=case_ids,
            out=out,
            resume=not args.no_resume,
            strength=args.strength,
            convert=args.convert,
            defense=defenses,
            benign_utility=args.benign_utility,
        )
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 1
    report.write(out)
    data = report.to_json()
    print(
        f"ASR {data['asr']:.1%}  utility {data['utility']:.1%}  over-refusal {data['over_refusal']:.1%}  "
        f"wrote {out}/report.html"
    )
    for label, key in (("delivery", "asr_by_delivery"), ("placement", "asr_by_placement")):
        bucket = data.get(key) or {}
        if bucket:
            bits = ", ".join(f"{k} {v:.0%}" for k, v in bucket.items())
            print(f"  {label}: {bits}")
    if args.smoke and not report.benign_called_tools():
        print(
            "smoke: no tool calls on benign cases — drop this model, do not run the full corpus",
            file=sys.stderr,
        )
        return 2
    if args.fail_above is not None and data["asr"] > args.fail_above:
        print(f"ASR {data['asr']:.1%} exceeds --fail-above {args.fail_above}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
