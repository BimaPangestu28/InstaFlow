"""
Tests for the actions module.
"""

import pytest
from unittest.mock import MagicMock, patch

from src.bot.actions import (
    follow_users_by_hashtag,
    engage_with_followers,
    unfollow_non_followers
)


@pytest.fixture
def mock_bot():
    """
    Fixture to create a mock InstagramBot.
    """
    bot = MagicMock()
    bot.username = 'test_user'
    bot.driver = MagicMock()
    bot.wait = MagicMock()
    return bot


class TestActions:
    """
    Test suite for actions module.
    """
    
    @patch('src.bot.actions.random_delay')
    def test_follow_users_by_hashtag(self, mock_delay, mock_bot):
        """Test following users by hashtag."""
        # Setup mock returns
        mock_bot.explore_hashtag.return_value = [
            'https://www.instagram.com/p/123456/',
            'https://www.instagram.com/p/789012/'
        ]
        
        # Setup username_element mock
        username_element = MagicMock()
        username_element.get_attribute.return_value = 'https://www.instagram.com/test_target/'
        mock_bot.wait.until.return_value = username_element
        
        # Set successful actions
        mock_bot.like_post.return_value = True
        mock_bot.follow_user.return_value = True
        
        # Call function
        results = follow_users_by_hashtag(
            mock_bot,
            'test',
            count=2,
            like_posts=True,
            comment=False
        )
        
        # Check results
        assert results['follows'] == 2
        assert results['likes'] == 2
        assert results['comments'] == 0
        assert results['errors'] == 0
        
        # Verify method calls
        mock_bot.explore_hashtag.assert_called_once_with('test', 4)
        assert mock_bot.like_post.call_count == 2
        assert mock_bot.follow_user.call_count == 2
    
    @patch('src.bot.actions.random_delay')
    def test_engage_with_followers(self, mock_delay, mock_bot):
        """Test engaging with followers."""
        # Setup mock returns
        mock_bot.get_user_followers.return_value = ['follower1', 'follower2']
        
        # Setup post links mock
        post_link1 = MagicMock()
        post_link1.get_attribute.return_value = 'https://www.instagram.com/p/123456/'
        post_link2 = MagicMock()
        post_link2.get_attribute.return_value = 'https://www.instagram.com/p/789012/'
        mock_bot.driver.find_elements.return_value = [post_link1, post_link2]
        
        # Set successful actions
        mock_bot.like_post.return_value = True
        
        # Call function
        results = engage_with_followers(
            mock_bot,
            count=2,
            like_count=2,
            comment=False
        )
        
        # Check results
        assert results['followers_engaged'] == 2
        assert results['likes'] == 4  # 2 followers x 2 posts
        assert results['comments'] == 0
        assert results['errors'] == 0
        
        # Verify method calls
        mock_bot.get_user_followers.assert_called_once_with('test_user', max_count=4)
        assert mock_bot.driver.get.call_count == 2  # One call per follower
        assert mock_bot.like_post.call_count == 4  # 2 followers x 2 posts
    
    @patch('src.bot.actions.random_delay')
    def test_unfollow_non_followers(self, mock_delay, mock_bot):
        """Test unfollowing non-followers."""
        # Setup mock returns for followers and following
        mock_bot.get_user_followers.return_value = ['follower1', 'mutual_follow']
        
        # Setup following elements mock
        following_link = MagicMock()
        following_dialog = MagicMock()
        following_element1 = MagicMock()
        following_element1.get_attribute.return_value = 'https://www.instagram.com/mutual_follow/'
        following_element2 = MagicMock()
        following_element2.get_attribute.return_value = 'https://www.instagram.com/following_only/'
        
        mock_bot.wait.until.side_effect = [following_link, following_dialog]
        following_dialog.find_elements.return_value = [following_element1, following_element2]
        
        # Set successful actions
        mock_bot.unfollow_user.return_value = True
        
        # Call function with whitelist
        results = unfollow_non_followers(
            mock_bot,
            count=1,
            days_threshold=7,
            whitelist=['whitelisted_user']
        )
        
        # Check results
        assert results['unfollows'] == 1
        assert results['skipped_whitelist'] == 0
        assert results['errors'] == 0
        
        # Verify method calls
        mock_bot.get_user_followers.assert_called_once_with('test_user', max_count=1000)
        following_link.click.assert_called_once()
        assert mock_bot.unfollow_user.call_count == 1