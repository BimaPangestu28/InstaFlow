from src import InstagramBot
from src.bot import follow_users_by_hashtag

# Initialize with environment variables
bot = InstagramBot()

# Login to Instagram
if bot.login():
    # Follow a user
    bot.follow_user('target_username')
    
    # Explore a hashtag and get recent posts
    posts = bot.explore_hashtag('photography')
    
    # Follow users from a hashtag
    follow_users_by_hashtag(bot, 'travel', count=5, like_posts=True)
    
    # Remember to close the browser when done
    bot.close()