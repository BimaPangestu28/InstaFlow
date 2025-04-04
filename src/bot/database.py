"""
Database module for tracking Instagram automation actions and metrics.

This module provides functionality for recording actions, tracking growth,
calculating engagement metrics, and exporting analytics data.
"""

import logging
import json
import os
import csv
from typing import Dict, List, Optional, Tuple, Union, Any
from datetime import datetime, timedelta
import sqlite3

from ..config.settings import settings
from .utils import create_directory_if_not_exists, get_current_timestamp

# Setup logger
logger = logging.getLogger(__name__)


class ActionDatabase:
    """
    Database for tracking Instagram automation actions and metrics.
    """
    
    def __init__(self, username: str):
        """
        Initialize the action database.
        
        Args:
            username: Instagram username to track actions for
        """
        self.username = username
        
        # Ensure data directory exists
        self.data_path = os.path.join(
            settings.get('data', 'path', default='data'),
            'db'
        )
        create_directory_if_not_exists(self.data_path)
        
        # Database file path
        self.db_path = os.path.join(self.data_path, f"{username}.db")
        
        # Initialize database
        self._initialize_database()
    
    def _initialize_database(self) -> None:
        """
        Initialize the SQLite database and create tables if they don't exist.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create actions table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                action_type TEXT NOT NULL,
                target_username TEXT,
                target_url TEXT,
                status TEXT NOT NULL,
                details TEXT
            )
            ''')
            
            # Create followers table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS followers (
                username TEXT PRIMARY KEY,
                first_seen TEXT NOT NULL,
                status TEXT NOT NULL,
                followed_by_us INTEGER DEFAULT 0,
                we_follow INTEGER DEFAULT 0,
                last_updated TEXT NOT NULL
            )
            ''')
            
            # Create metrics table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS metrics (
                date TEXT PRIMARY KEY,
                followers_count INTEGER DEFAULT 0,
                following_count INTEGER DEFAULT 0,
                likes_received INTEGER DEFAULT 0,
                comments_received INTEGER DEFAULT 0,
                engagement_rate REAL DEFAULT 0,
                growth_rate REAL DEFAULT 0
            )
            ''')
            
            # Commit changes
            conn.commit()
            
            # Create indexes for performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_actions_timestamp ON actions (timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_actions_type ON actions (action_type)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_actions_target ON actions (target_username)')
            
            conn.commit()
            conn.close()
            
            logger.debug(f"Database initialized for @{self.username}")
            
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
    
    def record_action(
        self, 
        action_type: str, 
        status: str, 
        target_username: Optional[str] = None,
        target_url: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Record an action in the database.
        
        Args:
            action_type: Type of action (follow, unfollow, like, comment, etc.)
            status: Status of the action (success, failed, etc.)
            target_username: Optional username the action was performed on
            target_url: Optional URL the action was performed on
            details: Optional dictionary with additional details
            
        Returns:
            int: ID of the inserted record, or -1 on failure
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Convert details to JSON if provided
            details_json = json.dumps(details) if details else None
            
            # Get current timestamp
            timestamp = get_current_timestamp()
            
            # Insert action record
            cursor.execute(
                '''
                INSERT INTO actions 
                (timestamp, action_type, target_username, target_url, status, details)
                VALUES (?, ?, ?, ?, ?, ?)
                ''',
                (timestamp, action_type, target_username, target_url, status, details_json)
            )
            
            # Get the ID of the inserted record
            action_id = cursor.lastrowid
            
            # Commit and close
            conn.commit()
            conn.close()
            
            logger.debug(f"Recorded {action_type} action with status {status}")
            
            return action_id
            
        except Exception as e:
            logger.error(f"Error recording action: {e}")
            return -1
    
    def update_follower(
        self, 
        username: str, 
        we_follow: bool,
        followed_by_us: bool
    ) -> bool:
        """
        Update follower status in the database.
        
        Args:
            username: Instagram username
            we_follow: Whether we are following them
            followed_by_us: Whether they follow us
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get current timestamp
            timestamp = get_current_timestamp()
            
            # Check if user exists
            cursor.execute(
                'SELECT username FROM followers WHERE username = ?',
                (username,)
            )
            
            exists = cursor.fetchone()
            
            if exists:
                # Update existing record
                cursor.execute(
                    '''
                    UPDATE followers
                    SET we_follow = ?, followed_by_us = ?, last_updated = ?,
                        status = CASE
                            WHEN ? = 1 AND ? = 1 THEN 'mutual'
                            WHEN ? = 1 AND ? = 0 THEN 'following_only'
                            WHEN ? = 0 AND ? = 1 THEN 'follower_only'
                            ELSE 'none'
                        END
                    WHERE username = ?
                    ''',
                    (
                        1 if we_follow else 0,
                        1 if followed_by_us else 0,
                        timestamp,
                        we_follow, followed_by_us,
                        we_follow, followed_by_us,
                        we_follow, followed_by_us,
                        username
                    )
                )
            else:
                # Determine status
                if we_follow and followed_by_us:
                    status = 'mutual'
                elif we_follow:
                    status = 'following_only'
                elif followed_by_us:
                    status = 'follower_only'
                else:
                    status = 'none'
                
                # Insert new record
                cursor.execute(
                    '''
                    INSERT INTO followers
                    (username, first_seen, status, we_follow, followed_by_us, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ''',
                    (
                        username,
                        timestamp,
                        status,
                        1 if we_follow else 0,
                        1 if followed_by_us else 0,
                        timestamp
                    )
                )
            
            # Commit and close
            conn.commit()
            conn.close()
            
            logger.debug(f"Updated follower status for @{username}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating follower: {e}")
            return False
    
    def update_daily_metrics(
        self,
        followers_count: int,
        following_count: int,
        likes_received: Optional[int] = None,
        comments_received: Optional[int] = None
    ) -> bool:
        """
        Update daily metrics in the database.
        
        Args:
            followers_count: Current follower count
            following_count: Current following count
            likes_received: Optional number of likes received today
            comments_received: Optional number of comments received today
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get current date (just the date part, not time)
            today = datetime.now().strftime("%Y-%m-%d")
            
            # Calculate engagement and growth rates
            engagement_rate = 0.0
            growth_rate = 0.0
            
            # Get previous metrics for calculating rates
            yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
            cursor.execute(
                'SELECT followers_count, engagement_rate FROM metrics WHERE date = ?',
                (yesterday,)
            )
            
            prev_metrics = cursor.fetchone()
            
            if prev_metrics:
                prev_followers, prev_engagement = prev_metrics
                
                # Calculate growth rate
                if prev_followers > 0:
                    growth_rate = ((followers_count - prev_followers) / prev_followers) * 100
                
                # Use previous engagement rate if we don't have new data
                if likes_received is None or comments_received is None:
                    engagement_rate = prev_engagement
            
            # Calculate engagement rate if we have the data
            if likes_received is not None and comments_received is not None and followers_count > 0:
                engagement_rate = ((likes_received + (comments_received * 2)) / followers_count) * 100
            
            # Check if we already have an entry for today
            cursor.execute(
                'SELECT date FROM metrics WHERE date = ?',
                (today,)
            )
            
            exists = cursor.fetchone()
            
            if exists:
                # Update existing record
                if likes_received is not None and comments_received is not None:
                    # Update with all fields
                    cursor.execute(
                        '''
                        UPDATE metrics
                        SET followers_count = ?, following_count = ?, 
                            likes_received = ?, comments_received = ?,
                            engagement_rate = ?, growth_rate = ?
                        WHERE date = ?
                        ''',
                        (
                            followers_count,
                            following_count,
                            likes_received,
                            comments_received,
                            engagement_rate,
                            growth_rate,
                            today
                        )
                    )
                else:
                    # Only update follower and following counts
                    cursor.execute(
                        '''
                        UPDATE metrics
                        SET followers_count = ?, following_count = ?, growth_rate = ?
                        WHERE date = ?
                        ''',
                        (
                            followers_count,
                            following_count,
                            growth_rate,
                            today
                        )
                    )
            else:
                # Insert new record
                cursor.execute(
                    '''
                    INSERT INTO metrics
                    (date, followers_count, following_count, likes_received, comments_received, 
                     engagement_rate, growth_rate)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''',
                    (
                        today,
                        followers_count,
                        following_count,
                        likes_received or 0,
                        comments_received or 0,
                        engagement_rate,
                        growth_rate
                    )
                )
            
            # Commit and close
            conn.commit()
            conn.close()
            
            logger.debug(f"Updated daily metrics for {today}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating daily metrics: {e}")
            return False
    
    def get_action_stats(
        self,
        action_type: Optional[str] = None,
        days: int = 30,
        include_details: bool = False
    ) -> List[Dict]:
        """
        Get statistics on actions performed.
        
        Args:
            action_type: Optional action type to filter by
            days: Number of days to look back
            include_details: Whether to include full details
            
        Returns:
            List of action records
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Return rows as dictionaries
            cursor = conn.cursor()
            
            # Calculate date cutoff
            cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
            
            # Build query
            query = '''
            SELECT id, timestamp, action_type, target_username, target_url, status
            FROM actions
            WHERE timestamp >= ?
            '''
            params = [cutoff_date]
            
            if action_type:
                query += ' AND action_type = ?'
                params.append(action_type)
            
            query += ' ORDER BY timestamp DESC'
            
            # Add details if requested
            if include_details:
                query = query.replace('status', 'status, details')
            
            # Execute query
            cursor.execute(query, params)
            
            # Convert to list of dictionaries
            result = [dict(row) for row in cursor.fetchall()]
            
            # Parse details JSON if included
            if include_details:
                for row in result:
                    if row['details']:
                        row['details'] = json.loads(row['details'])
            
            conn.close()
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting action stats: {e}")
            return []
    
    def get_follower_stats(self) -> Dict[str, Any]:
        """
        Get statistics about followers.
        
        Returns:
            Dictionary with follower statistics
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get follower counts by status
            cursor.execute('''
            SELECT status, COUNT(*) as count
            FROM followers
            GROUP BY status
            ''')
            
            status_counts = {row[0]: row[1] for row in cursor.fetchall()}
            
            # Get followers gained in last 7 days
            week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
            cursor.execute('''
            SELECT COUNT(*) FROM followers
            WHERE status IN ('follower_only', 'mutual')
            AND first_seen >= ?
            ''', (week_ago,))
            
            followers_gained_week = cursor.fetchone()[0]
            
            # Get followers gained in last 30 days
            month_ago = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            cursor.execute('''
            SELECT COUNT(*) FROM followers
            WHERE status IN ('follower_only', 'mutual')
            AND first_seen >= ?
            ''', (month_ago,))
            
            followers_gained_month = cursor.fetchone()[0]
            
            # Get follow/unfollow conversion rate
            cursor.execute('''
            SELECT 
                COUNT(CASE WHEN status = 'mutual' THEN 1 END) as converted,
                COUNT(CASE WHEN status = 'following_only' THEN 1 END) as not_converted
            FROM followers
            WHERE we_follow = 1
            ''')
            
            conversion_data = cursor.fetchone()
            converted = conversion_data[0]
            not_converted = conversion_data[1]
            
            follow_conversion_rate = 0
            if (converted + not_converted) > 0:
                follow_conversion_rate = (converted / (converted + not_converted)) * 100
            
            conn.close()
            
            # Build result dictionary
            result = {
                'status_counts': status_counts,
                'total_followers': status_counts.get('follower_only', 0) + status_counts.get('mutual', 0),
                'total_following': status_counts.get('following_only', 0) + status_counts.get('mutual', 0),
                'mutual_ratio': status_counts.get('mutual', 0) / max(1, status_counts.get('following_only', 0) + status_counts.get('mutual', 0)) * 100,
                'followers_gained': {
                    'last_7_days': followers_gained_week,
                    'last_30_days': followers_gained_month
                },
                'follow_conversion_rate': follow_conversion_rate
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting follower stats: {e}")
            return {}
    
    def get_growth_metrics(self, days: int = 30) -> Dict[str, Any]:
        """
        Get account growth metrics over time.
        
        Args:
            days: Number of days to look back
            
        Returns:
            Dictionary with growth metrics
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Calculate date cutoff
            cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
            
            # Get metrics for the time period
            cursor.execute('''
            SELECT date, followers_count, following_count, engagement_rate, growth_rate
            FROM metrics
            WHERE date >= ?
            ORDER BY date ASC
            ''', (cutoff_date,))
            
            rows = cursor.fetchall()
            
            # Format data for time series
            time_series = []
            for row in rows:
                time_series.append({
                    'date': row[0],
                    'followers_count': row[1],
                    'following_count': row[2],
                    'engagement_rate': row[3],
                    'growth_rate': row[4]
                })
            
            # Calculate averages
            if rows:
                avg_engagement = sum(row[3] for row in rows) / len(rows)
                avg_growth = sum(row[4] for row in rows) / len(rows)
                
                # Calculate net gain
                first_followers = rows[0][1]
                latest_followers = rows[-1][1]
                net_followers_gain = latest_followers - first_followers
                
                first_following = rows[0][2]
                latest_following = rows[-1][2]
                net_following_change = latest_following - first_following
            else:
                avg_engagement = 0
                avg_growth = 0
                net_followers_gain = 0
                net_following_change = 0
            
            conn.close()
            
            # Build result dictionary
            result = {
                'time_series': time_series,
                'averages': {
                    'engagement_rate': avg_engagement,
                    'growth_rate': avg_growth
                },
                'net_changes': {
                    'followers': net_followers_gain,
                    'following': net_following_change
                }
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting growth metrics: {e}")
            return {}
    
    def export_data(
        self,
        export_type: str,
        days: int = 30,
        file_path: Optional[str] = None
    ) -> str:
        """
        Export database data to CSV or JSON.
        
        Args:
            export_type: Type of data to export (actions, followers, metrics)
            days: Number of days to include
            file_path: Optional path to save file (defaults to data directory)
            
        Returns:
            str: Path to the exported file
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Return rows as dictionaries
            cursor = conn.cursor()
            
            # Calculate date cutoff
            cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
            
            # Default export directory
            if not file_path:
                export_dir = os.path.join(self.data_path, 'exports')
                create_directory_if_not_exists(export_dir)
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                file_path = os.path.join(
                    export_dir,
                    f"{self.username}_{export_type}_{timestamp}.csv"
                )
            
            # Query based on export type
            if export_type == 'actions':
                cursor.execute('''
                SELECT id, timestamp, action_type, target_username, target_url, status, details
                FROM actions
                WHERE timestamp >= ?
                ORDER BY timestamp DESC
                ''', (cutoff_date,))
                
            elif export_type == 'followers':
                cursor.execute('''
                SELECT username, first_seen, status, followed_by_us, we_follow, last_updated
                FROM followers
                WHERE last_updated >= ?
                ORDER BY first_seen DESC
                ''', (cutoff_date,))
                
            elif export_type == 'metrics':
                cursor.execute('''
                SELECT date, followers_count, following_count, likes_received, 
                       comments_received, engagement_rate, growth_rate
                FROM metrics
                WHERE date >= ?
                ORDER BY date DESC
                ''', (cutoff_date,))
                
            else:
                logger.error(f"Invalid export type: {export_type}")
                conn.close()
                return ""
            
            # Get results
            rows = cursor.fetchall()
            
            # Get column names
            if rows:
                columns = rows[0].keys()
                
                # Write to CSV
                with open(file_path, 'w', newline='') as csv_file:
                    writer = csv.DictWriter(csv_file, fieldnames=columns)
                    writer.writeheader()
                    
                    for row in rows:
                        # Convert details JSON if needed
                        if 'details' in row.keys() and row['details']:
                            try:
                                row_dict = dict(row)
                                row_dict['details'] = json.dumps(json.loads(row['details']))
                                writer.writerow(row_dict)
                            except:
                                writer.writerow(dict(row))
                        else:
                            writer.writerow(dict(row))
            
            conn.close()
            
            logger.info(f"Exported {export_type} data to {file_path}")
            
            return file_path
            
        except Exception as e:
            logger.error(f"Error exporting data: {e}")
            return ""
    
    def calculate_engagement_rate(self, posts_data: List[Dict[str, Any]]) -> float:
        """
        Calculate the engagement rate based on recent posts.
        
        Args:
            posts_data: List of dictionaries with post metrics
                (each with 'likes' and 'comments' keys)
            
        Returns:
            float: Calculated engagement rate percentage
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get latest follower count
            cursor.execute('''
            SELECT followers_count
            FROM metrics
            ORDER BY date DESC
            LIMIT 1
            ''')
            
            result = cursor.fetchone()
            
            if not result:
                return 0.0
                
            followers_count = result[0]
            
            # Calculate metrics
            if followers_count <= 0 or not posts_data:
                return 0.0
            
            total_likes = sum(post.get('likes', 0) for post in posts_data)
            total_comments = sum(post.get('comments', 0) for post in posts_data)
            
            # Weight comments more than likes
            weighted_engagement = total_likes + (total_comments * 2)
            
            # Engagement rate per post
            engagement_per_post = weighted_engagement / len(posts_data)
            
            # Engagement rate as percentage of followers
            engagement_rate = (engagement_per_post / followers_count) * 100
            
            conn.close()
            
            return engagement_rate
            
        except Exception as e:
            logger.error(f"Error calculating engagement rate: {e}")
            return 0.0