"""
Utility functions for the Instagram bot.

This module provides helper functions for various operations.
"""

import logging
import os
import random
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union

from ..config.settings import settings

# Setup logger
logger = logging.getLogger(__name__)


def random_delay(min_seconds: Optional[float] = None, max_seconds: Optional[float] = None) -> float:
    """
    Introduce a random delay to mimic human behavior.
    
    Args:
        min_seconds: Minimum delay in seconds (default from settings)
        max_seconds: Maximum delay in seconds (default from settings)
        
    Returns:
        Actual delay time in seconds
    """
    # Get delay settings from config if not provided
    if min_seconds is None:
        min_seconds = settings.get('actions', 'delay', 'min', default=2)
    
    if max_seconds is None:
        max_seconds = settings.get('actions', 'delay', 'max', default=5)
    
    # Generate random delay time
    delay_time = random.uniform(min_seconds, max_seconds)
    
    # Apply delay
    time.sleep(delay_time)
    
    # Log at debug level
    logger.debug(f"Applied random delay of {delay_time:.2f} seconds")
    
    return delay_time


def generate_random_comment(templates: List[str], variables: Dict[str, List[str]]) -> str:
    """
    Generate a random comment from templates and variables.
    
    Args:
        templates: List of comment templates with placeholder variables like {emoji}
        variables: Dictionary mapping variable names to possible values
        
    Returns:
        Generated comment string
    """
    # Select a random template
    template = random.choice(templates)
    
    # Replace all variables in the template
    for var_name, var_values in variables.items():
        placeholder = f"{{{var_name}}}"
        if placeholder in template:
            template = template.replace(placeholder, random.choice(var_values))
    
    return template


def get_current_timestamp() -> str:
    """
    Get the current timestamp in a standardized format.
    
    Returns:
        Formatted timestamp string
    """
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def create_directory_if_not_exists(path: str) -> bool:
    """
    Create a directory if it doesn't exist.
    
    Args:
        path: Directory path to create
        
    Returns:
        True if directory exists or was created, False on error
    """
    try:
        os.makedirs(path, exist_ok=True)
        return True
    except Exception as e:
        logger.error(f"Error creating directory {path}: {e}")
        return False


def username_to_profile_url(username: str) -> str:
    """
    Convert a username to a full Instagram profile URL.
    
    Args:
        username: Instagram username
        
    Returns:
        Full profile URL
    """
    return f"https://www.instagram.com/{username}/"


def post_id_to_url(post_id: str) -> str:
    """
    Convert a post ID to a full Instagram post URL.
    
    Args:
        post_id: Instagram post ID
        
    Returns:
        Full post URL
    """
    return f"https://www.instagram.com/p/{post_id}/"


def hashtag_to_url(hashtag: str) -> str:
    """
    Convert a hashtag to a full Instagram hashtag URL.
    
    Args:
        hashtag: Hashtag without the # symbol
        
    Returns:
        Full hashtag URL
    """
    return f"https://www.instagram.com/explore/tags/{hashtag}/"


def retry_on_exception(func, max_attempts: int = 3, delay: float = 2.0, 
                      exceptions: Tuple = (Exception,)):
    """
    Decorator to retry a function on specific exceptions.
    
    Args:
        func: Function to retry
        max_attempts: Maximum number of retry attempts
        delay: Delay between retries in seconds
        exceptions: Tuple of exceptions to catch and retry on
        
    Returns:
        Decorated function
    """
    def wrapper(*args, **kwargs):
        last_exception = None
        for attempt in range(1, max_attempts + 1):
            try:
                return func(*args, **kwargs)
            except exceptions as e:
                last_exception = e
                if attempt < max_attempts:
                    logger.warning(
                        f"Attempt {attempt}/{max_attempts} failed with error: {e}. "
                        f"Retrying in {delay} seconds..."
                    )
                    time.sleep(delay)
                else:
                    logger.error(
                        f"All {max_attempts} attempts failed. "
                        f"Last error: {e}"
                    )
        
        # If we get here, all attempts failed
        raise last_exception
    
    return wrapper


def extract_post_details(html_source: str) -> Dict[str, any]:
    """
    Extract post details from HTML source.
    
    Args:
        html_source: Instagram post page HTML source
        
    Returns:
        Dictionary with post details (likes_count, comments_count, timestamp, etc.)
    """
    # This is a stub implementation - a real implementation would use
    # BeautifulSoup or regex to extract data from the HTML source
    details = {
        'likes_count': 0,
        'comments_count': 0,
        'timestamp': '',
        'caption': '',
        'owner_username': '',
    }
    
    logger.warning("Post detail extraction not fully implemented")
    return details