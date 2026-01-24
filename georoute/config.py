"""
Configuration module with strict environment variable validation.
NO FALLBACKS - all required variables must be explicitly set.

Settings are centralized in config.yaml - modify there, not in code.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Any

import yaml
import numpy as np


class ConfigurationError(Exception):
    """Raised when required configuration is missing."""
    pass


# Load YAML config once at module level
_CONFIG_PATH = Path(__file__).parent / "config.yaml"
_YAML_CONFIG: dict = {}


def _load_yaml_config() -> dict:
    """Load configuration from config.yaml file."""
    global _YAML_CONFIG
    if not _YAML_CONFIG:
        if _CONFIG_PATH.exists():
            with open(_CONFIG_PATH, "r") as f:
                _YAML_CONFIG = yaml.safe_load(f)
        else:
            raise ConfigurationError(f"Configuration file not found: {_CONFIG_PATH}")
    return _YAML_CONFIG


def get_yaml_setting(*keys: str, default: Any = None) -> Any:
    """
    Get a setting from config.yaml using dot notation.

    Example: get_yaml_setting("gemini", "complex_model") -> "gemini-2.5-flash"
    """
    config = _load_yaml_config()
    value = config
    for key in keys:
        if isinstance(value, dict) and key in value:
            value = value[key]
        else:
            return default
    # Convert "inf" string to np.inf for cost values
    if value == "inf":
        return np.inf
    return value


def get_required_env(key: str) -> str:
    """Get a required environment variable. Raises if not set."""
    value = os.environ.get(key)
    if value is None or value.strip() == "":
        raise ConfigurationError(
            f"Missing required environment variable: {key}\n"
            f"Please set {key} in your .env file or environment."
        )
    return value.strip()


def get_optional_env(key: str) -> Optional[str]:
    """Get an optional environment variable. Returns None if not set."""
    value = os.environ.get(key)
    if value is None or value.strip() == "":
        return None
    return value.strip()


@dataclass(frozen=True)
class Config:
    """Application configuration - immutable after creation."""

    # Server settings - REQUIRED
    backend_port: int
    backend_host: str

    # Required API keys
    google_maps_api_key: str
    gemini_api_key: str
    google_cloud_project: str

    # Optional API keys (graceful degradation if missing)
    ors_api_key: Optional[str]
    opentopography_api_key: Optional[str]

    # CORS settings - REQUIRED
    cors_origins: list[str]

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""

        # Required settings
        backend_port = int(get_required_env("BACKEND_PORT"))
        backend_host = get_required_env("BACKEND_HOST")

        google_maps_api_key = get_required_env("GOOGLE_MAPS_API_KEY")
        gemini_api_key = get_required_env("GEMINI_API_KEY")
        google_cloud_project = get_required_env("GOOGLE_CLOUD_PROJECT")

        cors_origins_str = get_required_env("CORS_ORIGINS")
        cors_origins = [origin.strip() for origin in cors_origins_str.split(",")]

        # Optional settings
        ors_api_key = get_optional_env("ORS_API_KEY")
        opentopography_api_key = get_optional_env("OPENTOPOGRAPHY_API_KEY")

        return cls(
            backend_port=backend_port,
            backend_host=backend_host,
            google_maps_api_key=google_maps_api_key,
            gemini_api_key=gemini_api_key,
            google_cloud_project=google_cloud_project,
            ors_api_key=ors_api_key,
            opentopography_api_key=opentopography_api_key,
            cors_origins=cors_origins,
        )

    def validate_apis(self) -> dict[str, bool]:
        """Return which APIs are configured."""
        return {
            "google_maps": bool(self.google_maps_api_key),
            "gemini": bool(self.gemini_api_key),
            "osrm": True,  # Always available, no key needed
            "ors": bool(self.ors_api_key),
            "opentopography": bool(self.opentopography_api_key),
        }


def load_config() -> Config:
    """Load and validate configuration."""
    from dotenv import load_dotenv

    # Load .env file if present
    load_dotenv()

    return Config.from_env()
