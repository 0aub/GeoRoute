"""
Configuration module with strict environment variable validation.
Settings are centralized in config.yaml - modify there, not in code.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


class ConfigurationError(Exception):
    """Raised when required configuration is missing."""
    pass


# Path to YAML config
_CONFIG_PATH = Path(__file__).parent / "config.yaml"


def _load_yaml_config() -> dict:
    """Load configuration from config.yaml file (fresh read each time)."""
    if _CONFIG_PATH.exists():
        with open(_CONFIG_PATH, "r") as f:
            return yaml.safe_load(f)
    else:
        raise ConfigurationError(f"Configuration file not found: {_CONFIG_PATH}")


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
    # Convert "inf" string to infinity for cost values
    if value == "inf":
        return float('inf')
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


@dataclass(frozen=True)
class Config:
    """Application configuration - immutable after creation."""

    # Server settings
    backend_port: int
    backend_host: str

    # API keys
    google_maps_api_key: str
    gemini_api_key: str  # AI Studio API key (if not using Vertex)
    google_cloud_project: str

    # Vertex AI settings
    use_vertex_ai: bool  # If True, use Vertex AI instead of AI Studio
    vertex_location: str  # Vertex AI region (e.g., us-central1)

    # CORS settings
    cors_origins: list[str]

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        use_vertex = os.environ.get("USE_VERTEX_AI", "").lower() in ("true", "1", "yes")
        return cls(
            backend_port=int(get_required_env("BACKEND_PORT")),
            backend_host=get_required_env("BACKEND_HOST"),
            google_maps_api_key=get_required_env("GOOGLE_MAPS_API_KEY"),
            gemini_api_key=os.environ.get("GEMINI_API_KEY", ""),  # Optional if using Vertex
            google_cloud_project=get_required_env("GOOGLE_CLOUD_PROJECT"),
            use_vertex_ai=use_vertex,
            vertex_location=os.environ.get("VERTEX_LOCATION", "us-central1"),
            cors_origins=[o.strip() for o in get_required_env("CORS_ORIGINS").split(",")],
        )

    def validate_apis(self) -> dict[str, bool]:
        """Return which APIs are configured."""
        return {
            "google_maps": bool(self.google_maps_api_key),
            "gemini": bool(self.gemini_api_key) or self.use_vertex_ai,
        }


def load_config() -> Config:
    """Load and validate configuration."""
    from dotenv import load_dotenv

    # Load .env file if present
    load_dotenv()

    return Config.from_env()
