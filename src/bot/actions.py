"""
Instagram action module providing higher-level automation workflows.

This module contains functions for automated Instagram workflows like
follower growth, engagement campaigns, and content interaction.
"""

import logging
import random
import time
from typing import Dict, List, Optional, Tuple, Union

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException

from .instagram import InstagramBot
from .utils import random_delay, generate_random_comment

# Setup logger
logger = logging.getLogger(__name__)


def follow_users_by_hashtag(
    bot: InstagramBot, 
    hashtag: str, 
    count: int = 10,
    like_posts: bool = True,
    comment: bool = False,
    comment_templates: Optional[List[str]] = None
) -> Dict[str, int]:
    """
    Follow users who have posted with a specific hashtag.
    
    Args:
        bot: Initialized InstagramBot instance
        hashtag: Hashtag to target (without #)
        count: Maximum number of users to follow
        like_posts: Whether to also like the user's posts
        comment: Whether to comment on posts
        comment_templates: List of comment templates if commenting
        
    Returns:
        Dictionary with action counts (follows, likes, comments)
    """
    results = {
        'follows': 0,
        'likes': 0,
        'comments': 0,
        'errors': 0
    }
    
    logger.info(f"Starting follow campaign for hashtag #{hashtag}")
    
    try:
        # Explore the hashtag to get recent posts
        post_urls = bot.explore_hashtag(hashtag, count * 2)  # Get more than needed
        
        # Process posts until we reach the desired follow count
        for post_url in post_urls:
            if results['follows'] >= count:
                break
                
            try:
                # Navigate to the post
                bot.driver.get(post_url)
                random_delay(1, 3)
                
                # Find the username
                username_element = bot.wait.until(
                    EC.presence_of_element_located((
                        By.XPATH, 
                        "//a[contains(@href, '/') and not(contains(@href, '/explore'))]"
                    ))
                )
                username = username_element.get_attribute('href').split('/')[-2]
                
                # Like the post if enabled
                if like_posts:
                    if bot.like_post(post_url):
                        results['likes'] += 1
                    
                    # Add delay between like and follow
                    random_delay(2, 4)
                
                # Comment on the post if enabled
                if comment and comment_templates:
                    comment_text = generate_random_comment(
                        comment_templates,
                        {
                            'emoji': ['❤️', '🔥', '👍', '😊', '✨', '👏'],
                            'adjective': ['amazing', 'awesome', 'great', 'nice', 'cool', 'fantastic']
                        }
                    )
                    
                    if bot.comment_on_post(post_url, comment_text):
                        results['comments'] += 1
                    
                    # Add delay between comment and follow
                    random_delay(3, 5)
                
                # Follow the user
                if bot.follow_user(username):
                    results['follows'] += 1
                    logger.info(f"Followed @{username} from hashtag #{hashtag}")
                
                # Add delay between users
                random_delay(15, 30)
                
            except Exception as e:
                logger.error(f"Error processing post {post_url}: {e}")
                results['errors'] += 1
                random_delay(5, 10)  # Longer delay after error
    
    except Exception as e:
        logger.error(f"Follow campaign error for #{hashtag}: {e}")
        results['errors'] += 1
    
    logger.info(f"Completed follow campaign for #{hashtag}. Results: {results}")
    return results


def engage_with_followers(
    bot: InstagramBot,
    count: int = 10,
    like_count: int = 3,
    comment: bool = False,
    comment_templates: Optional[List[str]] = None
) -> Dict[str, int]:
    """
    Engage with existing followers by liking and optionally commenting on their posts.
    
    Args:
        bot: Initialized InstagramBot instance
        count: Maximum number of followers to engage with
        like_count: Number of posts to like for each follower
        comment: Whether to comment on posts
        comment_templates: List of comment templates if commenting
        
    Returns:
        Dictionary with action counts (likes, comments)
    """
    results = {
        'followers_engaged': 0,
        'likes': 0,
        'comments': 0,
        'errors': 0
    }
    
    logger.info(f"Starting follower engagement campaign")
    
    try:
        # Get list of followers
        followers = bot.get_user_followers(bot.username, max_count=count*2)
        
        # Shuffle to randomize
        random.shuffle(followers)
        
        # Process followers until we reach the desired count
        for username in followers[:count]:
            try:
                # Navigate to the user's profile
                bot.driver.get(f"https://www.instagram.com/{username}/")
                random_delay(2, 4)
                
                # Find post links
                post_links = bot.driver.find_elements(
                    By.XPATH, 
                    "//article//a[contains(@href, '/p/')]"
                )
                
                post_urls = []
                for link in post_links[:like_count]:
                    post_url = link.get_attribute('href')
                    if post_url:
                        post_urls.append(post_url)
                
                # Like and maybe comment on their posts
                posts_engaged = 0
                for post_url in post_urls:
                    # Like the post
                    if bot.like_post(post_url):
                        results['likes'] += 1
                        posts_engaged += 1
                    
                    # Comment if enabled
                    if comment and comment_templates and random.random() < 0.3:  # 30% chance to comment
                        comment_text = generate_random_comment(
                            comment_templates,
                            {
                                'emoji': ['❤️', '🔥', '👍', '😊', '✨', '👏'],
                                'adjective': ['amazing', 'awesome', 'great', 'nice', 'cool', 'fantastic']
                            }
                        )
                        
                        if bot.comment_on_post(post_url, comment_text):
                            results['comments'] += 1
                    
                    # Add delay between posts
                    random_delay(5, 10)
                
                if posts_engaged > 0:
                    results['followers_engaged'] += 1
                    logger.info(f"Engaged with @{username}, liked {posts_engaged} posts")
                
                # Add delay between users
                random_delay(15, 30)
                
            except Exception as e:
                logger.error(f"Error engaging with follower @{username}: {e}")
                results['errors'] += 1
                random_delay(5, 10)  # Longer delay after error
    
    except Exception as e:
        logger.error(f"Follower engagement campaign error: {e}")
        results['errors'] += 1
    
    logger.info(f"Completed follower engagement campaign. Results: {results}")
    return results


def unfollow_non_followers(
    bot: InstagramBot,
    count: int = 10,
    days_threshold: int = 7,
    whitelist: Optional[List[str]] = None
) -> Dict[str, int]:
    """
    Unfollow users who don't follow back after a certain period.
    
    Args:
        bot: Initialized InstagramBot instance
        count: Maximum number of users to unfollow
        days_threshold: Minimum days to wait before unfollowing
        whitelist: List of usernames to never unfollow
        
    Returns:
        Dictionary with action counts (unfollows)
    """
    results = {
        'unfollows': 0,
        'skipped_whitelist': 0,
        'errors': 0
    }
    
    logger.info(f"Starting unfollow campaign for non-followers")
    
    if whitelist is None:
        whitelist = []
    
    try:
        # This is a simplified version - a real implementation would need
        # to track when users were followed, to respect the days_threshold
        
        # Get followers and following
        followers = set(bot.get_user_followers(bot.username, max_count=1000))
        
        # Navigate to profile page to get following
        bot.driver.get(f"https://www.instagram.com/{bot.username}/")
        
        # Click on following count to open following list
        following_link = bot.wait.until(
            EC.element_to_be_clickable((
                By.XPATH, 
                "//a[contains(@href, '/following')]"
            ))
        )
        
        following_link.click()
        
        # Wait for dialog to appear
        following_dialog = bot.wait.until(
            EC.presence_of_element_located((
                By.XPATH, 
                "//div[@role='dialog']"
            ))
        )
        
        # Get following usernames
        following_elements = following_dialog.find_elements(
            By.XPATH,
            ".//a[contains(@href, '/') and not(contains(@href, '/following'))]"
        )
        
        following = set()
        for element in following_elements:
            username = element.get_attribute('href').split('/')[-2]
            if username:
                following.add(username)
        
        # Find users to unfollow (not following back and not in whitelist)
        to_unfollow = list(following - followers)
        to_unfollow = [user for user in to_unfollow if user not in whitelist]
        
        # Shuffle to randomize
        random.shuffle(to_unfollow)
        
        # Process users to unfollow
        for i, username in enumerate(to_unfollow[:count]):
            try:
                if username in whitelist:
                    results['skipped_whitelist'] += 1
                    continue
                
                # Unfollow the user
                if bot.unfollow_user(username):
                    results['unfollows'] += 1
                    logger.info(f"Unfollowed non-follower @{username} ({i+1}/{min(count, len(to_unfollow))})")
                
                # Add delay between unfollows
                random_delay(15, 30)
                
            except Exception as e:
                logger.error(f"Error unfollowing @{username}: {e}")
                results['errors'] += 1
                random_delay(5, 10)  # Longer delay after error
    
    except Exception as e:
        logger.error(f"Unfollow campaign error: {e}")
        results['errors'] += 1
    
    logger.info(f"Completed unfollow campaign. Results: {results}")
    return results


def like_by_location(
    bot: InstagramBot,
    location_id: str,
    count: int = 10,
    comment: bool = False,
    comment_templates: Optional[List[str]] = None
) -> Dict[str, int]:
    """
    Like posts from a specific location.
    
    Args:
        bot: Initialized InstagramBot instance
        location_id: Instagram location ID
        count: Maximum number of posts to like
        comment: Whether to comment on posts
        comment_templates: List of comment templates if commenting
        
    Returns:
        Dictionary with action counts (likes, comments)
    """
    results = {
        'likes': 0,
        'comments': 0,
        'errors': 0
    }
    
    logger.info(f"Starting location-based liking campaign for location {location_id}")
    
    try:
        # Navigate to the location page
        bot.driver.get(f"https://www.instagram.com/explore/locations/{location_id}/")
        random_delay(2, 4)
        
        # Wait for posts to load
        post_links = bot.wait.until(
            EC.presence_of_all_elements_located((
                By.XPATH, 
                "//article//a[contains(@href, '/p/')]"
            ))
        )
        
        post_urls = []
        for link in post_links:
            post_url = link.get_attribute('href')
            if post_url:
                post_urls.append(post_url)
        
        # Like and maybe comment on posts
        for i, post_url in enumerate(post_urls[:count]):
            try:
                # Like the post
                if bot.like_post(post_url):
                    results['likes'] += 1
                    logger.info(f"Liked post {post_url} from location {location_id} ({i+1}/{min(count, len(post_urls))})")
                
                # Comment if enabled
                if comment and comment_templates and random.random() < 0.3:  # 30% chance to comment
                    comment_text = generate_random_comment(
                        comment_templates,
                        {
                            'emoji': ['❤️', '🔥', '👍', '😊', '✨', '👏'],
                            'adjective': ['amazing', 'awesome', 'great', 'nice', 'cool', 'fantastic'],
                            'place': ['place', 'location', 'spot', 'area', 'venue']
                        }
                    )
                    
                    if bot.comment_on_post(post_url, comment_text):
                        results['comments'] += 1
                
                # Add delay between posts
                random_delay(5, 15)
                
            except Exception as e:
                logger.error(f"Error processing post {post_url}: {e}")
                results['errors'] += 1
                random_delay(5, 10)  # Longer delay after error
    
    except Exception as e:
        logger.error(f"Location-based liking campaign error for {location_id}: {e}")
        results['errors'] += 1
    
    logger.info(f"Completed location-based liking campaign. Results: {results}")
    return results


def auto_reply_to_comments(
    bot: InstagramBot,
    post_urls: List[str],
    reply_templates: List[str],
    max_replies_per_post: int = 5
) -> Dict[str, int]:
    """
    Automatically reply to comments on your posts.
    
    Args:
        bot: Initialized InstagramBot instance
        post_urls: List of your post URLs to monitor
        reply_templates: List of reply templates
        max_replies_per_post: Maximum number of replies per post
        
    Returns:
        Dictionary with action counts (replies)
    """
    results = {
        'replies': 0,
        'posts_processed': 0,
        'errors': 0
    }
    
    logger.info(f"Starting auto-reply to comments campaign")
    
    try:
        # Process each post
        for post_url in post_urls:
            try:
                # Navigate to the post
                bot.driver.get(post_url)
                random_delay(2, 4)
                
                # Find comments
                comments = bot.driver.find_elements(
                    By.XPATH,
                    "//ul[@class='_a9ym']//li[contains(@class, '_a9zj')]"
                )
                
                replies_made = 0
                for comment in comments[:max_replies_per_post]:
                    try:
                        # Find username of commenter
                        username_element = comment.find_element(
                            By.XPATH,
                            ".//a[contains(@href, '/')]"
                        )
                        username = username_element.get_attribute('href').split('/')[-2]
                        
                        # Skip if it's our own comment
                        if username == bot.username:
                            continue
                        
                        # Find reply button
                        reply_button = comment.find_element(
                            By.XPATH,
                            ".//button[contains(text(), 'Reply')]"
                        )
                        reply_button.click()
                        
                        # Wait for reply field to appear
                        reply_field = bot.wait.until(
                            EC.presence_of_element_located((
                                By.XPATH, 
                                "//form//textarea[@placeholder='Reply...']"
                            ))
                        )
                        
                        # Generate reply with @username
                        reply_text = f"@{username} " + random.choice(reply_templates)
                        
                        # Type reply
                        reply_field.send_keys(reply_text)
                        random_delay(1, 2)
                        
                        # Submit reply
                        reply_field.send_keys(Keys.RETURN)
                        random_delay(2, 3)
                        
                        replies_made += 1
                        results['replies'] += 1
                        
                        # Add delay between replies
                        random_delay(10, 20)
                        
                    except Exception as e:
                        logger.error(f"Error replying to comment on {post_url}: {e}")
                        results['errors'] += 1
                        random_delay(3, 5)
                
                if replies_made > 0:
                    logger.info(f"Made {replies_made} replies on post {post_url}")
                
                results['posts_processed'] += 1
                
                # Add delay between posts
                random_delay(15, 30)
                
            except Exception as e:
                logger.error(f"Error processing post comments on {post_url}: {e}")
                results['errors'] += 1
                random_delay(5, 10)
    
    except Exception as e:
        logger.error(f"Auto-reply campaign error: {e}")
        results['errors'] += 1
    
    logger.info(f"Completed auto-reply campaign. Results: {results}")
    return results


def run_daily_engagement_routine(
    bot: InstagramBot,
    hashtags: List[str] = None,
    follow_count: int = 20,
    unfollow_count: int = 15,
    like_count: int = 50,
    engagement_ratio: float = 0.3
) -> Dict[str, Dict[str, int]]:
    """
    Run a complete daily engagement routine with balanced actions.
    
    Args:
        bot: Initialized InstagramBot instance
        hashtags: List of hashtags to engage with
        follow_count: Maximum number of new users to follow
        unfollow_count: Maximum number of users to unfollow
        like_count: Maximum number of posts to like
        engagement_ratio: Ratio of engagement vs. growth actions
        
    Returns:
        Dictionary with results from all actions
    """
    results = {
        'login': False,
        'follow_hashtag': {},
        'engagement': {},
        'unfollow': {}
    }
    
    logger.info("Starting daily engagement routine")
    
    try:
        # Login first
        if bot.login():
            results['login'] = True
            
            # Default hashtags if none provided
            if not hashtags:
                hashtags = ['photography', 'travel', 'food', 'fitness', 'fashion']
            
            # Randomize hashtags order
            random.shuffle(hashtags)
            
            # 1. Follow users by hashtag campaign (growth)
            follow_per_hashtag = max(1, follow_count // len(hashtags))
            for hashtag in hashtags[:3]:  # Limit to 3 hashtags per day
                results['follow_hashtag'][hashtag] = follow_users_by_hashtag(
                    bot,
                    hashtag,
                    count=follow_per_hashtag,
                    like_posts=True,
                    comment=False
                )
                
                # Add delay between hashtags
                random_delay(30, 60)
            
            # 2. Engage with existing followers
            follower_count = int(like_count * engagement_ratio)
            results['engagement'] = engage_with_followers(
                bot,
                count=follower_count,
                like_count=3,
                comment=True,
                comment_templates=[
                    "Great content! {emoji}",
                    "Love this {emoji}",
                    "This is {adjective}! {emoji}",
                    "Amazing post {emoji}",
                    "Keep up the great work! {emoji}"
                ]
            )
            
            # Add delay between major actions
            random_delay(60, 120)
            
            # 3. Unfollow non-followers campaign
            results['unfollow'] = unfollow_non_followers(
                bot,
                count=unfollow_count,
                days_threshold=7,
                whitelist=[]  # Add any accounts you never want to unfollow
            )
        
        else:
            logger.error("Daily routine failed: Could not login")
    
    except Exception as e:
        logger.error(f"Error running daily routine: {e}")
    
    logger.info(f"Completed daily engagement routine. Results summary: {results}")
    return results