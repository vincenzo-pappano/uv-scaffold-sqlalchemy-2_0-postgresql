import yaml
import os


# class Config:
#     """
#     A class responsible for loading configuration from a YAML file.
#     """
#     def __init__(self, file_path):
#         self.file_path = file_path
#         self.config = self._load_config()

#     def _load_config(self):
#         if not os.path.exists(self.file_path):
#             raise FileNotFoundError(f"Configuration file not found: {self.file_path}")
#         with open(self.file_path, 'r') as file:
#             return yaml.safe_load(file)

#     def get(self, key, default=None):
#         return self.config.get(key, default)

#     '''
#     def set(self, key, value):
#         keys = key.split('.')
#         data = self.config
#         for k in keys[:-1]:
#             data = data[k]
#             data[keys[-1]] = value
#         with open(self.config_path, 'w+') as f:
#             yaml.safe_dump(self.config, f, default_flow_style=False)
#     '''

import yaml
from typing import Dict, Any, Optional

from utils.logger import logger_base
logger = logger_base.get_logger(__name__)

class Settings:
    _instance = None
    _config_data: Optional[Dict[str, Any]] = None

    def __new__(cls, *args, **kwargs):
        raise RuntimeError("Use get_instance() to access Settings")

    @classmethod
    def get_instance(cls, config_path: Optional[str] = None) -> Dict[str, Any]:
        if cls._instance is None:
            if config_path is None:
                raise ValueError("First call to ConfigLoader requires a config_path")

            try:
                with open(config_path, 'r') as f:
                    cls._config_data = yaml.safe_load(f)
                    cls._instance = object()  # mark initialized
                    logger.info(f"Config loaded from {config_path}")
            except Exception as e:
                logger.error(f"Failed to load config: {e}")
                raise
        return cls._config_data


settings_instance = Settings.get_instance('config/settings.yaml')