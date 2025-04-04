# InstaFlow

A powerful, feature-rich Instagram automation library for Python.

![PyPI version](https://img.shields.io/badge/version-0.1.0-blue)
![Python versions](https://img.shields.io/badge/python-3.8%20%7C%203.9%20%7C%203.10-blue)
![License](https://img.shields.io/badge/license-MIT-green)

## Overview

InstaFlow is a robust Instagram automation tool designed to help Instagram users grow their accounts organically through smart, configurable automation processes. It provides a complete set of tools for account management, engagement, and growth while focusing on safety and mimicking human behavior to avoid detection.

## Features

- **Account Management**: Secure cookie-based authentication with encryption
- **User Interaction**: Follow, unfollow, and engage with users based on various targeting criteria
- **Content Engagement**: Like, comment, and view stories with configurable rate limits
- **Hashtag & Location Targeting**: Find and engage with users based on hashtags and locations
- **Follower Management**: Track followers/following, unfollow non-followers, and maintain whitelists
- **Safety First**: Built-in rate limits and human-like behavior patterns
- **CLI Interface**: Complete command-line interface for easy automation
- **Customizable**: Extensive configuration options for all aspects of automation
- **Well-Documented**: Comprehensive documentation with examples

## Installation

```bash
# Install from PyPI
pip install instaflow

# Development installation
git clone https://github.com/BimaPangestu28/InstaFlow.git
cd InstaFlow
pip install -e .
```

## Quick Start

### Basic Usage

```python
from instaflow import InstagramBot

# Initialize with environment variables INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD
bot = InstagramBot()

# Login to Instagram
if bot.login():
    # Follow a user
    bot.follow_user('target_username')
    
    # Like a post
    bot.like_post('https://www.instagram.com/p/ABC123/')
    
    # Explore a hashtag and get recent posts
    posts = bot.explore_hashtag('photography')
    
    # Remember to close the browser when done
    bot.close()
```

### Using the CLI

```bash
# Run daily engagement routine
instaflow daily --hashtags "photography,nature,travel" --follow 20 --unfollow 15

# Follow users based on a hashtag
instaflow follow photography --count 10 --like

# Engage with existing followers
instaflow engage --count 15 --likes 3 --comment

# Unfollow users who don't follow back
instaflow unfollow --count 20 --days 7 --whitelist "friend1,friend2"
```

## Configuration

InstaFlow can be configured through:

1. Default configuration file: `config/default.json`
2. Custom configuration file: Specified with `--config` option
3. Environment variables: Override settings from config files

Example `.env` file:

```
INSTAGRAM_USERNAME=your_username
INSTAGRAM_PASSWORD=your_password
COOKIE_ENCRYPTION_KEY=your_secure_key

# Optional overrides
CONFIG_HEADLESS=true
CONFIG_LOG_LEVEL=INFO
```

## Advanced Features

### Running a Complete Growth Campaign

```python
from instaflow.bot import run_daily_engagement_routine

with InstagramBot() as bot:
    if bot.login():
        # Run a complete daily routine with balanced actions
        results = run_daily_engagement_routine(
            bot,
            hashtags=['photography', 'travel', 'nature'],
            follow_count=20,
            unfollow_count=15,
            like_count=50
        )
        
        print(f"Campaign results: {results}")
```

### Custom Comment Templates

```python
from instaflow.bot import follow_users_by_hashtag

with InstagramBot() as bot:
    if bot.login():
        results = follow_users_by_hashtag(
            bot,
            'photography',
            count=10,
            like_posts=True,
            comment=True,
            comment_templates=[
                "Great shot! {emoji}",
                "Love the {adjective} composition {emoji}",
                "The lighting is {adjective}! {emoji}"
            ]
        )
```

## Safety and Best Practices

- Start with low limits and gradually increase them
- Use realistic delays between actions (already built into InstaFlow)
- Avoid running automation 24/7
- Don't use multiple automation tools at the same time
- Rotate between different actions to appear natural
- Always respect Instagram's terms of service

## Development

### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/BimaPangestu28/InstaFlow.git
cd InstaFlow

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -r requirements-dev.txt

# Install the package in development mode
pip install -e .
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=src tests/
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This tool is for educational purposes only. Automation of Instagram actions may violate Instagram's terms of service. Use at your own risk.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Contact

- GitHub: [https://github.com/BimaPangestu28/InstaFlow](https://github.com/BimaPangestu28/InstaFlow)
- Website: [https://instaflow.catalystlabs.id](https://instaflow.catalystlabs.id)