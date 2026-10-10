DEVPILOT_HOST ?= 127.0.0.1
DEVPILOT_PORT ?= 8000

.PHONY: check test run

check:
	uv run ruff check .
	uv run ruff format --check .
	$(MAKE) test

test:
	uv run pytest

run:
	uv run uvicorn devpilot.api.app:app --host $(DEVPILOT_HOST) --port $(DEVPILOT_PORT)
