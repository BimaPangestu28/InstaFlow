"""
Tests for the utils module.
"""

import os
import time
from unittest.mock import MagicMock, patch

import pytest

from src.bot.utils import (
    random_delay,
    generate_random_comment,
    get_current_timestamp,
    create_directory_if_not_exists,
    username_to_profile_url,
    post_id_to_url,
    hashtag_to_url,
    retry_on_exception
)


class TestUtils:
    """
    Test suite for utils module.
    """
    
    @patch('src.bot.utils.time.sleep')
    @patch('src.bot.utils.random.uniform')
    def test_random_delay(self, mock_uniform, mock_sleep):
        """Test random delay function."""
        # Setup mock returns
        mock_uniform.return_value = 3.5
        
        # Call function with default parameters
        result = random_delay()
        
        # Check results
        assert result == 3.5
        mock_uniform.assert_called_once()
        mock_sleep.assert_called_once_with(3.5)
        
        # Call function with custom parameters
        mock_uniform.reset_mock()
        mock_sleep.reset_mock()
        
        result = random_delay(min_seconds=1.0, max_seconds=2.0)
        
        mock_uniform.assert_called_once_with(1.0, 2.0)
        mock_sleep.assert_called_once_with(3.5)
    
    @patch('src.bot.utils.random.choice')
    def test_generate_random_comment(self, mock_choice):
        """Test random comment generation."""
        # Setup mock to return fixed values
        mock_choice.side_effect = ["Great {emoji}!", "❤️"]
        
        # Call function
        templates = ["Great {emoji}!", "Love this {emoji}", "So {adjective}"]
        variables = {
            'emoji': ['❤️', '🔥', '👍'],
            'adjective': ['cool', 'amazing', 'awesome']
        }
        
        result = generate_random_comment(templates, variables)
        
        # Check results
        assert result == "Great ❤️!"
        assert mock_choice.call_count == 2
    
    def test_get_current_timestamp(self):
        """Test timestamp generation."""
        # Call function
        result = get_current_timestamp()
        
        # Basic check for format (YYYY-MM-DD HH:MM:SS)
        assert len(result) == 19
        assert result[4] == '-' and result[7] == '-'
        assert result[10] == ' '
        assert result[13] == ':' and result[16] == ':'
    
    @patch('src.bot.utils.os.makedirs')
    def test_create_directory_if_not_exists_success(self, mock_makedirs):
        """Test successful directory creation."""
        # Call function
        result = create_directory_if_not_exists('test_dir')
        
        # Check results
        assert result is True
        mock_makedirs.assert_called_once_with('test_dir', exist_ok=True)
    
    @patch('src.bot.utils.os.makedirs')
    def test_create_directory_if_not_exists_failure(self, mock_makedirs):
        """Test failed directory creation."""
        # Setup mock to raise exception
        mock_makedirs.side_effect = PermissionError("Permission denied")
        
        # Call function
        result = create_directory_if_not_exists('test_dir')
        
        # Check results
        assert result is False
        mock_makedirs.assert_called_once_with('test_dir', exist_ok=True)
    
    def test_url_transformations(self):
        """Test URL transformation functions."""
        # Test username to profile URL
        assert username_to_profile_url('test_user') == 'https://www.instagram.com/test_user/'
        
        # Test post ID to URL
        assert post_id_to_url('ABC123') == 'https://www.instagram.com/p/ABC123/'
        
        # Test hashtag to URL
        assert hashtag_to_url('nature') == 'https://www.instagram.com/explore/tags/nature/'
    
    def test_retry_on_exception(self):
        """Test retry decorator."""
        # Create a mock function that fails twice then succeeds
        mock_func = MagicMock()
        mock_func.side_effect = [ValueError("First error"), ValueError("Second error"), "success"]
        
        # Apply decorator
        decorated_func = retry_on_exception(mock_func, max_attempts=3, delay=0.01, exceptions=(ValueError,))
        
        # Call decorated function
        result = decorated_func("arg1", kwarg1="kwarg1")
        
        # Check results
        assert result == "success"
        assert mock_func.call_count == 3
        
        # Test with function that always fails
        mock_func.reset_mock()
        mock_func.side_effect = ValueError("Always fails")
        
        # Should raise exception after all attempts
        with pytest.raises(ValueError, match="Always fails"):
            decorated_func("arg1", kwarg1="kwarg1")
        
        assert mock_func.call_count == 3