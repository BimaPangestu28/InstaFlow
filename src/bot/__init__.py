"""
Bot package for InstaFlow.

This package provides Instagram automation functionality.
"""

from .instagram import InstagramBot
from .actions import (
    follow_users_by_hashtag,
    engage_with_followers,
    unfollow_non_followers,
    like_by_location,
    auto_reply_to_comments,
    run_daily_engagement_routine
)
from .utils import (
    random_delay,
    generate_random_comment,
    get_current_timestamp,
    create_directory_if_not_exists,
    username_to_profile_url,
    post_id_to_url,
    hashtag_to_url
)

__all__ = [
    'InstagramBot',
    'follow_users_by_hashtag',
    'engage_with_followers',
    'unfollow_non_followers',
    'like_by_location',
    'auto_reply_to_comments',
    'run_daily_engagement_routine',
    'random_delay',
    'generate_random_comment',
    'get_current_timestamp',
    'create_directory_if_not_exists',
    'username_to_profile_url',
    'post_id_to_url',
    'hashtag_to_url'
]