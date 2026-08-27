#!/usr/bin/env bash
# Phase 2–3 experiment runner. Requires OPENAI_API_KEY (OpenRouter sk-or-…).
# Usage: ./scripts/run_v2_experiments.sh phase2|phase3-smoke|phase3
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi
APY="${APY:-.venv/bin/agentprobe}"
if [[ -z "${OPENAI_API_KEY:-}${OPENROUTER_API_KEY:-}" ]]; then
  echo "set OPENAI_API_KEY (or OPENROUTER_API_KEY) first" >&2
  exit 1
fi

MODELS=(
  anthropic/claude-haiku-4.5
  openai/gpt-5.6-terra
  meta-llama/llama-4-maverick
  deepseek/deepseek-v4-flash
)
slug() { echo "$1" | tr '/.' '--'; }

smoke_one() {
  local model="$1" extra="${2:-}"
  echo "SMOKE $model $extra"
  $APY run --agent openai --model "$model" --smoke --out "reports/smoke-$(slug "$model")" $extra
}

phase2() {
  smoke_one "anthropic/claude-haiku-4.5" "--system naive"
  for m in "${MODELS[@]}"; do
    echo "NAIVE $m"
    $APY run --agent openai --model "$m" --system naive --out "reports/naive-$(slug "$m")"
  done
}

phase3() {
  local ds=deepseek/deepseek-v4-flash
  local hk=anthropic/claude-haiku-4.5
  for d in sandwich allowlist detector; do
    echo "DEFENSE $ds $d"
    $APY run --agent openai --model "$ds" --defense "$d" --out "reports/def-$(slug "$ds")-$d"
  done
  $APY run --agent openai --model "$ds" --defense sandwich,allowlist --out "reports/def-$(slug "$ds")-sandwich-allowlist"
  for d in sandwich allowlist; do
    echo "DEFENSE $hk $d"
    $APY run --agent openai --model "$hk" --defense "$d" --out "reports/def-$(slug "$hk")-$d"
  done
}

cmd="${1:-}"
case "$cmd" in
  phase2) phase2 ;;
  phase3) phase3 ;;
  *) echo "usage: $0 phase2|phase3" >&2; exit 2 ;;
esac
