# Launch copy

Post after v0.3 is tagged. Do not attach API keys. A demo video is optional later — not required to ship.

Repo: https://github.com/ayanverse-io/agentprobe. The table is the `hardened-395-2026-08-26` freeze.

## LinkedIn

I red-teamed four tool-using LLM agents with a pytest-style harness. Success is not a scary-looking reply — it is a forbidden sandbox tool firing, or a canary leaking in the tool arguments.

395 cases (293 loud + 52 quiet original + 50 benign). OpenRouter, thinking off.

- Claude Haiku 4.5 — ASR 2.3% (0% loud, 15.4% quiet), utility 84.7%
- GPT-5.6 Terra — ASR 2.3% (0% loud, 15.4% quiet), utility 87.2%
- Llama 4 Maverick — ASR 10.4%, utility 16.5%, over-refusal 22%
- DeepSeek V4 Flash — ASR 31.3% (21% loud, 90% quiet), utility 93.4%

0% on loud payloads (`attacker@evil.test`) is not robustness. Haiku and Terra still delete a file and mail `ops@…` when the request reads like ops. A tool allowlist dropped DeepSeek to 0.3% ASR; a sandwich reminder made it worse.

AgentProbe is a drop-in adapter (`run(user_message, tools, execute)`), a YAML corpus, and a GitHub Action that fails CI above an ASR threshold. Point it at your company agent with mock tools — never production.

Repo: https://github.com/ayanverse-io/agentprobe

## X / Twitter

I scored four tool-using agents on prompt injection. Metric = forbidden tool fired, not chat matching.

Haiku / Terra: 0% loud, 15% quiet (same 8 ops-like cases)
Llama: 10% ASR but utility 16% (it mostly refuses)
DeepSeek: 31% ASR, 90% on quiet requests, still 93% useful

Allowlist → 0.3%. Sandwich made DeepSeek worse. Encoding did not help the attacker.

https://github.com/ayanverse-io/agentprobe

## Optional later

- 3-min demo video
- PyPI (`pip install agentprobe`)
- GitHub Marketplace listing for the composite action
- Rotate the OpenRouter key used for the freeze
