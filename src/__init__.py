"""
InstaFlow: A Python Instagram Automation Library.

This package provides a set of tools for automating Instagram interactions.
"""

import logging

from .config import setup_logging
from .bot import (
    InstagramBot,
    follow_users_by_hashtag,
    engage_with_followers,
    unfollow_non_followers,
    like_by_location,
    auto_reply_to_comments,
    run_daily_engagement_routine
)

__version__ = '0.1.0'
__author__ = 'Bima Pangestu'

# Setup logging
setup_logging()

# Package exports
__all__ = [
    'InstagramBot',
    'follow_users_by_hashtag',
    'engage_with_followers',
    'unfollow_non_followers',
    'like_by_location',
    'auto_reply_to_comments',
    'run_daily_engagement_routine',
    'setup_logging'
]