# DevPilot

AI-assisted DevOps platform: Dockerfile generation, CI pipeline generation (GitHub Actions and GitLab CI), and CI failure triage on a shared core.

Status: bootstrap (S0). See [ARCHITECTURE.md](ARCHITECTURE.md) and [docs/adr/](docs/adr/).

## Development

Requires Python 3.12 and [uv](https://docs.astral.sh/uv/).

    uv sync
    make check   # ruff + tests
    make run     # API on http://127.0.0.1:8000 (/health, /metrics, /docs)

Configuration is read from environment variables; see `.env.example`.

## Known issues

- Tests emit `StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated; install httpx2 instead.` Since Starlette 1.2.0, `TestClient` is built on `httpx2`, and plain `httpx` is still supported but deprecated ([Starlette test client docs](https://github.com/Kludex/starlette/blob/main/docs/testclient.md), [release notes](https://github.com/Kludex/starlette/blob/main/docs/release-notes.md)). Tests are unaffected for now.
