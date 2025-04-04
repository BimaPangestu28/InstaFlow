"""
Tests for the InstagramBot class.
"""

import os
import pytest
from unittest.mock import MagicMock, patch

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from src.bot.instagram import InstagramBot


@pytest.fixture
def mock_driver():
    """
    Fixture to create a mock WebDriver.
    """
    mock = MagicMock()
    mock.find_element.return_value = MagicMock()
    mock.find_elements.return_value = []
    return mock


@pytest.fixture
def mock_wait():
    """
    Fixture to create a mock WebDriverWait.
    """
    mock = MagicMock()
    mock.until.return_value = MagicMock()
    return mock


@pytest.fixture
def bot(mock_driver, mock_wait):
    """
    Fixture to create an InstagramBot with mocked dependencies.
    """
    with patch('src.bot.instagram.webdriver.Chrome', return_value=mock_driver), \
         patch('src.bot.instagram.WebDriverWait', return_value=mock_wait), \
         patch.dict(os.environ, {'INSTAGRAM_USERNAME': 'test_user', 'INSTAGRAM_PASSWORD': 'test_pass'}):
        
        bot = InstagramBot()
        bot.driver = mock_driver
        bot.wait = mock_wait
        return bot


class TestInstagramBot:
    """
    Test suite for InstagramBot class.
    """
    
    def test_init(self, bot):
        """Test bot initialization."""
        assert bot.username == 'test_user'
        assert bot.password == 'test_pass'
        assert bot.base_url == 'https://www.instagram.com'
    
    def test_login_with_cookies_success(self, bot, mock_driver):
        """Test successful login with cookies."""
        # Mock _load_cookies to return True
        bot._load_cookies = MagicMock(return_value=True)
        # Mock _check_login_status to return True
        bot._check_login_status = MagicMock(return_value=True)
        
        result = bot.login()
        
        assert result is True
        bot._load_cookies.assert_called_once()
        bot._check_login_status.assert_called_once()
    
    def test_login_with_credentials_success(self, bot, mock_driver, mock_wait):
        """Test successful login with username and password."""
        # Mock _load_cookies to return False
        bot._load_cookies = MagicMock(return_value=False)
        # Mock _save_cookies to return True
        bot._save_cookies = MagicMock(return_value=True)
        # Mock _handle_save_login_prompt
        bot._handle_save_login_prompt = MagicMock()
        # Mock _handle_notifications_prompt
        bot._handle_notifications_prompt = MagicMock()
        
        # Set up the mocks to simulate successful login flow
        username_input = MagicMock()
        password_input = MagicMock()
        mock_wait.until.return_value = username_input
        mock_driver.find_element.return_value = password_input
        
        result = bot.login()
        
        assert result is True
        bot._load_cookies.assert_called_once()
        bot._save_cookies.assert_called_once()
        bot._handle_save_login_prompt.assert_called_once()
        bot._handle_notifications_prompt.assert_called_once()
    
    def test_follow_user_success(self, bot, mock_driver, mock_wait):
        """Test successfully following a user."""
        # Set up mocks
        follow_button = MagicMock()
        mock_wait.until.return_value = follow_button
        
        # Mock _check_rate_limit to return True
        bot._check_rate_limit = MagicMock(return_value=True)
        
        result = bot.follow_user('test_target')
        
        assert result is True
        mock_driver.get.assert_called_with('https://www.instagram.com/test_target/')
        follow_button.click.assert_called_once()
        bot._check_rate_limit.assert_called_once_with('follows')
    
    def test_follow_user_rate_limited(self, bot):
        """Test follow user when rate limited."""
        # Mock _check_rate_limit to return False
        bot._check_rate_limit = MagicMock(return_value=False)
        
        result = bot.follow_user('test_target')
        
        assert result is False
        bot._check_rate_limit.assert_called_once_with('follows')
    
    def test_explore_hashtag(self, bot, mock_driver, mock_wait):
        """Test exploring a hashtag."""
        # Set up mocks
        post_link1 = MagicMock()
        post_link1.get_attribute.return_value = 'https://www.instagram.com/p/123456/'
        post_link2 = MagicMock()
        post_link2.get_attribute.return_value = 'https://www.instagram.com/p/789012/'
        
        mock_driver.find_elements.return_value = [post_link1, post_link2]
        
        result = bot.explore_hashtag('test')
        
        assert len(result) == 2
        assert result[0] == 'https://www.instagram.com/p/123456/'
        assert result[1] == 'https://www.instagram.com/p/789012/'
        mock_driver.get.assert_called_with('https://www.instagram.com/explore/tags/test/')