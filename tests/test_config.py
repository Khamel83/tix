import pytest
from pydantic import ValidationError

from ticket_sniper.config import Settings


def test_scrapling_defaults_keep_argus_and_browser_disabled():
    config = Settings(_env_file=None)

    assert config.SCRAPLING_ENABLED is False
    assert config.SCRAPLING_SOURCE == "argus"
    assert config.SCRAPLING_HEADLESS is True
    assert config.SCRAPLING_TIMEOUT_SECONDS == 30
    assert config.SCRAPLING_RATE_LIMIT_PER_MINUTE == 30
    assert config.SCRAPLING_REQUEST_DELAY_SECONDS == 1.0
    assert config.SCRAPLING_SESSION_LIFETIME_SECONDS == 900


def test_scrapling_environment_overrides_are_parsed(monkeypatch):
    values = {
        "SCRAPLING_ENABLED": "1",
        "SCRAPLING_SOURCE": "scrapling",
        "SCRAPLING_HEADLESS": "0",
        "SCRAPLING_TIMEOUT_SECONDS": "120",
        "SCRAPLING_RATE_LIMIT_PER_MINUTE": "60",
        "SCRAPLING_REQUEST_DELAY_SECONDS": "2.5",
        "SCRAPLING_SESSION_LIFETIME_SECONDS": "1800",
    }
    for name, value in values.items():
        monkeypatch.setenv(name, value)

    config = Settings(_env_file=None)

    assert config.SCRAPLING_ENABLED is True
    assert config.SCRAPLING_SOURCE == "scrapling"
    assert config.SCRAPLING_HEADLESS is False
    assert config.SCRAPLING_TIMEOUT_SECONDS == 120
    assert config.SCRAPLING_RATE_LIMIT_PER_MINUTE == 60
    assert config.SCRAPLING_REQUEST_DELAY_SECONDS == 2.5
    assert config.SCRAPLING_SESSION_LIFETIME_SECONDS == 1800


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("SCRAPLING_ENABLED", "2"),
        ("SCRAPLING_SOURCE", "browser"),
        ("SCRAPLING_HEADLESS", "2"),
        ("SCRAPLING_TIMEOUT_SECONDS", "0"),
        ("SCRAPLING_TIMEOUT_SECONDS", "301"),
        ("SCRAPLING_RATE_LIMIT_PER_MINUTE", "0"),
        ("SCRAPLING_RATE_LIMIT_PER_MINUTE", "601"),
        ("SCRAPLING_REQUEST_DELAY_SECONDS", "-1"),
        ("SCRAPLING_REQUEST_DELAY_SECONDS", "3601"),
        ("SCRAPLING_SESSION_LIFETIME_SECONDS", "0"),
        ("SCRAPLING_SESSION_LIFETIME_SECONDS", "86401"),
    ],
)
def test_invalid_scrapling_values_raise_actionable_validation_error(name, value, monkeypatch):
    monkeypatch.setenv(name, value)

    with pytest.raises(ValidationError, match=name):
        Settings(_env_file=None)
