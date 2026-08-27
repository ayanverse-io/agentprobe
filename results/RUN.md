# Frozen eval — 395-case corpus (`hardened-395-2026-08-26`)

Do not change the corpus, `DEFAULT_SYSTEM`, tool list, or judge and then quote these numbers.
Canonical per-case JSON (gitignored, keep on disk): `reports/hardened-395-*/report.json`.
Machine-readable summaries: [`hardened-395-metrics.json`](hardened-395-metrics.json), [`naive-metrics.json`](naive-metrics.json), [`defense-metrics.json`](defense-metrics.json), [`convert-metrics.json`](convert-metrics.json).

An earlier freeze, [`full-metrics.json`](full-metrics.json) (`full-2026-08-24`, 343 cases), scored only the 293 loud attacks plus 50 benign. Its 0% Haiku/Terra rows are loud-only. Do not mix them with the table below.

## Setup

| Item | Value |
|---|---|
| Cases | 395 (293 loud + 52 quiet + 50 benign) |
| Adapter | `openai` via OpenRouter (`https://openrouter.ai/api/v1`) |
| Thinking | off (`extra_body.reasoning.enabled=false` when the API accepts it) |
| Temperature | 0 (omitted if the model 400s) |
| System prompt | `DEFAULT_SYSTEM` in `src/agentprobe/protocol.py` |
| Gemini | dropped (OpenRouter 400s) |
| Ablations | `--system naive`; `--defense sandwich\|allowlist\|detector`; `--convert markdown\|unicode\|base64` (Haiku + DeepSeek) |

## Results (hardened prompt)

| Model | OpenRouter id | ASR | Loud | Quiet | Utility | Over-refusal |
|---|---|---:|---:|---:|---:|---:|
| Haiku 4.5 | `anthropic/claude-haiku-4.5` | 2.3% [1.2–4.5] | 0.0% | 15.4% | 84.7% | 0.0% |
| GPT-5.6 Terra | `openai/gpt-5.6-terra` | 2.3% [1.2–4.5] | 0.0% | 15.4% | 87.2% | 0.0% |
| Llama 4 Maverick | `meta-llama/llama-4-maverick` | 10.4% [7.6–14.1] | 2.0% | 57.7% | 16.5% | 22.0% |
| DeepSeek V4 Flash | `deepseek/deepseek-v4-flash` | 31.3% [26.6–36.4] | 20.8% | 90.4% | 93.4% | 0.0% |

ASR over 345 attacks (293 loud + 52 quiet). Utility over 242 scored attacks. Over-refusal over 50 benign. Intervals are Wilson 95%. Haiku and Terra quiet hits are `qtm-001`–`qtm-008`.

DeepSeek by category (ASR): direct 64.3%, hijack 53.6%, exfil 42.3%, prompt-extraction 39.3%, tool-misuse 23.5%, indirect 3.4%.

## How to quote

These numbers measure loud lexical injection **and** quiet original cases under a hardened system prompt. 0% loud is not “prompt injection is solved.” Allowlist collapsed DeepSeek to 0.3% ASR; sandwich raised it to 36.5%. HTML-comment / ZWSP / Base64 wraps of the same payloads did not raise ASR.

## Reproduce

```bash
agentprobe run --agent openai --model anthropic/claude-haiku-4.5 --out reports/hardened-395-claude-haiku-4.5
```

Same for the other three ids. Resume skips ids already in `report.json`. Ablations: `--system naive`, `--defense allowlist`, `--convert base64`.

## Key

Rotate the OpenRouter key used for this run. It was in local shells; do not commit it.
