"""Configuration system with multi-profile support for Nautobot connections.

Supports loading from environment variables, YAML config files, and CLI arguments.
Env vars override config file values. Multi-server profiles allow switching between
production, staging, and other environments.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class NautobotProfile(BaseModel):
    """Connection profile for a Nautobot server instance."""

    url: str = Field(description="Nautobot server URL")
    token: str = Field(description="API authentication token")
    verify_ssl: bool = Field(default=True, description="Enable SSL certificate verification")
    api_version: Optional[str] = Field(
        default=None,
        description="API version to use. Auto-detected from server if None.",
    )


class NautobotSettings(BaseSettings):
    """Application settings with multi-profile support.

    Configuration precedence (highest to lowest):
    1. Environment variables (NAUTOBOT_URL, NAUTOBOT_TOKEN, etc.)
    2. Config file (.nautobot-mcp.yaml or ~/.config/nautobot-mcp/config.yaml)
    3. Default values
    """

    profiles: dict[str, NautobotProfile] = Field(
        default_factory=dict,
        description="Named connection profiles (e.g., production, staging)",
    )
    active_profile: str = Field(
        default="default",
        description="Currently active profile name",
    )
    default_limit: int = Field(
        default=50,
        description="Default result limit for MCP layer queries",
    )

    model_config = {
        "env_prefix": "",
        "extra": "ignore",
    }

    def model_post_init(self, __context: object) -> None:
        """After initialization, merge env vars into profiles."""
        env_url = os.environ.get("NAUTOBOT_URL")
        env_token = os.environ.get("NAUTOBOT_TOKEN")
        env_profile = os.environ.get("NAUTOBOT_PROFILE")
        env_verify = os.environ.get("NAUTOBOT_VERIFY_SSL")

        if env_profile:
            self.active_profile = env_profile

        if env_url and env_token:
            verify_ssl = True
            if env_verify is not None:
                verify_ssl = env_verify.lower() in ("true", "1", "yes")

            self.profiles[self.active_profile] = NautobotProfile(
                url=env_url,
                token=env_token,
                verify_ssl=verify_ssl,
            )

    def get_active_profile(self) -> NautobotProfile:
        """Return the currently active connection profile.

        Raises:
            ValueError: If the active profile doesn't exist.
        """
        if self.active_profile not in self.profiles:
            available = list(self.profiles.keys())
            raise ValueError(
                f"Profile '{self.active_profile}' not found. "
                f"Available profiles: {available}"
            )
        return self.profiles[self.active_profile]

    @classmethod
    def load_from_yaml(cls, path: str | Path) -> NautobotSettings:
        """Load settings from a YAML configuration file.

        Expected format:
            profiles:
              default:
                url: "https://nautobot.netnam.vn"
                token: "your-token"
                verify_ssl: true
              staging:
                url: "https://staging.nautobot.netnam.vn"
                token: "staging-token"
            active_profile: default

        Args:
            path: Path to the YAML config file.

        Returns:
            NautobotSettings instance with loaded profiles.

        Raises:
            FileNotFoundError: If config file doesn't exist.
        """
        config_path = Path(path)
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(config_path) as f:
            data = yaml.safe_load(f) or {}

        profiles = {}
        for name, profile_data in data.get("profiles", {}).items():
            profiles[name] = NautobotProfile(**profile_data)

        return cls(
            profiles=profiles,
            active_profile=data.get("active_profile", "default"),
            default_limit=data.get("default_limit", 50),
        )

    @classmethod
    def discover(cls) -> NautobotSettings:
        """Discover and load settings from standard locations.

        Search order:
        1. NAUTOBOT_CONFIG_FILE env var (explicit absolute path)
        2. .nautobot-mcp.yaml in current directory
        3. ~/.config/nautobot-mcp/config.yaml
        4. Environment variables only (empty profiles)

        Returns:
            NautobotSettings from first found config or env vars.
        """
        # Explicit config file wins over all discovery
        env_config = os.environ.get("NAUTOBOT_CONFIG_FILE")
        if env_config:
            return cls.load_from_yaml(env_config)

        search_paths = [
            Path(".nautobot-mcp.yaml"),
            Path.home() / ".config" / "nautobot-mcp" / "config.yaml",
        ]

        for config_path in search_paths:
            if config_path.exists():
                return cls.load_from_yaml(config_path)

        return cls()
