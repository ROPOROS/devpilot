# DevPilot

AI-assisted DevOps platform: Dockerfile generation, CI pipeline generation (GitHub Actions and GitLab CI), and CI failure triage on a shared core.

Status: bootstrap (S0). See [ARCHITECTURE.md](ARCHITECTURE.md) and [docs/adr/](docs/adr/).

## Development

Requires Python 3.12 and [uv](https://docs.astral.sh/uv/).

    uv sync
    make check   # ruff + tests
    make run     # API on http://127.0.0.1:8000 (/health, /metrics, /docs)

Configuration is read from environment variables; see `.env.example`.
