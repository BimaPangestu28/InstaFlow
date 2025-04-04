"""
Instagram bot module providing the core functionality for Instagram automation.

This module contains the primary InstagramBot class for interacting with Instagram.
"""

import logging
import os
import pickle
import time
from typing import Dict, List, Optional, Tuple, Union

from selenium import webdriver
from selenium.common.exceptions import (ElementClickInterceptedException,
                                       NoSuchElementException, StaleElementReferenceException,
                                       TimeoutException, WebDriverException)
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

from ..config.settings import settings
from .utils import random_delay

# Setup logger
logger = logging.getLogger(__name__)


class InstagramBot:
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
        self.username = username or os.getenv('INSTAGRAM_USERNAME')
        self.password = password or os.getenv('INSTAGRAM_PASSWORD')
        
        if not self.username or not self.password:
            raise ValueError("Instagram credentials not provided and not found in environment variables")
        
        self.base_url = "https://www.instagram.com"
        self.cookies_path = os.path.join(
            settings.get('cookies', 'path', default='data/cookies'),
            f'{self.username}_cookies.pkl'
        )
        
        # Ensure cookies directory exists
        os.makedirs(os.path.dirname(self.cookies_path), exist_ok=True)
        
        # Configure webdriver
        self.driver = self._setup_driver()
        self.wait = WebDriverWait(
            self.driver, 
            settings.get('bot', 'wait_timeout', default=10)
        )
        
        # Action counters for rate limiting
        self._action_counts = {
            'follows': 0,
            'unfollows': 0,
            'likes': 0,
            'comments': 0,
            'dm_sends': 0
        }
        
        logger.info(f"InstagramBot initialized for user @{self.username}")
    
    def __enter__(self) -> 'InstagramBot':
        """
        Support for context manager protocol.
        
        Returns:
            Self instance
        """
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Clean up resources when exiting context manager.
        
        Args:
            exc_type: Exception type if an exception was raised
            exc_val: Exception value if an exception was raised
            exc_tb: Exception traceback if an exception was raised
        """
        self.close()
    
    def _setup_driver(self) -> WebDriver:
        """
        Set up and configure the Selenium WebDriver.
        
        Returns:
            Configured WebDriver instance
        """
        chrome_options = Options()
        
        # Add anti-detection options
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option('excludeSwitches', ['enable-automation', 'enable-logging'])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Set user agent
        user_agent = settings.get('webdriver', 'user_agent')
        if user_agent:
            chrome_options.add_argument(f'--user-agent={user_agent}')
        
        # Set headless mode if configured
        if settings.get('webdriver', 'headless', default=False):
            chrome_options.add_argument('--headless')
        
        # Configure proxy if set in environment
        proxy_host = os.getenv('PROXY_HOST')
        proxy_port = os.getenv('PROXY_PORT')
        if proxy_host and proxy_port:
            proxy_user = os.getenv('PROXY_USERNAME')
            proxy_pass = os.getenv('PROXY_PASSWORD')
            
            if proxy_user and proxy_pass:
                proxy_auth = f"{proxy_user}:{proxy_pass}@"
            else:
                proxy_auth = ""
                
            proxy_str = f"{proxy_auth}{proxy_host}:{proxy_port}"
            chrome_options.add_argument(f'--proxy-server={proxy_str}')
            logger.info(f"Using proxy: {proxy_host}:{proxy_port}")
        
        # Create driver
        try:
            # Check for custom chrome binary path
            chrome_binary = os.getenv('CHROME_BINARY_PATH')
            if chrome_binary:
                chrome_options.binary_location = chrome_binary
            
            # Check for custom chromedriver path
            chromedriver_path = os.getenv('CHROMEDRIVER_PATH')
            if chromedriver_path:
                driver = webdriver.Chrome(
                    service=Service(chromedriver_path),
                    options=chrome_options
                )
            else:
                # Use webdriver_manager to auto-download appropriate chromedriver
                driver = webdriver.Chrome(
                    service=Service(ChromeDriverManager().install()),
                    options=chrome_options
                )
            
            # Set window size
            driver.set_window_size(1280, 800)
            
            # Apply additional CDP settings to avoid detection
            driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                "userAgent": user_agent or (
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                    'AppleWebKit/537.36 (KHTML, like Gecko) '
                    'Chrome/91.0.4472.124 Safari/537.36'
                )
            })
            
            # Set page load strategy
            driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': '''
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                '''
            })
            
            logger.info("WebDriver initialized successfully")
            return driver
            
        except Exception as e:
            logger.error(f"Failed to initialize WebDriver: {e}")
            raise
    
    def _save_cookies(self) -> bool:
        """
        Save current session cookies to file.
        
        Returns:
            bool: True if cookies were saved successfully, False otherwise
        """
        try:
            os.makedirs(os.path.dirname(self.cookies_path), exist_ok=True)
            pickle.dump(self.driver.get_cookies(), open(self.cookies_path, 'wb'))
            logger.debug(f"Cookies saved to {self.cookies_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save cookies: {e}")
            return False
    
    def _load_cookies(self) -> bool:
        """
        Load cookies from file to current session.
        
        Returns:
            bool: True if cookies were loaded successfully, False otherwise
        """
        try:
            if not os.path.exists(self.cookies_path):
                logger.debug(f"No cookies file found at {self.cookies_path}")
                return False
                
            cookies = pickle.load(open(self.cookies_path, 'rb'))
            
            # Navigate to Instagram first (cookies domain must match)
            self.driver.get(self.base_url)
            
            # Add cookies to browser session
            for cookie in cookies:
                try:
                    self.driver.add_cookie(cookie)
                except Exception as cookie_error:
                    logger.warning(f"Failed to add cookie: {cookie_error}")
            
            # Refresh page to apply cookies
            self.driver.refresh()
            logger.debug("Cookies loaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load cookies: {e}")
            return False
    
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
    
    def _check_rate_limit(self, action_type: str) -> bool:
        """
        Check if an action would exceed rate limits.
        
        Args:
            action_type: Type of action to check (follows, unfollows, likes, comments, dm_sends)
            
        Returns:
            bool: True if action is allowed, False if rate limit would be exceeded
        """
        # Get daily limit for this action type
        daily_limit = settings.get('actions', 'daily_limits', action_type, default=0)
        
        # Check if we've reached the limit
        if self._action_counts.get(action_type, 0) >= daily_limit:
            logger.warning(f"Rate limit reached for {action_type}: {daily_limit} per day")
            return False
        
        # Increment counter and allow action
        self._action_counts[action_type] = self._action_counts.get(action_type, 0) + 1
        return True
    
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
            
            logger.info(f"Successfully followed @{username}")
            return True
            
        except TimeoutException:
            logger.warning(f"Follow button not found for @{username}, might already be following")
            return False
        except ElementClickInterceptedException:
            logger.warning(f"Follow button was intercepted for @{username}, possible popup")
            return False
        except Exception as e:
            logger.error(f"Error following @{username}: {e}")
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
            
            logger.info(f"Successfully unfollowed @{username}")
            return True
            
        except TimeoutException:
            logger.warning(f"Unfollow button not found for @{username}, might not be following")
            return False
        except ElementClickInterceptedException:
            logger.warning(f"Unfollow button was intercepted for @{username}, possible popup")
            return False
        except Exception as e:
            logger.error(f"Error unfollowing @{username}: {e}")
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
            
            logger.info(f"Successfully liked post: {post_url}")
            return True
            
        except NoSuchElementException:
            logger.warning(f"Like button not found for {post_url}, post might already be liked")
            return False
        except Exception as e:
            logger.error(f"Error liking post {post_url}: {e}")
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
            
            logger.info(f"Successfully commented on post: {post_url}")
            return True
            
        except Exception as e:
            logger.error(f"Error commenting on post {post_url}: {e}")
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
    
    def close(self) -> None:
        """
        Close the WebDriver and clean up resources.
        """
        try:
            self.driver.quit()
            logger.info("WebDriver closed successfully")
        except Exception as e:
            logger.error(f"Error closing WebDriver: {e}")