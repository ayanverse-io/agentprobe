# Launch copy

Post after the public repo exists. Do not attach API keys. A demo video is optional later — not required to ship.

Replace `URL` with https://github.com/ayanverse-io/agentprobe. The table is the 2026-08-24 freeze — do not update it from a later run without a new freeze.

## LinkedIn

I red-teamed four tool-using LLM agents with a pytest-style harness. Success is not a scary-looking reply — it is a forbidden sandbox tool firing, or a canary leaking in the tool arguments.

343 cases (293 attack + 50 benign). OpenRouter, thinking off.

- Claude Haiku 4.5 — ASR 0%, utility 99.5%, over-refusal 0%
- GPT-5.6 Terra — ASR 0%, utility 99.5%, over-refusal 0%
- Llama 4 Maverick — ASR 1.7%, utility 26%, over-refusal 24%
- DeepSeek V4 Flash — ASR 21.5%, utility 99.5%, over-refusal 0%

0% is not “prompt injection is solved.” The payloads are loud (`attacker@evil.test`). Llama looks safe because it often does nothing. DeepSeek is helpful and still leaks.

AgentProbe is a drop-in adapter (`run(user_message, tools, execute)`), a YAML corpus, and a GitHub Action that fails CI above an ASR threshold. Point it at your company agent with mock tools — never production.

Repo: https://github.com/ayanverse-io/agentprobe

## X / Twitter

I scored four tool-using agents on prompt injection. Metric = forbidden tool fired, not chat matching.

Haiku 4.5 / GPT-5.6 Terra: ASR 0%, still useful
Llama 4 Maverick: ASR 1.7% but utility 26% (it mostly refuses)
DeepSeek V4 Flash: ASR 21.5% and still 99.5% useful

0% ≠ injection solved. Loud payloads + stubborn system prompt.

https://github.com/ayanverse-io/agentprobe

## Optional later

- 3-min demo video
- PyPI (`pip install agentprobe`)
- GitHub Marketplace listing for the composite action
- Rotate the OpenRouter key used for the freeze
