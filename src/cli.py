"""
Command-line interface for InstaFlow.

This module provides a CLI for using InstaFlow.
"""

import argparse
import json
import logging
import os
import sys
from typing import Dict, List, Optional

from .bot import (
    InstagramBot,
    follow_users_by_hashtag,
    engage_with_followers,
    unfollow_non_followers,
    run_daily_engagement_routine
)
from .config import setup_logging, settings

logger = logging.getLogger(__name__)

def parse_args():
    """
    Parse command-line arguments.
    
    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description='InstaFlow: Instagram Automation Tool',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    # General options
    parser.add_argument(
        '--config', '-c',
        help='Path to custom configuration file',
        default=None
    )
    
    parser.add_argument(
        '--username', '-u',
        help='Instagram username (overrides environment variable)',
        default=None
    )
    
    parser.add_argument(
        '--password', '-p',
        help='Instagram password (overrides environment variable)',
        default=None
    )
    
    parser.add_argument(
        '--log-level',
        help='Logging level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        default=None
    )
    
    # Subcommands
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Daily routine command
    daily_parser = subparsers.add_parser(
        'daily',
        help='Run daily engagement routine'
    )
    daily_parser.add_argument(
        '--hashtags',
        help='Comma-separated list of hashtags to target',
        default='photography,travel,food,fitness,fashion'
    )
    daily_parser.add_argument(
        '--follow',
        help='Maximum number of users to follow',
        type=int,
        default=20
    )
    daily_parser.add_argument(
        '--unfollow',
        help='Maximum number of users to unfollow',
        type=int,
        default=15
    )
    daily_parser.add_argument(
        '--like',
        help='Maximum number of posts to like',
        type=int,
        default=50
    )
    
    # Follow command
    follow_parser = subparsers.add_parser(
        'follow',
        help='Follow users based on hashtag'
    )
    follow_parser.add_argument(
        'hashtag',
        help='Hashtag to target (without #)'
    )
    follow_parser.add_argument(
        '--count',
        help='Maximum number of users to follow',
        type=int,
        default=10
    )
    follow_parser.add_argument(
        '--like',
        help='Also like their posts',
        action='store_true'
    )
    follow_parser.add_argument(
        '--comment',
        help='Also comment on their posts',
        action='store_true'
    )
    
    # Engage command
    engage_parser = subparsers.add_parser(
        'engage',
        help='Engage with existing followers'
    )
    engage_parser.add_argument(
        '--count',
        help='Number of followers to engage with',
        type=int,
        default=10
    )
    engage_parser.add_argument(
        '--likes',
        help='Number of posts to like per follower',
        type=int,
        default=3
    )
    engage_parser.add_argument(
        '--comment',
        help='Also comment on their posts',
        action='store_true'
    )
    
    # Unfollow command
    unfollow_parser = subparsers.add_parser(
        'unfollow',
        help='Unfollow users who don\'t follow back'
    )
    unfollow_parser.add_argument(
        '--count',
        help='Maximum number of users to unfollow',
        type=int,
        default=10
    )
    unfollow_parser.add_argument(
        '--days',
        help='Minimum days to wait before unfollowing',
        type=int,
        default=7
    )
    unfollow_parser.add_argument(
        '--whitelist',
        help='Comma-separated list of usernames to never unfollow',
        default=''
    )
    
    return parser.parse_args()


def main():
    """
    Main entry point for the CLI.
    """
    # Parse arguments
    args = parse_args()
    
    # Setup logging with custom config if provided
    if args.config:
        setup_logging(args.config)
    
    # Override log level if specified
    if args.log_level:
        log_level = getattr(logging, args.log_level)
        logging.getLogger().setLevel(log_level)
    
    logger.info("InstaFlow CLI starting")
    
    try:
        # Initialize bot
        with InstagramBot(username=args.username, password=args.password) as bot:
            # Login
            if not bot.login():
                logger.error("Failed to login. Check credentials and try again.")
                sys.exit(1)
            
            # Execute requested command
            if args.command == 'daily':
                hashtags = args.hashtags.split(',') if args.hashtags else []
                results = run_daily_engagement_routine(
                    bot,
                    hashtags=hashtags,
                    follow_count=args.follow,
                    unfollow_count=args.unfollow,
                    like_count=args.like
                )
                logger.info(f"Daily routine completed with results: {json.dumps(results, indent=2)}")
            
            elif args.command == 'follow':
                results = follow_users_by_hashtag(
                    bot,
                    args.hashtag,
                    count=args.count,
                    like_posts=args.like,
                    comment=args.comment,
                    comment_templates=[
                        "Great content! ❤️",
                        "Love this 🔥",
                        "Amazing post 👍",
                        "Nice shot! ✨",
                        "Keep up the good work! 👏"
                    ] if args.comment else None
                )
                logger.info(f"Follow campaign completed with results: {results}")
            
            elif args.command == 'engage':
                results = engage_with_followers(
                    bot,
                    count=args.count,
                    like_count=args.likes,
                    comment=args.comment,
                    comment_templates=[
                        "Great content! ❤️",
                        "Love your feed! 🔥",
                        "Amazing post! 👍",
                        "Awesome content! ✨",
                        "Keep it up! 👏"
                    ] if args.comment else None
                )
                logger.info(f"Engagement campaign completed with results: {results}")
            
            elif args.command == 'unfollow':
                whitelist = args.whitelist.split(',') if args.whitelist else []
                results = unfollow_non_followers(
                    bot,
                    count=args.count,
                    days_threshold=args.days,
                    whitelist=whitelist
                )
                logger.info(f"Unfollow campaign completed with results: {results}")
            
            else:
                logger.error(f"Unknown command: {args.command}")
                sys.exit(1)
    
    except KeyboardInterrupt:
        logger.info("Operation interrupted by user")
    except Exception as e:
        logger.error(f"An error occurred: {e}", exc_info=True)
        sys.exit(1)
    
    logger.info("InstaFlow CLI completed successfully")


if __name__ == "__main__":
    main()