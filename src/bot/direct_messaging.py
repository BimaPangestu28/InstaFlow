"""
Direct messaging module for Instagram automation.

This module provides functionality for sending, tracking, and automating
direct messages on Instagram.
"""

import logging
import re
import time
import random
import json
import os
from typing import Dict, List, Optional, Tuple, Union
from datetime import datetime, timedelta

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException

from ..config.settings import settings
from .utils import random_delay, get_current_timestamp, create_directory_if_not_exists

# Setup logger
logger = logging.getLogger(__name__)


class MessageTemplate:
    """
    Message template class for creating customizable message templates.
    """
    
    def __init__(self, template: str, variables: Optional[Dict[str, List[str]]] = None):
        """
        Initialize a message template.
        
        Args:
            template: Message template with {variable} placeholders
            variables: Dictionary mapping variable names to possible values
        """
        self.template = template
        self.variables = variables or {}
        
        # Extract all variables needed from the template
        self.required_vars = set(re.findall(r'\{(\w+)\}', template))
    
    def render(self, custom_vars: Optional[Dict[str, str]] = None) -> str:
        """
        Render the template with provided variables.
        
        Args:
            custom_vars: Custom variables to use for this specific rendering
            
        Returns:
            Rendered message with variables substituted
        """
        # Start with a copy of the template
        message = self.template
        
        # Create a dictionary of variables to use
        vars_to_use = {}
        
        # Go through each required variable
        for var_name in self.required_vars:
            # If provided in custom_vars, use that
            if custom_vars and var_name in custom_vars:
                vars_to_use[var_name] = custom_vars[var_name]
            
            # Otherwise, if in predefined variables, choose random value
            elif var_name in self.variables:
                vars_to_use[var_name] = random.choice(self.variables[var_name])
            
            # If not found, use a placeholder
            else:
                vars_to_use[var_name] = f"[{var_name}]"
        
        # Replace all variables in the template
        for var_name, value in vars_to_use.items():
            placeholder = f"{{{var_name}}}"
            message = message.replace(placeholder, value)
        
        return message


class MessageTracker:
    """
    Track and analyze direct message interactions.
    """
    
    def __init__(self, username: str):
        """
        Initialize the message tracker.
        
        Args:
            username: Instagram username to track messages for
        """
        self.username = username
        
        # Ensure directory exists
        self.data_path = os.path.join(
            settings.get('data', 'path', default='data'),
            'messages'
        )
        create_directory_if_not_exists(self.data_path)
        
        # Path to the message data file
        self.file_path = os.path.join(self.data_path, f"{username}_messages.json")
        
        # Load existing data if available
        self.messages = self._load_messages()
    
    def _load_messages(self) -> Dict:
        """
        Load message data from file.
        
        Returns:
            Dictionary containing message data
        """
        try:
            if os.path.exists(self.file_path):
                with open(self.file_path, 'r') as f:
                    return json.load(f)
            else:
                return {
                    'sent': {},
                    'received': {},
                    'metrics': {
                        'total_sent': 0,
                        'total_received': 0,
                        'response_rate': 0.0,
                        'avg_response_time': 0.0
                    }
                }
        except Exception as e:
            logger.error(f"Error loading message data: {e}")
            return {
                'sent': {},
                'received': {},
                'metrics': {
                    'total_sent': 0,
                    'total_received': 0,
                    'response_rate': 0.0,
                    'avg_response_time': 0.0
                }
            }
    
    def _save_messages(self) -> bool:
        """
        Save message data to file.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with open(self.file_path, 'w') as f:
                json.dump(self.messages, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error saving message data: {e}")
            return False
    
    def track_sent_message(self, recipient: str, message: str, template_id: Optional[str] = None) -> None:
        """
        Track a sent message.
        
        Args:
            recipient: Username of message recipient
            message: Message content
            template_id: Optional template ID if a template was used
        """
        timestamp = get_current_timestamp()
        
        # Initialize recipient data if not exists
        if recipient not in self.messages['sent']:
            self.messages['sent'][recipient] = []
        
        # Add the message
        self.messages['sent'][recipient].append({
            'timestamp': timestamp,
            'message': message,
            'template_id': template_id
        })
        
        # Update metrics
        self.messages['metrics']['total_sent'] += 1
        
        # Save changes
        self._save_messages()
        
        logger.debug(f"Tracked sent message to @{recipient}")
    
    def track_received_message(self, sender: str, message: str) -> None:
        """
        Track a received message.
        
        Args:
            sender: Username of message sender
            message: Message content
        """
        timestamp = get_current_timestamp()
        
        # Initialize sender data if not exists
        if sender not in self.messages['received']:
            self.messages['received'][sender] = []
        
        # Add the message
        self.messages['received'][sender].append({
            'timestamp': timestamp,
            'message': message
        })
        
        # Update metrics
        self.messages['metrics']['total_received'] += 1
        
        # If this is a response to our message, update response metrics
        if sender in self.messages['sent']:
            self._update_response_metrics(sender, timestamp)
        
        # Save changes
        self._save_messages()
        
        logger.debug(f"Tracked received message from @{sender}")
    
    def _update_response_metrics(self, username: str, response_timestamp: str) -> None:
        """
        Update response metrics based on a new received message.
        
        Args:
            username: Username who responded
            response_timestamp: Timestamp of the response
        """
        try:
            # Find the latest message we sent to this user
            if username in self.messages['sent'] and len(self.messages['sent'][username]) > 0:
                last_sent = self.messages['sent'][username][-1]
                last_sent_time = datetime.strptime(last_sent['timestamp'], "%Y-%m-%d %H:%M:%S")
                response_time = datetime.strptime(response_timestamp, "%Y-%m-%d %H:%M:%S")
                
                # Calculate response time in hours
                time_diff = (response_time - last_sent_time).total_seconds() / 3600
                
                # Track how many people responded at all
                responding_users = set()
                for user in self.messages['received']:
                    if user in self.messages['sent']:
                        responding_users.add(user)
                
                # Calculate response rate
                total_messaged_users = len(self.messages['sent'])
                response_rate = len(responding_users) / max(1, total_messaged_users)
                
                # Update metrics
                self.messages['metrics']['response_rate'] = response_rate
                
                # Update average response time
                current_avg = self.messages['metrics']['avg_response_time']
                total_responses = len(responding_users)
                
                # Calculate new average
                new_avg = ((current_avg * (total_responses - 1)) + time_diff) / total_responses
                self.messages['metrics']['avg_response_time'] = new_avg
        
        except Exception as e:
            logger.error(f"Error updating response metrics: {e}")
    
    def get_metrics(self) -> Dict:
        """
        Get message interaction metrics.
        
        Returns:
            Dictionary with metrics
        """
        return self.messages['metrics']
    
    def get_sent_messages(self, username: Optional[str] = None) -> List:
        """
        Get sent messages.
        
        Args:
            username: Optional username to filter by
            
        Returns:
            List of sent messages
        """
        if username:
            return self.messages['sent'].get(username, [])
        else:
            # Return all sent messages as a flat list
            all_messages = []
            for user, messages in self.messages['sent'].items():
                for msg in messages:
                    all_messages.append({
                        'recipient': user,
                        'timestamp': msg['timestamp'],
                        'message': msg['message'],
                        'template_id': msg.get('template_id')
                    })
            return all_messages
    
    def get_received_messages(self, username: Optional[str] = None) -> List:
        """
        Get received messages.
        
        Args:
            username: Optional username to filter by
            
        Returns:
            List of received messages
        """
        if username:
            return self.messages['received'].get(username, [])
        else:
            # Return all received messages as a flat list
            all_messages = []
            for user, messages in self.messages['received'].items():
                for msg in messages:
                    all_messages.append({
                        'sender': user,
                        'timestamp': msg['timestamp'],
                        'message': msg['message']
                    })
            return all_messages
    
    def get_users_to_follow_up(self, days_threshold: int = 7) -> List[str]:
        """
        Get users who haven't responded and need follow-up.
        
        Args:
            days_threshold: Minimum days since last message
            
        Returns:
            List of usernames
        """
        users_to_follow_up = []
        current_time = datetime.now()
        
        for username, messages in self.messages['sent'].items():
            # Skip if they've already responded
            if username in self.messages['received']:
                continue
            
            # Check when we last messaged them
            last_message = messages[-1]
            last_time = datetime.strptime(last_message['timestamp'], "%Y-%m-%d %H:%M:%S")
            
            # Calculate days since
            days_since = (current_time - last_time).days
            
            # If it's been longer than the threshold, add to follow-up list
            if days_since >= days_threshold:
                users_to_follow_up.append(username)
        
        return users_to_follow_up


class DirectMessaging:
    """
    Direct messaging functionality for Instagram.
    """
    
    def __init__(self, bot):
        """
        Initialize direct messaging functionality.
        
        Args:
            bot: InstagramBot instance
        """
        self.bot = bot
        self.tracker = MessageTracker(bot.username)
        
        # Load message templates
        self.templates = self._load_templates()
    
    def _load_templates(self) -> Dict[str, MessageTemplate]:
        """
        Load message templates from configuration.
        
        Returns:
            Dictionary mapping template IDs to MessageTemplate objects
        """
        templates = {}
        
        # Load templates from settings
        config_templates = settings.get('messages', 'templates', default={})
        
        for template_id, template_data in config_templates.items():
            if isinstance(template_data, dict) and 'text' in template_data:
                templates[template_id] = MessageTemplate(
                    template_data['text'],
                    template_data.get('variables', {})
                )
            elif isinstance(template_data, str):
                templates[template_id] = MessageTemplate(template_data)
        
        # Add default templates if none exist
        if not templates:
            templates['welcome'] = MessageTemplate(
                "Hi {name}! Thanks for connecting. I appreciate your support!",
                {'name': ['{name}']}
            )
            
            templates['follow_up'] = MessageTemplate(
                "Hey {name}, just checking in! Hope you're having a great day.",
                {'name': ['{name}']}
            )
        
        return templates
    
    def send_message(self, username: str, message: str, track: bool = True) -> bool:
        """
        Send a direct message to a user.
        
        Args:
            username: Username to send message to
            message: Message text to send
            track: Whether to track this message
            
        Returns:
            bool: True if successful, False otherwise
        """
        result = self.bot.send_direct_message(username, message)
        
        if result and track:
            self.tracker.track_sent_message(username, message)
        
        return result
    
    def send_template_message(self, username: str, template_id: str, 
                             variables: Optional[Dict[str, str]] = None) -> bool:
        """
        Send a templated message to a user.
        
        Args:
            username: Username to send message to
            template_id: ID of template to use
            variables: Custom variables for the template
            
        Returns:
            bool: True if successful, False otherwise
        """
        if template_id not in self.templates:
            logger.error(f"Template {template_id} not found")
            return False
        
        # If username is provided in variables, use it as {name} if not explicitly provided
        if variables and 'username' in variables and 'name' not in variables:
            variables['name'] = variables['username']
        
        # If no name is provided, use the username
        if not variables:
            variables = {'name': username}
        elif 'name' not in variables:
            variables['name'] = username
        
        # Render the template
        message = self.templates[template_id].render(variables)
        
        # Send the message
        result = self.bot.send_direct_message(username, message)
        
        if result:
            self.tracker.track_sent_message(username, message, template_id)
        
        return result
    
    def send_welcome_message(self, username: str) -> bool:
        """
        Send a welcome message to a new follower.
        
        Args:
            username: Username of new follower
            
        Returns:
            bool: True if successful, False otherwise
        """
        # Check if we've messaged this user before
        if username in self.tracker.get_sent_messages():
            logger.debug(f"Already messaged @{username} before, skipping welcome message")
            return False
        
        return self.send_template_message(username, 'welcome', {'name': username})
    
    def send_follow_up_messages(self, days_threshold: int = 7) -> Dict[str, int]:
        """
        Send follow-up messages to users who haven't responded.
        
        Args:
            days_threshold: Minimum days since last message
            
        Returns:
            Dict with results (total, success, failed)
        """
        results = {'total': 0, 'success': 0, 'failed': 0}
        
        # Get users to follow up with
        users = self.tracker.get_users_to_follow_up(days_threshold)
        
        results['total'] = len(users)
        
        for username in users:
            if self.send_template_message(username, 'follow_up'):
                results['success'] += 1
            else:
                results['failed'] += 1
            
            # Add delay between messages
            random_delay(min_seconds=30, max_seconds=60)
        
        return results
    
    def check_new_messages(self) -> int:
        """
        Check for new direct messages and track them.
        
        Returns:
            int: Number of new messages found
        """
        new_messages_count = 0
        
        try:
            # Navigate to direct messages
            self.bot.driver.get(f"{self.bot.base_url}/direct/inbox/")
            
            # Wait for inbox to load
            self.bot.wait.until(
                EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'inbox')]"))
            )
            
            # Find conversation elements
            conversations = self.bot.driver.find_elements(
                By.XPATH,
                "//div[contains(@class, 'conversation-item')]"
            )
            
            # Look for unread indicators
            for convo in conversations:
                try:
                    # Check for unread indicator
                    unread = convo.find_element(By.XPATH, ".//div[contains(@class, 'unread')]")
                    
                    # If found, click on the conversation
                    convo.click()
                    
                    # Wait for conversation to load
                    self.bot.wait.until(
                        EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'message-thread')]"))
                    )
                    
                    # Get the username
                    username_element = self.bot.driver.find_element(
                        By.XPATH,
                        "//header//div[contains(@class, 'username')]"
                    )
                    username = username_element.text.strip()
                    
                    # Find new messages
                    messages = self.bot.driver.find_elements(
                        By.XPATH,
                        "//div[contains(@class, 'message-item') and not(contains(@class, 'outgoing'))]"
                    )
                    
                    # Track each message
                    for message in messages[-3:]:  # Only process the last few messages for efficiency
                        try:
                            # Get message text
                            message_text = message.find_element(By.XPATH, ".//div[contains(@class, 'message-text')]").text
                            
                            # Get timestamp if available
                            try:
                                timestamp = message.find_element(By.XPATH, ".//time").get_attribute('datetime')
                            except NoSuchElementException:
                                timestamp = get_current_timestamp()
                            
                            # Track the message
                            self.tracker.track_received_message(username, message_text)
                            new_messages_count += 1
                            
                        except Exception as e:
                            logger.error(f"Error processing message: {e}")
                    
                    # Add delay before next conversation
                    random_delay(min_seconds=1, max_seconds=3)
                    
                except NoSuchElementException:
                    # No unread indicator, skip
                    continue
            
            return new_messages_count
            
        except Exception as e:
            logger.error(f"Error checking new messages: {e}")
            return 0
    
    def get_message_analytics(self) -> Dict:
        """
        Get analytics on messaging performance.
        
        Returns:
            Dictionary with messaging metrics and analytics
        """
        metrics = self.tracker.get_metrics()
        
        # Add additional analytics
        analytics = {
            'metrics': metrics,
            'top_responders': self._get_top_responders(),
            'best_templates': self._get_best_performing_templates(),
            'response_times': {
                'avg_hours': metrics['avg_response_time'],
                'avg_days': metrics['avg_response_time'] / 24,
                'within_day': self._get_percentage_responses_within(24)
            }
        }
        
        return analytics
    
    def _get_top_responders(self, limit: int = 5) -> List[Dict]:
        """
        Get users who respond most frequently.
        
        Args:
            limit: Maximum number of users to return
            
        Returns:
            List of dictionaries with username and response count
        """
        responders = {}
        
        # Count messages for each user
        for username, messages in self.tracker.messages['received'].items():
            responders[username] = len(messages)
        
        # Sort by count
        sorted_responders = sorted(responders.items(), key=lambda x: x[1], reverse=True)
        
        # Format as list of dictionaries
        return [{'username': username, 'responses': count} 
                for username, count in sorted_responders[:limit]]
    
    def _get_best_performing_templates(self, limit: int = 3) -> List[Dict]:
        """
        Get templates with highest response rates.
        
        Args:
            limit: Maximum number of templates to return
            
        Returns:
            List of dictionaries with template ID and response rate
        """
        template_stats = {}
        
        # Get all sent messages
        sent_messages = self.tracker.get_sent_messages()
        
        # Group by template
        for message in sent_messages:
            template_id = message.get('template_id')
            if not template_id:
                continue
                
            if template_id not in template_stats:
                template_stats[template_id] = {
                    'sent': 0,
                    'responses': 0
                }
            
            template_stats[template_id]['sent'] += 1
            
            # Check if recipient responded
            recipient = message['recipient']
            if recipient in self.tracker.messages['received']:
                template_stats[template_id]['responses'] += 1
        
        # Calculate response rates
        results = []
        for template_id, stats in template_stats.items():
            if stats['sent'] > 0:
                response_rate = stats['responses'] / stats['sent']
                results.append({
                    'template_id': template_id,
                    'sent': stats['sent'],
                    'responses': stats['responses'],
                    'response_rate': response_rate
                })
        
        # Sort by response rate
        sorted_results = sorted(results, key=lambda x: x['response_rate'], reverse=True)
        
        return sorted_results[:limit]
    
    def _get_percentage_responses_within(self, hours: int) -> float:
        """
        Get percentage of responses received within specified time.
        
        Args:
            hours: Number of hours threshold
            
        Returns:
            Percentage of responses within time threshold
        """
        total_responses = 0
        responses_within_time = 0
        
        # Process each recipient who responded
        for username, received_messages in self.tracker.messages['received'].items():
            if username not in self.tracker.messages['sent']:
                continue
                
            sent_messages = self.tracker.messages['sent'][username]
            
            for received_msg in received_messages:
                received_time = datetime.strptime(received_msg['timestamp'], "%Y-%m-%d %H:%M:%S")
                
                # Find the most recent sent message before this response
                prev_sent_msg = None
                for sent_msg in reversed(sent_messages):
                    sent_time = datetime.strptime(sent_msg['timestamp'], "%Y-%m-%d %H:%M:%S")
                    if sent_time < received_time:
                        prev_sent_msg = sent_msg
                        break
                
                if prev_sent_msg:
                    total_responses += 1
                    sent_time = datetime.strptime(prev_sent_msg['timestamp'], "%Y-%m-%d %H:%M:%S")
                    time_diff = (received_time - sent_time).total_seconds() / 3600
                    
                    if time_diff <= hours:
                        responses_within_time += 1
        
        if total_responses == 0:
            return 0.0
            
        return (responses_within_time / total_responses) * 100