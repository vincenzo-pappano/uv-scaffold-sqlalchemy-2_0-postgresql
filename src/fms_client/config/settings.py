# fms_client/config/settings.py
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from fms_client.utils.logger import logger_base

logger = logger_base.get_logger(__name__)


class Settings:
    _instance: object | None = None
    _config_data: Dict[str, Any] | None = None

    def __new__(cls, *args, **kwargs):
        raise RuntimeError("Use get_instance() to access Settings")

    @classmethod
    def _default_config_path(cls) -> Path:
        return Path(__file__).resolve().parent / "settings.yaml"

    @classmethod
    def get_instance(cls, config_path: Optional[str | Path] = None) -> Dict[str, Any]:
        """
        Load settings from a YAML file. If no path is given on first call,
        use the package-relative settings.yaml next to this module.
        """
        if cls._instance is None:
            cfg_path = Path(config_path) if config_path else cls._default_config_path()
            try:
                with cfg_path.open("r", encoding="utf-8") as f:
                    cls._config_data = yaml.safe_load(f) or {}
                cls._instance = object()
                logger.info(f"Config loaded from {cfg_path}")
            except FileNotFoundError:
                logger.error(f"Config file not found: {cfg_path}")
                raise
            except Exception as e:
                logger.error(f"Failed to load config from {cfg_path}: {e}")
                raise

        # At this point, _config_data must be populated
        return cls._config_data or {}

    @classmethod
    def reload(cls, config_path: Optional[str | Path] = None) -> Dict[str, Any]:
        """Force reload of settings (useful for tests)."""
        cls._instance = None
        cls._config_data = None
        return cls.get_instance(config_path)


# Default instance using package-relative path
settings_instance = Settings.get_instance()
