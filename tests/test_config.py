import pytest
from pydantic import ValidationError

from devpilot.core.config import load_settings


def test_defaults_when_unset_or_empty():
    settings = load_settings({"DEVPILOT_PORT": ""})
    assert settings.host == "127.0.0.1"
    assert settings.port == 8000


def test_reads_environment():
    settings = load_settings({"DEVPILOT_HOST": "0.0.0.0", "DEVPILOT_PORT": "7860"})  # noqa: S104
    assert settings.host == "0.0.0.0"  # noqa: S104
    assert settings.port == 7860


def test_rejects_invalid_port():
    with pytest.raises(ValidationError):
        load_settings({"DEVPILOT_PORT": "70000"})
