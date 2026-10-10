# DevPilot: architecture brief (source of truth)

## Purpose
Reduce the time DevOps engineers lose on two chores: writing and fixing container and CI configuration, and diagnosing failed CI runs. DevPilot does both with an LLM, validated by deterministic tools, and measures its own accuracy.

## Principles
1. **Deterministic first, LLM second.** Stack detection, log cleaning, linting, and scanning are rule and tool based. The LLM handles only what rules cannot.
2. **Every LLM output is validated** by a schema and by a real tool (hadolint, Trivy, actionlint, a GitLab CI validator, or a CI build).
3. **Free-tier resilient.** The gateway fails over across providers, caches, and enforces a daily budget so quotas never become outages.
4. **Measured.** Every claim on the CV comes from a reproducible benchmark in `eval/`.
5. **Untrusted input.** Repo files and CI logs are data, never instructions.

## Components

    +-------------------------- FastAPI service ---------------------------+
    |  /dockerize   /pipeline   /triage   /webhook/github   /metrics       |
    +---------+-----------+-----------+------------------+-----------------+
              |           |           |                  |
        +-----v-----+ +---v------+ +--v---------+        |
        | dockerize | | pipeline | |   triage   |<-------+  GitHub webhook
        |  module   | |   gen    | |   module   |           (workflow_run failed)
        +-----+-----+ +----+-----+ +--+------+--+
              |            |          |      |
        +-----v------------v----------v--+ +-v--------------+
        |         LLM gateway            | | Similarity     |
        | Gemini > Groq > OpenRouter     | | (TF-IDF over   |
        | cache, budget, schema retry    | |  error sigs)   |
        +----------------+---------------+ +-------+--------+
                         |                         |
                    +----v-------------------------v----+
                    |  SQLite store (+ seed fixtures)   |
                    +-----------------+-----------------+
                                      |
                       Prometheus metrics --> Grafana (provisioned as code)

## Module contracts

### Core: LLM gateway
`generate(task, messages, schema) -> Result[T]`
- Providers implement `Provider.complete(request) -> ProviderResponse`.
- Order and models from config. Failover on 429, 5xx, timeout, and quota errors.
- Exponential backoff with jitter. Response cache keyed by hash of (task, prompt version, inputs, model). Daily request budget per provider with a hard stop.
- Returns typed failure (never raises raw provider errors to callers).

### Dockerize
Input: public repo URL (and optional pinned commit). Steps:
1. Fetch the file tree and key files over the GitHub API or a shallow archive. Cap size.
2. **Analyzer (deterministic):** detect language, framework, package manager, entrypoint, port, build and runtime versions. Output `RepoAnalysis` JSON.
3. **Generate:** LLM produces `{dockerfile, dockerignore, assumptions[], confidence}`.
4. **Validate (tiers):**
   - Static (runs everywhere, including the Space): hadolint, Trivy config scan, custom rules (non-root user, no `latest` tag, no secrets, healthcheck present).
   - Build (runs where a Docker daemon exists: local optional, GitHub Actions always): `docker build`, short run, Trivy image scan.
5. **Repair loop:** on any failure, send validator output to the LLM for a minimal fix. Max 3 attempts. Record per-attempt outcome.

### Pipeline generator
Same analysis input, plus a `target`: `github` (GitHub Actions) or `gitlab` (GitLab CI). Both targets are first-class because GitLab CI is widely used in the Tunisian market. LLM produces a pipeline file (build, test, scan, package) for the chosen target. Each target has its own prompt, validators, and custom rules behind one `PipelineTarget` interface, so adding a target never touches the repair loop.
- `github`: actionlint plus custom rules (pinned action versions, least-privilege `permissions`, no secrets echoed, job timeouts).
- `gitlab`: a GitLab CI validator (the exact tool is chosen in S9 after checking current options; offline schema validation is preferred so no GitLab account or token is needed) plus custom rules (pinned image tags, `rules:` instead of deprecated `only/except`, job `timeout`, artifact `expire_in`, no secrets echoed, security scan jobs not allowed to fail silently).
- GitLab support is **generation and validation only**. Triage ingestion remains GitHub-only.

### CI triage
Input: GitHub `workflow_run` webhook with `conclusion=failure`.
1. Verify signature. Fetch failed job logs.
2. **Preprocess:** strip ANSI and timestamps, scrub secrets, extract a window around the first error, build a normalized **error signature**.
3. **Rule pre-classifier** for obvious cases (e.g., network timeout, registry rate limit).
4. **Retrieve** top-k similar past failures (TF-IDF cosine over signatures).
5. **LLM classify** into `{flaky, infrastructure, dependency, test_failure, build_config, unknown}` with `{root_cause, evidence_lines[], suggested_fix, confidence}`. Evidence lines must be verbatim from the log; the code checks this and downgrades confidence if not.
6. Store result, expose metrics, optionally comment on the PR (dry-run mode by default).

### Feedback loop
When a failed run belongs to a repo whose Dockerfile or workflow DevPilot generated, triage emits a `repair_request`, which re-enters Dockerize or Pipeline generator with the failure as validator output.

## Data model (SQLite)
- `llm_cache(key PK, task, model, response_json, created_at)`
- `llm_usage(day, provider, requests, tokens_in, tokens_out)`
- `analyses(id, repo, commit, analysis_json, created_at)`
- `dockerize_runs(id, repo, commit, attempt, dockerfile, validator_results_json, outcome, created_at)`
- `pipeline_runs(id, repo, commit, target, attempt, pipeline_text, validator_results_json, outcome, created_at)`
- `failures(id, repo, run_id, job, signature, category, root_cause, fix, confidence, evidence_json, created_at)`
- `labels(failure_id, true_category, labeled_by)`: ground truth for evaluation.

## Deployment
- **Public demo:** Hugging Face Space, Docker SDK. One container runs the API, Prometheus, and Grafana under a process supervisor. Only static validation is available there. Assume **ephemeral disk**: the SQLite file is rebuilt from committed seed fixtures on start. Verify the Space port, user, and README metadata requirements in the current Spaces docs.
- **Build and Kubernetes verification:** GitHub Actions. Workflows: `ci.yml` (lint, test), `eval.yml` (benchmark with a Docker daemon), `e2e-kind.yml` (create a `kind` cluster, **deploy the app with Terraform**, run smoke tests, destroy).
- **Terraform scope:** Terraform is used to *deploy* the app onto the throwaway `kind` cluster in CI, using its Kubernetes or Helm provider (chosen in S10 and recorded in an ADR). It needs **no cloud credentials and no remote state**: state lives on the ephemeral runner and is never committed. Provider versions are pinned and the lock file is committed. `terraform fmt -check`, `terraform validate`, and a Trivy config scan of the Terraform are CI gates. This is a deployment practice, not a Terraform *generator* (see non-goals).
- Webhook target is the Space URL. Cold starts are acceptable and documented.

## Deliberate trade-offs (each deserves an ADR and a README line)
- **SQLite instead of Postgres:** keeps the demo light and the dev machine within limits. The repository layer isolates SQL so a Postgres swap is a contained change. Production systems would use Postgres.
- **TF-IDF retrieval instead of embeddings and a vector database:** no heavy dependencies, and error logs are keyword-heavy. The triage evaluation (S7) is the evidence for whether this is good enough; a hosted-embeddings backend is a possible later comparison.
- **Custom LLM gateway instead of an existing proxy:** gives exact control over failover, caching, and the daily free-tier budget with a tiny dependency footprint. An existing gateway proxy is a fair alternative; S1 should record why it was not chosen, based on actually checking its footprint.
- **Hugging Face Space for the demo:** a free, card-free host, not a production platform. The Kubernetes manifests and the Terraform-on-`kind` e2e test are the production-style deployment evidence.
- **GitHub Actions as the primary CI:** free for public repositories with no card. GitLab CI is supported as a generation target to match the local market.

## Known limitations (to document honestly in the README)
- Free-tier LLM quotas and quality vary; the gateway mitigates but cannot remove this.
- The demo Space cannot build images; build-verified results come from the Actions benchmark.
- Data sent to free-tier LLMs may be used by providers, so only public data is processed.
- Accuracy numbers apply to the evaluation sets, not to all repositories.

## Non-goals (deferred roadmap)
Kubernetes manifest generation, Terraform *generation* (using Terraform to deploy is in scope), GitLab webhook ingestion for triage, cost analysis, multi-tenant auth, private repositories, a web UI beyond Grafana and the API docs.

## Evaluation (summary; full specs in the prompt pack)
- Dockerize: first-try and post-repair build success on a pinned set of public repos.
- Triage: accuracy and macro-F1 on a hand-labeled failure set; compare rules-only vs LLM vs LLM+retrieval.
- Pipeline generator: validation pass rate before and after repair, reported separately for the `github` and `gitlab` targets.
- Gateway: failover and cache hit behavior under simulated 429s.