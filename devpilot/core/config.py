"""Application settings, read from environment variables."""

import os
from collections.abc import Mapping
from typing import Literal

from pydantic import BaseModel, Field


class Settings(BaseModel):
    env: Literal["dev", "test", "prod"] = "dev"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    host: str = "127.0.0.1"
    port: int = Field(default=8000, ge=1, le=65535)


_ENV_VARS = {
    "env": "DEVPILOT_ENV",
    "log_level": "DEVPILOT_LOG_LEVEL",
    "host": "DEVPILOT_HOST",
    "port": "DEVPILOT_PORT",
}


def load_settings(environ: Mapping[str, str] | None = None) -> Settings:
    """Build Settings from environment variables; unset or empty variables keep their defaults."""
    source = os.environ if environ is None else environ
    values = {field: source[var] for field, var in _ENV_VARS.items() if source.get(var)}
    return Settings.model_validate(values)
