"""
Instagram bot module providing the core functionality for Instagram automation.

This module contains the InstagramBot class for interacting with Instagram.
"""

import logging
import os
import pickle
import time
from typing import Dict, List, Optional, Tuple, Union

from selenium.common.exceptions import (ElementClickInterceptedException,
                                       NoSuchElementException, StaleElementReferenceException,
                                       TimeoutException, WebDriverException)
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from ..config.settings import settings
from .base import BaseBot
from .challenge_handler import ChallengeHandler
from .utils import random_delay

# Setup logger
logger = logging.getLogger(__name__)


class InstagramBot(BaseBot):
    """
    Instagram automation bot for performing various actions on Instagram.
    
    This class provides methods for logging in, following users, exploring hashtags,
    and other Instagram interactions, while handling rate limits and detection prevention.
    """
    
    def __init__(self, username: Optional[str] = None, password: Optional[str] = None):
        """
        Initialize the Instagram bot with given credentials.
        
        Args:
            username: Instagram username (defaults to environment variable)
            password: Instagram password (defaults to environment variable)
        """
        # Set Instagram-specific attributes before calling parent init
        self.username = username or os.getenv('INSTAGRAM_USERNAME')
        self.password = password or os.getenv('INSTAGRAM_PASSWORD')
        
        if not self.username or not self.password:
            raise ValueError("Instagram credentials not provided and not found in environment variables")
            
        # Initialize parent class
        super().__init__(self.username, self.password)
        
        # Set Instagram-specific attributes
        self.base_url = "https://www.instagram.com"
        self.cookies_path = os.path.join(
            settings.get('cookies', 'path', default='data/cookies'),
            f'{self.username}_cookies.pkl'
        )
        
        # Ensure cookies directory exists
        os.makedirs(os.path.dirname(self.cookies_path), exist_ok=True)
        
        # Initialize challenge handler
        self.challenge_handler = ChallengeHandler(self.driver, self.wait)
        
        # Initialize action counters for Instagram-specific rate limiting
        self._action_counts = {
            'follows': 0,
            'unfollows': 0,
            'likes': 0,
            'comments': 0,
            'dm_sends': 0,
            'stories_viewed': 0
        }
        
        logger.info(f"InstagramBot initialized for user @{self.username}")
    
    def _check_login_status(self) -> bool:
        """
        Check if the current session is logged in.
        
        Returns:
            bool: True if logged in, False otherwise
        """
        try:
            # Look for elements that indicate a logged-in state
            self.driver.find_element(By.XPATH, "//a[contains(@href, '/direct/inbox/')]")
            logger.debug("Login check: User is logged in")
            return True
        except (NoSuchElementException, TimeoutException):
            logger.debug("Login check: User is not logged in")
            return False
    
    def _handle_save_login_prompt(self) -> None:
        """
        Handle the 'Save Login Info' prompt that appears after login.
        """
        try:
            # Wait for and click "Not Now" button
            not_now_button = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Not Now')]"))
            )
            not_now_button.click()
            logger.debug("Clicked 'Not Now' on save login prompt")
        except (TimeoutException, NoSuchElementException):
            logger.debug("No 'Save Login Info' prompt appeared or it was already handled")
    
    def _handle_notifications_prompt(self) -> None:
        """
        Handle the 'Turn on Notifications' prompt that might appear.
        """
        try:
            # Wait for and click "Not Now" button
            not_now_button = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Not Now')]"))
            )
            not_now_button.click()
            logger.debug("Clicked 'Not Now' on notifications prompt")
        except (TimeoutException, NoSuchElementException):
            logger.debug("No notifications prompt appeared or it was already handled")
    
    def login(self) -> bool:
        """
        Log in to Instagram using stored credentials.
        
        Attempts to use cookies first, then falls back to username/password.
        
        Returns:
            bool: True if login successful, False otherwise
        """
        logger.info(f"Attempting to log in as @{self.username}")
        
        try:
            # Try cookies first
            if self._load_cookies():
                # Check if we're actually logged in
                if self._check_login_status():
                    logger.info("Login with cookies successful")
                    return True
                logger.debug("Cookies loaded but not logged in, trying username/password")
            
            # Navigate to login page
            self.driver.get(f"{self.base_url}/accounts/login/")
            
            # Wait for login form
            username_input = self.wait.until(
                EC.presence_of_element_located((By.NAME, 'username'))
            )
            
            # Enter credentials
            username_input.send_keys(self.username)
            password_input = self.driver.find_element(By.NAME, 'password')
            password_input.send_keys(self.password)
            
            # Submit login form
            password_input.send_keys(Keys.RETURN)
            
            # Check for login challenges
            time.sleep(3)  # Wait a moment for any challenge to appear
            if self.challenge_handler.check_for_challenge():
                logger.warning("Login challenge detected, attempting to handle")
                if not self.challenge_handler.handle_challenge():
                    logger.error("Failed to handle login challenge")
                    return False
            
            # Wait for successful login
            self.wait.until(
                EC.presence_of_element_located((By.XPATH, "//a[contains(@href, '/direct/inbox/')]"))
            )
            
            # Handle post-login prompts
            self._handle_save_login_prompt()
            self._handle_notifications_prompt()
            
            # Save cookies for future use
            self._save_cookies()
            
            logger.info("Login with username/password successful")
            return True
            
        except Exception as e:
            logger.error(f"Login failed: {e}")
            return False
    
    def follow_user(self, username: str) -> bool:
        """
        Follow a specific Instagram user.
        
        Args:
            username: Username of the account to follow
            
        Returns:
            bool: True if successfully followed, False otherwise
        """
        # Check rate limit first
        if not self._check_rate_limit('follows'):
            return False
            
        logger.info(f"Attempting to follow user @{username}")
        
        try:
            # Navigate to user's profile
            self.driver.get(f"{self.base_url}/{username}/")
            
            # Wait for the profile to load and find follow button
            follow_button = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Follow')]"))
            )
            
            # Apply random delay to mimic human behavior
            random_delay()
            
            # Click follow button
            follow_button.click()
            
            # Wait a moment for the action to complete
            random_delay(min_seconds=1, max_seconds=3)
            
            # Update success rate tracking
            self._update_success_rate('follows', True)
            
            logger.info(f"Successfully followed @{username}")
            return True
            
        except TimeoutException:
            logger.warning(f"Follow button not found for @{username}, might already be following")
            # Update success rate tracking
            self._update_success_rate('follows', False)
            return False
        except ElementClickInterceptedException:
            logger.warning(f"Follow button was intercepted for @{username}, possible popup")
            # Update success rate tracking
            self._update_success_rate('follows', False)
            return False
        except Exception as e:
            logger.error(f"Error following @{username}: {e}")
            # Update success rate tracking
            self._update_success_rate('follows', False)
            return False
    
    def unfollow_user(self, username: str) -> bool:
        """
        Unfollow a specific Instagram user.
        
        Args:
            username: Username of the account to unfollow
            
        Returns:
            bool: True if successfully unfollowed, False otherwise
        """
        # Check rate limit first
        if not self._check_rate_limit('unfollows'):
            return False
            
        logger.info(f"Attempting to unfollow user @{username}")
        
        try:
            # Navigate to user's profile
            self.driver.get(f"{self.base_url}/{username}/")
            
            # Wait for the profile to load and find following button
            unfollow_button = self.wait.until(
                EC.element_to_be_clickable((
                    By.XPATH, 
                    "//button[contains(@class, 'following') or contains(text(), 'Following')]"
                ))
            )
            
            # Apply random delay to mimic human behavior
            random_delay()
            
            # Click to open unfollow dialog
            unfollow_button.click()
            
            # Wait for and click the confirm unfollow button in the dialog
            confirm_button = self.wait.until(
                EC.element_to_be_clickable((
                    By.XPATH, 
                    "//button[contains(text(), 'Unfollow') and not(ancestor::button)]"
                ))
            )
            
            # Apply another small delay
            random_delay(min_seconds=1, max_seconds=2)
            
            # Click confirm
            confirm_button.click()
            
            # Wait a moment for the action to complete
            random_delay(min_seconds=1, max_seconds=3)
            
            # Update success rate tracking
            self._update_success_rate('unfollows', True)
            
            logger.info(f"Successfully unfollowed @{username}")
            return True
            
        except TimeoutException:
            logger.warning(f"Unfollow button not found for @{username}, might not be following")
            # Update success rate tracking
            self._update_success_rate('unfollows', False)
            return False
        except ElementClickInterceptedException:
            logger.warning(f"Unfollow button was intercepted for @{username}, possible popup")
            # Update success rate tracking
            self._update_success_rate('unfollows', False)
            return False
        except Exception as e:
            logger.error(f"Error unfollowing @{username}: {e}")
            # Update success rate tracking
            self._update_success_rate('unfollows', False)
            return False
    
    def like_post(self, post_url: str) -> bool:
        """
        Like a specific Instagram post.
        
        Args:
            post_url: URL of the post to like
            
        Returns:
            bool: True if successfully liked, False otherwise
        """
        # Check rate limit first
        if not self._check_rate_limit('likes'):
            return False
            
        logger.info(f"Attempting to like post: {post_url}")
        
        try:
            # Navigate to the post
            self.driver.get(post_url)
            
            # Wait for post to load
            self.wait.until(
                EC.presence_of_element_located((By.XPATH, "//article"))
            )
            
            # Find like button
            like_button = self.driver.find_element(
                By.XPATH,
                "//span[@class='_aamw']//button[not(.//*[local-name()='svg']/*[contains(@fill, 'rgb(255, 48, 64)')])]"
            )
            
            # Apply random delay to mimic human behavior
            random_delay()
            
            # Click like button
            like_button.click()
            
            # Wait a moment for the action to complete
            random_delay(min_seconds=1, max_seconds=2)
            
            # Update success rate tracking
            self._update_success_rate('likes', True)
            
            logger.info(f"Successfully liked post: {post_url}")
            return True
            
        except NoSuchElementException:
            logger.warning(f"Like button not found for {post_url}, post might already be liked")
            # Update success rate tracking
            self._update_success_rate('likes', False)
            return False
        except Exception as e:
            logger.error(f"Error liking post {post_url}: {e}")
            # Update success rate tracking
            self._update_success_rate('likes', False)
            return False
    
    def explore_hashtag(self, hashtag: str, num_posts: int = 5) -> List[str]:
        """
        Explore posts from a specific hashtag and return their URLs.
        
        Args:
            hashtag: Hashtag to explore without the '#' symbol
            num_posts: Number of posts to collect (default: 5)
            
        Returns:
            List of post URLs
        """
        logger.info(f"Exploring hashtag #{hashtag}")
        post_urls = []
        
        try:
            # Navigate to hashtag page
            self.driver.get(f"{self.base_url}/explore/tags/{hashtag}/")
            
            # Wait for posts to load
            self.wait.until(
                EC.presence_of_element_located((By.XPATH, "//article//a"))
            )
            
            # Apply random delay to mimic human behavior
            random_delay()
            
            # Find post links
            post_links = self.driver.find_elements(By.XPATH, "//article//a")
            
            # Get URLs for the specified number of posts
            for i, link in enumerate(post_links):
                if i >= num_posts:
                    break
                    
                post_url = link.get_attribute('href')
                if post_url:
                    post_urls.append(post_url)
            
            logger.info(f"Found {len(post_urls)} posts for hashtag #{hashtag}")
            return post_urls
            
        except Exception as e:
            logger.error(f"Error exploring hashtag #{hashtag}: {e}")
            return post_urls
    
    def comment_on_post(self, post_url: str, comment_text: str) -> bool:
        """
        Comment on a specific Instagram post.
        
        Args:
            post_url: URL of the post to comment on
            comment_text: Text to comment on the post
            
        Returns:
            bool: True if successfully commented, False otherwise
        """
        # Check rate limit first
        if not self._check_rate_limit('comments'):
            return False
            
        logger.info(f"Attempting to comment on post: {post_url}")
        
        try:
            # Navigate to the post
            self.driver.get(post_url)
            
            # Wait for post to load
            self.wait.until(
                EC.presence_of_element_located((By.XPATH, "//article"))
            )
            
            # Apply random delay to mimic human behavior
            random_delay()
            
            # Find comment input field
            comment_input = self.wait.until(
                EC.presence_of_element_located((
                    By.XPATH, 
                    "//form//textarea[@placeholder='Add a comment…']"
                ))
            )
            
            # Click on the input to activate it
            comment_input.click()
            
            # Find the expanded input field (it might change after clicking)
            comment_input = self.wait.until(
                EC.presence_of_element_located((
                    By.XPATH, 
                    "//form//textarea[@placeholder='Add a comment…']"
                ))
            )
            
            # Type comment
            comment_input.send_keys(comment_text)
            
            # Apply random delay to mimic human behavior
            random_delay(min_seconds=1, max_seconds=3)
            
            # Submit the comment
            comment_input.send_keys(Keys.RETURN)
            
            # Wait for the comment to be posted
            random_delay(min_seconds=2, max_seconds=4)
            
            # Update success rate tracking
            self._update_success_rate('comments', True)
            
            logger.info(f"Successfully commented on post: {post_url}")
            return True
            
        except Exception as e:
            logger.error(f"Error commenting on post {post_url}: {e}")
            # Update success rate tracking
            self._update_success_rate('comments', False)
            return False
    
    def get_user_followers(self, username: str, max_count: int = 50) -> List[str]:
        """
        Get a list of followers for a specific user.
        
        Args:
            username: Username to get followers from
            max_count: Maximum number of followers to retrieve
            
        Returns:
            List of follower usernames
        """
        logger.info(f"Retrieving followers for @{username} (max: {max_count})")
        followers = []
        
        try:
            # Navigate to user's profile
            self.driver.get(f"{self.base_url}/{username}/")
            
            # Wait for the profile to load
            self.wait.until(
                EC.presence_of_element_located((By.XPATH, "//header"))
            )
            
            # Click on followers count to open followers list
            followers_link = self.wait.until(
                EC.element_to_be_clickable((
                    By.XPATH, 
                    "//a[contains(@href, '/followers')]"
                ))
            )
            
            followers_link.click()
            
            # Wait for followers dialog to appear
            followers_dialog = self.wait.until(
                EC.presence_of_element_located((
                    By.XPATH, 
                    "//div[@role='dialog']"
                ))
            )
            
            # Scroll to load more followers
            scroll_attempts = 0
            max_scroll_attempts = max(1, max_count // 10)  # Adjust based on max_count
            
            while len(followers) < max_count and scroll_attempts < max_scroll_attempts:
                # Find follower elements
                follower_elements = followers_dialog.find_elements(
                    By.XPATH,
                    ".//a[contains(@href, '/') and not(contains(@href, '/followers'))]"
                )
                
                # Extract usernames
                for element in follower_elements:
                    username = element.get_attribute('href').split('/')[-2]
                    if username and username not in followers:
                        followers.append(username)
                        
                    if len(followers) >= max_count:
                        break
                
                if len(followers) >= max_count:
                    break
                    
                # Scroll down in the dialog
                self.driver.execute_script(
                    "arguments[0].scrollTop = arguments[0].scrollHeight", 
                    followers_dialog
                )
                
                # Wait for more followers to load
                random_delay(min_seconds=1, max_seconds=2)
                
                scroll_attempts += 1
            
            logger.info(f"Retrieved {len(followers)} followers for @{username}")
            return followers
            
        except Exception as e:
            logger.error(f"Error retrieving followers for @{username}: {e}")
            return followers
    
    def view_story(self, username: str) -> bool:
        """
        View the Instagram story of a specific user.
        
        Args:
            username: Username of the account whose story to view
            
        Returns:
            bool: True if successfully viewed story, False otherwise
        """
        # Check rate limit first
        if not self._check_rate_limit('stories_viewed'):
            return False
            
        logger.info(f"Attempting to view story of @{username}")
        
        try:
            # Navigate to user's profile
            self.driver.get(f"{self.base_url}/{username}/")
            
            # Wait for the profile to load
            self.wait.until(
                EC.presence_of_element_located((By.XPATH, "//header"))
            )
            
            # Check if story is available
            story_element = None
            try:
                story_element = self.driver.find_element(
                    By.XPATH,
                    "//div[contains(@class, 'story-ring')]"
                )
            except NoSuchElementException:
                logger.info(f"@{username} doesn't have an active story")
                return False
            
            # Click on the story
            story_element.click()
            
            # Wait for story to load
            self.wait.until(
                EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'story')]"))
            )
            
            # Wait for a random amount of time to simulate viewing
            random_delay(min_seconds=2, max_seconds=10)
            
            # Multiple story items - randomly view a few
            story_items = random.randint(1, 5)
            for _ in range(story_items):
                try:
                    # Click right side to advance to next item
                    next_button = self.driver.find_element(
                        By.XPATH,
                        "//button[contains(@class, 'next')]"
                    )
                    next_button.click()
                    random_delay(min_seconds=1, max_seconds=5)
                except NoSuchElementException:
                    break  # No more story items
            
            # Press ESC to exit story viewer
            webdriver.ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
            
            # Update success rate tracking
            self._update_success_rate('stories_viewed', True)
            
            logger.info(f"Successfully viewed story of @{username}")
            return True
            
        except Exception as e:
            logger.error(f"Error viewing story of @{username}: {e}")
            # Update success rate tracking
            self._update_success_rate('stories_viewed', False)
            return False
    
    def send_direct_message(self, username: str, message: str) -> bool:
        """
        Send a direct message to a specific Instagram user.
        
        Args:
            username: Username of the account to message
            message: Message text to send
            
        Returns:
            bool: True if successfully sent message, False otherwise
        """
        # Check rate limit first
        if not self._check_rate_limit('dm_sends'):
            return False
            
        logger.info(f"Attempting to send DM to @{username}")
        
        try:
            # Navigate to direct messages
            self.driver.get(f"{self.base_url}/direct/inbox/")
            
            # Wait for inbox to load
            self.wait.until(
                EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'inbox')]"))
            )
            
            # Click on new message button
            new_message_button = self.driver.find_element(
                By.XPATH,
                "//button[contains(text(), 'New message') or contains(@aria-label, 'New message')]"
            )
            new_message_button.click()
            
            # Wait for recipient selector dialog
            recipient_input = self.wait.until(
                EC.presence_of_element_located((By.XPATH, "//input[contains(@placeholder, 'Search')]"))
            )
            
            # Type username
            recipient_input.send_keys(username)
            
            # Wait for search results
            random_delay(min_seconds=1, max_seconds=3)
            
            # Select the user from search results
            user_element = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, f"//div[contains(text(), '{username}')]"))
            )
            user_element.click()
            
            # Click Next button
            next_button = self.driver.find_element(
                By.XPATH,
                "//button[contains(text(), 'Next')]"
            )
            next_button.click()
            
            # Wait for message input field
            message_input = self.wait.until(
                EC.presence_of_element_located((By.XPATH, "//textarea[contains(@placeholder, 'Message')]"))
            )
            
            # Type message
            message_input.send_keys(message)
            
            # Wait a moment before sending
            random_delay(min_seconds=1, max_seconds=3)
            
            # Send the message
            message_input.send_keys(Keys.RETURN)
            
            # Wait for the message to be sent
            random_delay(min_seconds=2, max_seconds=4)
            
            # Update success rate tracking
            self._update_success_rate('dm_sends', True)
            
            logger.info(f"Successfully sent DM to @{username}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending DM to @{username}: {e}")
            # Update success rate tracking
            self._update_success_rate('dm_sends', False)
            return False
    
    def get_competitor_followers(self, competitor_username: str, max_count: int = 50) -> List[str]:
        """
        Get followers of a competitor/similar account for targeting.
        
        This is a wrapper around get_user_followers but with specific logging.
        
        Args:
            competitor_username: Username of the competitor account
            max_count: Maximum number of followers to retrieve
            
        Returns:
            List of follower usernames
        """
        logger.info(f"Retrieving followers from competitor @{competitor_username}")
        return self.get_user_followers(competitor_username, max_count)
    
    def find_users_by_location(self, location_id: str, max_count: int = 20) -> List[str]:
        """
        Find users who posted at a specific location.
        
        Args:
            location_id: Instagram location ID
            max_count: Maximum number of users to retrieve
            
        Returns:
            List of usernames
        """
        logger.info(f"Finding users for location {location_id}")
        usernames = []
        
        try:
            # Navigate to the location page
            self.driver.get(f"{self.base_url}/explore/locations/{location_id}/")
            
            # Wait for posts to load
            self.wait.until(
                EC.presence_of_element_located((By.XPATH, "//article//a"))
            )
            
            # Apply random delay to mimic human behavior
            random_delay()
            
            # Find post links
            post_links = self.driver.find_elements(By.XPATH, "//article//a")
            
            # Process posts until we reach the max count
            post_urls = []
            for link in post_links:
                post_url = link.get_attribute('href')
                if post_url:
                    post_urls.append(post_url)
            
            # Visit each post to get the username
            for post_url in post_urls[:min(len(post_urls), max_count * 2)]:  # Get more than needed
                if len(usernames) >= max_count:
                    break
                    
                try:
                    # Navigate to the post
                    self.driver.get(post_url)
                    
                    # Wait for post to load
                    self.wait.until(
                        EC.presence_of_element_located((By.XPATH, "//article"))
                    )
                    
                    # Find username
                    username_element = self.driver.find_element(
                        By.XPATH,
                        "//a[contains(@href, '/') and not(contains(@href, '/explore'))]"
                    )
                    
                    username = username_element.get_attribute('href').split('/')[-2]
                    
                    if username and username not in usernames:
                        usernames.append(username)
                    
                    # Add random delay between post visits
                    random_delay(min_seconds=1, max_seconds=3)
                    
                except Exception as e:
                    logger.error(f"Error processing post {post_url}: {e}")
                    continue
            
            logger.info(f"Found {len(usernames)} users for location {location_id}")
            return usernames
            
        except Exception as e:
            logger.error(f"Error finding users for location {location_id}: {e}")
            return usernames