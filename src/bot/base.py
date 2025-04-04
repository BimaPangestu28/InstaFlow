"""
Base bot module providing the foundation for all automation bots.

This module contains the BaseBotClass that handles common functionality across bots.
"""

import logging
import os
import pickle
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple, Union

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

from ..config.settings import settings
from .utils import random_delay, create_directory_if_not_exists

# Setup logger
logger = logging.getLogger(__name__)


class BaseBot(ABC):
    """
    Base class for social media automation bots.
    
    This abstract class provides common functionality for browser automation,
    including WebDriver setup, cookie management, and rate limiting.
    """
    
    def __init__(self, username: Optional[str] = None, password: Optional[str] = None):
        """
        Initialize the base bot with given credentials.
        
        Args:
            username: Account username (defaults to environment variable)
            password: Account password (defaults to environment variable)
        """
        self.username = username
        self.password = password
        
        # Base paths and URLs to be defined by child classes
        self.base_url = ""
        self.cookies_path = ""
        
        # Action counters for rate limiting
        self._action_counts = {}
        self._last_actions = {}
        
        # Emergency stop indicators
        self._block_warning_count = 0
        self._action_success_rate = 1.0  # Start at 100%
        self._is_emergency_mode = False
        
        # Configure webdriver
        self.driver = self._setup_driver()
        self.wait = WebDriverWait(
            self.driver, 
            settings.get('bot', 'wait_timeout', default=10)
        )
    
    def __enter__(self) -> 'BaseBot':
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
            
            # Navigate to domain first (cookies domain must match)
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
    
    def _check_rate_limit(self, action_type: str) -> bool:
        """
        Check if an action would exceed rate limits.
        
        Args:
            action_type: Type of action to check
            
        Returns:
            bool: True if action is allowed, False if rate limit would be exceeded
        """
        # Check emergency mode first
        if self._is_emergency_mode:
            logger.warning(f"Emergency mode active. Action {action_type} rejected.")
            return False
            
        # Get daily limit for this action type
        daily_limit = settings.get('actions', 'daily_limits', action_type, default=0)
        
        # Check if we've reached the limit
        if self._action_counts.get(action_type, 0) >= daily_limit:
            logger.warning(f"Rate limit reached for {action_type}: {daily_limit} per day")
            return False
        
        # Increment counter and allow action
        self._action_counts[action_type] = self._action_counts.get(action_type, 0) + 1
        
        # Record timestamp for this action
        if action_type not in self._last_actions:
            self._last_actions[action_type] = []
            
        self._last_actions[action_type].append(time.time())
        
        # Remove old timestamps (older than 24 hours)
        day_ago = time.time() - (24 * 60 * 60)
        self._last_actions[action_type] = [
            t for t in self._last_actions[action_type] if t > day_ago
        ]
        
        return True
    
    def _update_success_rate(self, action_type: str, success: bool) -> None:
        """
        Update the success rate tracking for a specific action type.
        
        Args:
            action_type: Type of action performed
            success: Whether the action was successful
        """
        # Get current stats
        action_stats = settings.get('stats', 'actions', action_type, default={})
        attempts = action_stats.get('attempts', 0) + 1
        successes = action_stats.get('successes', 0) + (1 if success else 0)
        
        # Calculate success rate
        success_rate = successes / max(1, attempts)
        
        # Update stats
        action_stats['attempts'] = attempts
        action_stats['successes'] = successes
        action_stats['success_rate'] = success_rate
        
        # Check for emergency conditions
        if not success:
            self._block_warning_count += 1
            
            # Calculate overall success rate (weighted recent actions more heavily)
            self._action_success_rate = 0.7 * self._action_success_rate + 0.3 * (1.0 if success else 0.0)
            
            # Check emergency thresholds
            emergency_threshold = settings.get('safety', 'emergency_threshold', default=0.6)
            warning_limit = settings.get('safety', 'warning_limit', default=5)
            
            if (self._block_warning_count >= warning_limit or 
                self._action_success_rate < emergency_threshold):
                self._activate_emergency_mode()
    
    def _activate_emergency_mode(self) -> None:
        """
        Activate emergency mode to prevent account issues.
        """
        self._is_emergency_mode = True
        logger.critical(
            f"EMERGENCY MODE ACTIVATED - Too many failed actions detected. "
            f"Block warnings: {self._block_warning_count}, "
            f"Success rate: {self._action_success_rate:.2f}"
        )
        
        # Send notification if configured
        self._send_emergency_notification()
    
    def _send_emergency_notification(self) -> None:
        """
        Send emergency notification to admin.
        """
        email = settings.get('notifications', 'admin_email')
        if email:
            logger.info(f"Would send emergency notification to {email}")
            # In real implementation, send actual email/notification
    
    @abstractmethod
    def login(self) -> bool:
        """
        Log in to the service.
        
        Returns:
            bool: True if login successful, False otherwise
        """
        pass
    
    def close(self) -> None:
        """
        Close the WebDriver and clean up resources.
        """
        try:
            self.driver.quit()
            logger.info("WebDriver closed successfully")
        except Exception as e:
            logger.error(f"Error closing WebDriver: {e}")