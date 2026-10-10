# ADR 0001: Custom LLM gateway on free tiers

- Status: Accepted
- Date: 2026-10-10
- Source: ARCHITECTURE.md (Principles, Core: LLM gateway, Deliberate trade-offs)

## Context
DevPilot uses LLMs for Dockerfile generation, pipeline generation, and CI triage. The project must run on free, card-free LLM tiers, whose quotas, model names, and quality vary and change often. The developer machine (8 GB RAM) cannot host a local model.

## Decision
- All LLM calls go through one in-house gateway in `devpilot/core/llm/`. No other code calls a provider SDK or HTTP API.
- Interface: `generate(task, messages, schema) -> Result[T]`. Providers implement `Provider.complete(request) -> ProviderResponse`.
- Provider order is Gemini > Groq > OpenRouter, with order and model names taken from config, never hardcoded.
- Failover on 429, 5xx, timeout, and quota errors, with exponential backoff and jitter.
- Response cache keyed by a hash of (task, prompt version, inputs, model).
- Daily request budget per provider, with a hard stop.
- Responses are requested as JSON and validated with pydantic. One retry with the validation error, then a typed failure. Raw provider errors never reach callers.

## Alternatives
An existing gateway proxy is a fair alternative. It was not chosen because a custom gateway gives exact control over failover, caching, and the daily free-tier budget with a tiny dependency footprint. S1 must record the reason based on actually checking the proxy's footprint.

## Consequences
- Free-tier quotas become degraded service rather than outages, but quotas and quality still vary.
- Data sent to free-tier providers may be used by them, so only public data is processed.
- The gateway is ours to maintain, including adapters when provider APIs change.
