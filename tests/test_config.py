"""Tests for the configuration system."""

import os

from nautobot_mcp.config import NautobotProfile, NautobotSettings


def test_profile_creation():
    """NautobotProfile should be created with url, token, and verify_ssl."""
    profile = NautobotProfile(
        url="https://nautobot.example.com",
        token="my-api-token",
        verify_ssl=True,
    )
    assert profile.url == "https://nautobot.example.com"
    assert profile.token == "my-api-token"
    assert profile.verify_ssl is True


def test_profile_verify_ssl_default_true():
    """SSL verification should be True by default."""
    profile = NautobotProfile(
        url="https://nautobot.example.com",
        token="my-api-token",
    )
    assert profile.verify_ssl is True


def test_settings_default_profile():
    """Default active profile should be 'default'."""
    settings = NautobotSettings(
        profiles={
            "default": NautobotProfile(
                url="https://nautobot.example.com",
                token="token",
            ),
        },
    )
    assert settings.active_profile == "default"


def test_settings_get_active_profile(monkeypatch):
    """get_active_profile should return the correct profile."""
    monkeypatch.delenv("NAUTOBOT_URL", raising=False)
    monkeypatch.delenv("NAUTOBOT_TOKEN", raising=False)
    profile = NautobotProfile(
        url="https://nautobot.example.com",
        token="my-token",
    )
    settings = NautobotSettings(
        profiles={"default": profile},
        active_profile="default",
    )
    active = settings.get_active_profile()
    assert active.url == "https://nautobot.example.com"
    assert active.token == "my-token"


def test_settings_get_active_profile_not_found(monkeypatch):
    """get_active_profile should raise ValueError if profile doesn't exist."""
    monkeypatch.delenv("NAUTOBOT_URL", raising=False)
    monkeypatch.delenv("NAUTOBOT_TOKEN", raising=False)
    settings = NautobotSettings(
        profiles={},
        active_profile="nonexistent",
    )
    try:
        settings.get_active_profile()
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "nonexistent" in str(e)


def test_settings_multiple_profiles(monkeypatch):
    """Settings should support multiple named profiles."""
    monkeypatch.delenv("NAUTOBOT_URL", raising=False)
    monkeypatch.delenv("NAUTOBOT_TOKEN", raising=False)
    settings = NautobotSettings(
        profiles={
            "production": NautobotProfile(
                url="https://nautobot.prod.example.com",
                token="prod-token",
            ),
            "staging": NautobotProfile(
                url="https://nautobot.staging.example.com",
                token="staging-token",
                verify_ssl=False,
            ),
        },
        active_profile="production",
    )
    assert len(settings.profiles) == 2
    prod = settings.profiles["production"]
    staging = settings.profiles["staging"]
    assert prod.url == "https://nautobot.prod.example.com"
    assert staging.verify_ssl is False


def test_settings_env_override(monkeypatch):
    """Environment variables should override config settings."""
    monkeypatch.setenv("NAUTOBOT_URL", "https://env.nautobot.example.com")
    monkeypatch.setenv("NAUTOBOT_TOKEN", "env-token")

    settings = NautobotSettings()
    profile = settings.get_active_profile()
    assert profile.url == "https://env.nautobot.example.com"
    assert profile.token == "env-token"


def test_settings_env_profile_override(monkeypatch):
    """NAUTOBOT_PROFILE env var should switch the active profile."""
    monkeypatch.setenv("NAUTOBOT_URL", "https://staging.example.com")
    monkeypatch.setenv("NAUTOBOT_TOKEN", "staging-token")
    monkeypatch.setenv("NAUTOBOT_PROFILE", "staging")

    settings = NautobotSettings()
    assert settings.active_profile == "staging"
    profile = settings.get_active_profile()
    assert profile.url == "https://staging.example.com"


def test_settings_env_verify_ssl_false(monkeypatch):
    """NAUTOBOT_VERIFY_SSL=false should disable SSL verification."""
    monkeypatch.setenv("NAUTOBOT_URL", "https://nautobot.example.com")
    monkeypatch.setenv("NAUTOBOT_TOKEN", "token")
    monkeypatch.setenv("NAUTOBOT_VERIFY_SSL", "false")

    settings = NautobotSettings()
    profile = settings.get_active_profile()
    assert profile.verify_ssl is False
