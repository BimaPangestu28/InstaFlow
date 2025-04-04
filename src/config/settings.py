"""
Configuration management module for InstaFlow.

This module handles loading configuration from multiple sources in this order:
1. Default configuration file
2. User specified configuration file
3. Environment variables (which override file settings)
"""

import json
import os
import logging
from typing import Any, Dict, Optional

# Setup logging
logger = logging.getLogger(__name__)

class Settings:
    """
    Configuration management class for InstaFlow.
    
    Handles loading settings from config files and environment variables.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the Settings object.
        
        Args:
            config_path: Optional path to a custom config file
        """
        self.config: Dict[str, Any] = {}
        
        # Load default config
        default_config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'config',
            'default.json'
        )
        self._load_config_file(default_config_path)
        
        # Load user config if provided
        if config_path and os.path.exists(config_path):
            self._load_config_file(config_path)
        
        # Override with environment variables
        self._load_from_env()
    
    def _load_config_file(self, config_path: str) -> None:
        """
        Load configuration from a JSON file.
        
        Args:
            config_path: Path to the configuration file
        """
        try:
            with open(config_path, 'r') as f:
                file_config = json.load(f)
                self._merge_configs(self.config, file_config)
                logger.debug(f"Loaded configuration from {config_path}")
        except Exception as e:
            logger.error(f"Error loading config from {config_path}: {e}")
    
    def _merge_configs(self, target: Dict[str, Any], source: Dict[str, Any]) -> None:
        """
        Recursively merge source dictionary into target dictionary.
        
        Args:
            target: Target dictionary to merge into
            source: Source dictionary to merge from
        """
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._merge_configs(target[key], value)
            else:
                target[key] = value
    
    def _load_from_env(self) -> None:
        """
        Override configuration with environment variables.
        
        Environment variables in the format CONFIG_SECTION_KEY will override
        config[section][key] in the configuration.
        """
        # Handle specific environment variable mappings
        mappings = {
            "INSTAGRAM_USERNAME": ["bot", "username"],
            "INSTAGRAM_PASSWORD": ["bot", "password"],
            "CONFIG_HEADLESS": ["webdriver", "headless"],
            "CONFIG_LOG_LEVEL": ["logs", "level"]
        }
        
        for env_var, path in mappings.items():
            if env_var in os.environ:
                self._set_nested_value(self.config, path, self._convert_env_value(os.environ[env_var]))
        
        # Process any CONFIG_ prefixed environment variables
        for env_var, value in os.environ.items():
            if env_var.startswith("CONFIG_"):
                # Skip the ones we already processed
                if env_var in mappings:
                    continue
                    
                # Convert CONFIG_SECTION_KEY to ["section", "key"]
                path = env_var[7:].lower().split('_')
                if len(path) >= 2:
                    self._set_nested_value(self.config, path, self._convert_env_value(value))
    
    def _set_nested_value(self, config: Dict[str, Any], path: list, value: Any) -> None:
        """
        Set a value in a nested dictionary based on a path.
        
        Args:
            config: The configuration dictionary
            path: List representing the path to set
            value: The value to set
        """
        current = config
        for i, key in enumerate(path):
            if i == len(path) - 1:
                current[key] = value
            else:
                if key not in current:
                    current[key] = {}
                current = current[key]
    
    def _convert_env_value(self, value: str) -> Any:
        """
        Convert string environment variable to appropriate Python type.
        
        Args:
            value: String value from environment variable
            
        Returns:
            Converted value as appropriate type
        """
        # Convert true/false to boolean
        if value.lower() == 'true':
            return True
        if value.lower() == 'false':
            return False
        
        # Convert numeric values
        try:
            # Check if it's an integer
            return int(value)
        except ValueError:
            try:
                # Check if it's a float
                return float(value)
            except ValueError:
                # Otherwise, keep as string
                return value
    
    def get(self, *keys: str, default: Any = None) -> Any:
        """
        Get a configuration value by key path.
        
        Args:
            *keys: Key path segments to the desired config value
            default: Default value to return if path doesn't exist
            
        Returns:
            The configuration value or default if not found
        """
        current = self.config
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        return current

# Create a singleton instance
settings = Settings()

def initialize_settings(config_path: Optional[str] = None) -> Settings:
    """
    Initialize settings with optional custom config path.
    
    Args:
        config_path: Optional custom configuration file path
        
    Returns:
        Initialized Settings instance
    """
    global settings
    settings = Settings(config_path)
    return settings