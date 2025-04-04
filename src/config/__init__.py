"""
Configuration module for InstaFlow.

This module initializes the configuration and logging systems.
"""

import os
import logging
import logging.handlers
from pathlib import Path
from typing import Optional

from .settings import initialize_settings, settings

def setup_logging(config_path: Optional[str] = None) -> None:
    """
    Configure the logging system according to the current settings.
    
    Args:
        config_path: Optional path to a custom config file
    """
    # Initialize settings if needed
    if config_path:
        initialize_settings(config_path)
    
    # Get logging configuration from settings
    log_path = settings.get('logs', 'file_path', default='instaflow.log')
    log_level_str = settings.get('logs', 'level', default='INFO')
    log_format_str = settings.get('logs', 'format', 
                                 default='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Convert log level string to constant
    log_level = getattr(logging, log_level_str.upper(), logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter(log_format_str)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Clear existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level)
    root_logger.addHandler(console_handler)
    
    # Create file handler
    # Make sure the log directory exists
    log_dir = os.path.dirname(log_path)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
        
    # Get rotation settings
    rotation_when = settings.get('logs', 'rotation', 'when', default='midnight')
    backup_count = settings.get('logs', 'rotation', 'backup_count', default=7)
    
    # Create rotating file handler
    file_handler = logging.handlers.TimedRotatingFileHandler(
        log_path,
        when=rotation_when,
        backupCount=backup_count
    )
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('selenium').setLevel(logging.WARNING)
    
    # Log configuration completed
    logging.info(f"Logging initialized at level {log_level_str}")

# Initialize logging with default settings
setup_logging()