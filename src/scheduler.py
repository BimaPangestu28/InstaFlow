"""
Scheduler module for InstaFlow.

This module provides functionality for scheduling and managing automated tasks.
"""

import logging
import time
import json
import os
import threading
import schedule
from typing import Dict, List, Optional, Tuple, Union, Any, Callable
from datetime import datetime, timedelta
import importlib

from .config.settings import settings
from .bot import InstagramBot
from .bot.utils import create_directory_if_not_exists, get_current_timestamp

# Setup logger
logger = logging.getLogger(__name__)


class JobDefinition:
    """
    Definition for a scheduled job.
    """
    
    def __init__(
        self,
        name: str,
        function: Union[str, Callable],
        schedule_at: str,
        args: Optional[List] = None,
        kwargs: Optional[Dict] = None,
        enabled: bool = True,
        tags: Optional[List[str]] = None,
        description: Optional[str] = None
    ):
        """
        Initialize a job definition.
        
        Args:
            name: Unique name for the job
            function: Function to execute (string path or callable)
            schedule_at: Schedule string (e.g., "daily at 10:00", "every 1 hour")
            args: Positional arguments for the function
            kwargs: Keyword arguments for the function
            enabled: Whether this job is enabled
            tags: Optional tags for categorizing jobs
            description: Optional job description
        """
        self.name = name
        self.function = function
        self.schedule_at = schedule_at
        self.args = args or []
        self.kwargs = kwargs or {}
        self.enabled = enabled
        self.tags = tags or []
        self.description = description or ""
        
        # Runtime tracking
        self.last_run = None
        self.last_status = None
        self.next_run = None
        self.run_count = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert job definition to dictionary.
        
        Returns:
            Dictionary representation of the job
        """
        # Function needs special handling
        if callable(self.function):
            function_str = f"{self.function.__module__}.{self.function.__name__}"
        else:
            function_str = self.function
        
        return {
            'name': self.name,
            'function': function_str,
            'schedule_at': self.schedule_at,
            'args': self.args,
            'kwargs': self.kwargs,
            'enabled': self.enabled,
            'tags': self.tags,
            'description': self.description,
            'last_run': self.last_run,
            'last_status': self.last_status,
            'next_run': self.next_run,
            'run_count': self.run_count
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'JobDefinition':
        """
        Create job definition from dictionary.
        
        Args:
            data: Dictionary with job configuration
            
        Returns:
            JobDefinition instance
        """
        job = cls(
            name=data['name'],
            function=data['function'],
            schedule_at=data['schedule_at'],
            args=data.get('args', []),
            kwargs=data.get('kwargs', {}),
            enabled=data.get('enabled', True),
            tags=data.get('tags', []),
            description=data.get('description', "")
        )
        
        # Set runtime tracking
        job.last_run = data.get('last_run')
        job.last_status = data.get('last_status')
        job.next_run = data.get('next_run')
        job.run_count = data.get('run_count', 0)
        
        return job


class JobResult:
    """
    Result of a job execution.
    """
    
    def __init__(
        self,
        job_name: str,
        start_time: str,
        end_time: Optional[str] = None,
        success: Optional[bool] = None,
        result: Optional[Any] = None,
        error: Optional[str] = None
    ):
        """
        Initialize a job result.
        
        Args:
            job_name: Name of the job
            start_time: Start timestamp
            end_time: Optional end timestamp
            success: Whether the job succeeded
            result: Optional job result data
            error: Optional error message
        """
        self.job_name = job_name
        self.start_time = start_time
        self.end_time = end_time
        self.success = success
        self.result = result
        self.error = error
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert job result to dictionary.
        
        Returns:
            Dictionary representation of the result
        """
        return {
            'job_name': self.job_name,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'success': self.success,
            'result': self.result,
            'error': self.error
        }
    
    def complete(self, success: bool, result: Optional[Any] = None, error: Optional[str] = None) -> None:
        """
        Mark the job as complete.
        
        Args:
            success: Whether the job succeeded
            result: Optional result data
            error: Optional error message
        """
        self.end_time = get_current_timestamp()
        self.success = success
        self.result = result
        self.error = error


class Scheduler:
    """
    Task scheduler for managing automated Instagram routines.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the scheduler.
        
        Args:
            config_path: Optional path to custom jobs configuration
        """
        # Data storage paths
        self.data_path = os.path.join(
            settings.get('data', 'path', default='data'),
            'scheduler'
        )
        create_directory_if_not_exists(self.data_path)
        
        self.jobs_file = os.path.join(self.data_path, 'jobs.json')
        self.results_file = os.path.join(self.data_path, 'results.json')
        
        # Load or initialize jobs
        self.jobs: Dict[str, JobDefinition] = {}
        self.job_results: List[JobResult] = []
        
        # Custom config path
        self.config_path = config_path
        
        # Initialize
        self._load_jobs()
        self._load_results()
        
        # Threading
        self.running = False
        self.scheduler_thread = None
    
    def _load_jobs(self) -> None:
        """
        Load jobs from configuration.
        """
        # First, try loading from jobs file
        if os.path.exists(self.jobs_file):
            try:
                with open(self.jobs_file, 'r') as f:
                    job_dicts = json.load(f)
                    
                    for job_dict in job_dicts:
                        job = JobDefinition.from_dict(job_dict)
                        self.jobs[job.name] = job
                        
                logger.debug(f"Loaded {len(self.jobs)} jobs from {self.jobs_file}")
                return
            except Exception as e:
                logger.error(f"Error loading jobs from {self.jobs_file}: {e}")
        
        # If that fails, load from configuration
        try:
            default_jobs = settings.get('scheduler', 'jobs', default=[])
            
            for job_config in default_jobs:
                job = JobDefinition(
                    name=job_config.get('name', f"job_{len(self.jobs)}"),
                    function=job_config.get('function', ''),
                    schedule_at=job_config.get('schedule_at', ''),
                    args=job_config.get('args', []),
                    kwargs=job_config.get('kwargs', {}),
                    enabled=job_config.get('enabled', True),
                    tags=job_config.get('tags', []),
                    description=job_config.get('description', '')
                )
                
                self.jobs[job.name] = job
            
            logger.debug(f"Loaded {len(self.jobs)} jobs from configuration")
        except Exception as e:
            logger.error(f"Error loading jobs from configuration: {e}")
    
    def _save_jobs(self) -> None:
        """
        Save jobs to file.
        """
        try:
            job_dicts = [job.to_dict() for job in self.jobs.values()]
            
            with open(self.jobs_file, 'w') as f:
                json.dump(job_dicts, f, indent=2)
                
            logger.debug(f"Saved {len(self.jobs)} jobs to {self.jobs_file}")
        except Exception as e:
            logger.error(f"Error saving jobs to {self.jobs_file}: {e}")
    
    def _load_results(self) -> None:
        """
        Load job results from file.
        """
        if os.path.exists(self.results_file):
            try:
                with open(self.results_file, 'r') as f:
                    result_dicts = json.load(f)
                    
                    for result_dict in result_dicts:
                        result = JobResult(
                            job_name=result_dict.get('job_name', ''),
                            start_time=result_dict.get('start_time', ''),
                            end_time=result_dict.get('end_time'),
                            success=result_dict.get('success'),
                            result=result_dict.get('result'),
                            error=result_dict.get('error')
                        )
                        
                        self.job_results.append(result)
                        
                # Only keep the most recent results
                max_results = settings.get('scheduler', 'max_results', default=100)
                if len(self.job_results) > max_results:
                    self.job_results = self.job_results[-max_results:]
                    
                logger.debug(f"Loaded {len(self.job_results)} job results from {self.results_file}")
            except Exception as e:
                logger.error(f"Error loading job results from {self.results_file}: {e}")
    
    def _save_results(self) -> None:
        """
        Save job results to file.
        """
        try:
            result_dicts = [result.to_dict() for result in self.job_results]
            
            with open(self.results_file, 'w') as f:
                json.dump(result_dicts, f, indent=2)
                
            logger.debug(f"Saved {len(self.job_results)} job results to {self.results_file}")
        except Exception as e:
            logger.error(f"Error saving job results to {self.results_file}: {e}")
    
    def _resolve_function(self, function_ref: Union[str, Callable]) -> Callable:
        """
        Resolve a function reference to a callable.
        
        Args:
            function_ref: Function reference (string path or callable)
            
        Returns:
            Callable function
            
        Raises:
            ValueError: If function cannot be resolved
        """
        if callable(function_ref):
            return function_ref
        
        if not isinstance(function_ref, str):
            raise ValueError(f"Function reference must be a string or callable, got {type(function_ref)}")
        
        try:
            # Split module path and function name
            module_path, function_name = function_ref.rsplit('.', 1)
            
            # Import the module
            module = importlib.import_module(module_path)
            
            # Get the function
            function = getattr(module, function_name)
            
            if not callable(function):
                raise ValueError(f"Resolved object {function_ref} is not callable")
            
            return function
            
        except (ValueError, ImportError, AttributeError) as e:
            raise ValueError(f"Could not resolve function {function_ref}: {e}")
    
    def _run_job(self, job: JobDefinition) -> None:
        """
        Run a scheduled job and track the result.
        
        Args:
            job: Job definition to run
        """
        logger.info(f"Running job: {job.name}")
        
        # Create result object
        result = JobResult(
            job_name=job.name,
            start_time=get_current_timestamp()
        )
        
        try:
            # Resolve function
            func = self._resolve_function(job.function)
            
            # Run the function
            function_result = func(*job.args, **job.kwargs)
            
            # Update result
            result.complete(True, result=function_result)
            
            # Update job stats
            job.last_run = result.start_time
            job.last_status = "success"
            job.run_count += 1
            
            logger.info(f"Job {job.name} completed successfully")
            
        except Exception as e:
            # Update result with error
            result.complete(False, error=str(e))
            
            # Update job stats
            job.last_run = result.start_time
            job.last_status = "failed"
            job.run_count += 1
            
            logger.error(f"Job {job.name} failed: {e}")
        
        # Add to results
        self.job_results.append(result)
        
        # Save updated state
        self._save_jobs()
        self._save_results()
    
    def add_job(
        self,
        name: str,
        function: Union[str, Callable],
        schedule_at: str,
        args: Optional[List] = None,
        kwargs: Optional[Dict] = None,
        enabled: bool = True,
        tags: Optional[List[str]] = None,
        description: Optional[str] = None
    ) -> JobDefinition:
        """
        Add a new job to the scheduler.
        
        Args:
            name: Unique name for the job
            function: Function to execute (string path or callable)
            schedule_at: Schedule string (e.g., "daily at 10:00")
            args: Positional arguments for the function
            kwargs: Keyword arguments for the function
            enabled: Whether this job is enabled
            tags: Optional tags for categorizing jobs
            description: Optional job description
            
        Returns:
            JobDefinition instance
            
        Raises:
            ValueError: If job with the same name already exists
        """
        if name in self.jobs:
            raise ValueError(f"Job with name '{name}' already exists")
        
        # Create job definition
        job = JobDefinition(
            name=name,
            function=function,
            schedule_at=schedule_at,
            args=args,
            kwargs=kwargs,
            enabled=enabled,
            tags=tags,
            description=description
        )
        
        # Add to jobs dictionary
        self.jobs[name] = job
        
        # Save jobs
        self._save_jobs()
        
        logger.info(f"Added job: {name}")
        
        return job
    
    def remove_job(self, name: str) -> bool:
        """
        Remove a job from the scheduler.
        
        Args:
            name: Name of the job to remove
            
        Returns:
            bool: True if job was removed, False if not found
        """
        if name not in self.jobs:
            logger.warning(f"Job {name} not found")
            return False
        
        # Remove from jobs dictionary
        del self.jobs[name]
        
        # Save jobs
        self._save_jobs()
        
        logger.info(f"Removed job: {name}")
        
        return True
    
    def update_job(
        self,
        name: str,
        function: Optional[Union[str, Callable]] = None,
        schedule_at: Optional[str] = None,
        args: Optional[List] = None,
        kwargs: Optional[Dict] = None,
        enabled: Optional[bool] = None,
        tags: Optional[List[str]] = None,
        description: Optional[str] = None
    ) -> JobDefinition:
        """
        Update an existing job.
        
        Args:
            name: Name of the job to update
            function: New function (optional)
            schedule_at: New schedule (optional)
            args: New args (optional)
            kwargs: New kwargs (optional)
            enabled: New enabled state (optional)
            tags: New tags (optional)
            description: New description (optional)
            
        Returns:
            Updated JobDefinition
            
        Raises:
            ValueError: If job not found
        """
        if name not in self.jobs:
            raise ValueError(f"Job {name} not found")
        
        job = self.jobs[name]
        
        # Update fields if provided
        if function is not None:
            job.function = function
        
        if schedule_at is not None:
            job.schedule_at = schedule_at
        
        if args is not None:
            job.args = args
        
        if kwargs is not None:
            job.kwargs = kwargs
        
        if enabled is not None:
            job.enabled = enabled
        
        if tags is not None:
            job.tags = tags
        
        if description is not None:
            job.description = description
        
        # Save jobs
        self._save_jobs()
        
        logger.info(f"Updated job: {name}")
        
        return job
    
    def get_job(self, name: str) -> Optional[JobDefinition]:
        """
        Get a job by name.
        
        Args:
            name: Name of the job
            
        Returns:
            JobDefinition or None if not found
        """
        return self.jobs.get(name)
    
    def get_jobs(
        self,
        tag: Optional[str] = None,
        enabled_only: bool = False
    ) -> List[JobDefinition]:
        """
        Get all jobs, optionally filtered.
        
        Args:
            tag: Optional tag to filter by
            enabled_only: Whether to only include enabled jobs
            
        Returns:
            List of matching jobs
        """
        result = []
        
        for job in self.jobs.values():
            # Filter by enabled state
            if enabled_only and not job.enabled:
                continue
                
            # Filter by tag
            if tag and tag not in job.tags:
                continue
                
            result.append(job)
        
        return result
    
    def get_job_results(
        self,
        job_name: Optional[str] = None,
        success_only: Optional[bool] = None,
        limit: Optional[int] = None
    ) -> List[JobResult]:
        """
        Get job results, optionally filtered.
        
        Args:
            job_name: Optional job name to filter by
            success_only: Optional success state filter
            limit: Optional limit on number of results
            
        Returns:
            List of matching job results
        """
        results = []
        
        for result in reversed(self.job_results):  # Most recent first
            # Filter by job name
            if job_name and result.job_name != job_name:
                continue
                
            # Filter by success state
            if success_only is not None and result.success != success_only:
                continue
                
            results.append(result)
            
            # Apply limit
            if limit and len(results) >= limit:
                break
        
        return results
    
    def run_job_now(self, name: str) -> Optional[JobResult]:
        """
        Run a job immediately.
        
        Args:
            name: Name of the job to run
            
        Returns:
            JobResult or None if job not found
        """
        if name not in self.jobs:
            logger.warning(f"Job {name} not found")
            return None
        
        job = self.jobs[name]
        
        # Run the job
        self._run_job(job)
        
        # Return the most recent result
        for result in reversed(self.job_results):
            if result.job_name == name:
                return result
        
        return None
    
    def _schedule_all_jobs(self) -> None:
        """
        Schedule all enabled jobs with the scheduler library.
        """
        # Clear any existing jobs
        schedule.clear()
        
        # Schedule enabled jobs
        for job in self.jobs.values():
            if not job.enabled:
                continue
                
            try:
                # Parse schedule string
                schedule_parts = job.schedule_at.split()
                
                if job.schedule_at.startswith('every'):
                    # Format: "every X hours/minutes/seconds"
                    if len(schedule_parts) >= 3:
                        interval = int(schedule_parts[1])
                        unit = schedule_parts[2].lower().rstrip('s')  # Remove trailing 's' if present
                        
                        if unit == 'second':
                            scheduled_job = schedule.every(interval).seconds
                        elif unit == 'minute':
                            scheduled_job = schedule.every(interval).minutes
                        elif unit == 'hour':
                            scheduled_job = schedule.every(interval).hours
                        elif unit == 'day':
                            scheduled_job = schedule.every(interval).days
                        elif unit == 'week':
                            scheduled_job = schedule.every(interval).weeks
                        else:
                            logger.error(f"Unknown time unit in schedule: {unit}")
                            continue
                            
                elif job.schedule_at.startswith('daily at'):
                    # Format: "daily at HH:MM"
                    time_part = job.schedule_at.replace('daily at', '').strip()
                    scheduled_job = schedule.every().day.at(time_part)
                    
                elif job.schedule_at.startswith('weekly on'):
                    # Format: "weekly on DAY at HH:MM"
                    day_time_part = job.schedule_at.replace('weekly on', '').strip()
                    day_parts = day_time_part.split('at')
                    
                    if len(day_parts) == 2:
                        day = day_parts[0].strip().lower()
                        time_part = day_parts[1].strip()
                        
                        if day == 'monday':
                            scheduled_job = schedule.every().monday.at(time_part)
                        elif day == 'tuesday':
                            scheduled_job = schedule.every().tuesday.at(time_part)
                        elif day == 'wednesday':
                            scheduled_job = schedule.every().wednesday.at(time_part)
                        elif day == 'thursday':
                            scheduled_job = schedule.every().thursday.at(time_part)
                        elif day == 'friday':
                            scheduled_job = schedule.every().friday.at(time_part)
                        elif day == 'saturday':
                            scheduled_job = schedule.every().saturday.at(time_part)
                        elif day == 'sunday':
                            scheduled_job = schedule.every().sunday.at(time_part)
                        else:
                            logger.error(f"Unknown day in schedule: {day}")
                            continue
                    else:
                        logger.error(f"Invalid weekly schedule format: {job.schedule_at}")
                        continue
                else:
                    logger.error(f"Unsupported schedule format: {job.schedule_at}")
                    continue
                
                # Add the job to the scheduler
                scheduled_job.do(self._run_job, job)
                
                # Calculate and store next run time
                job.next_run = scheduled_job.next_run.strftime("%Y-%m-%d %H:%M:%S")
                
                logger.debug(f"Scheduled job {job.name} to run {job.schedule_at}")
                
            except Exception as e:
                logger.error(f"Error scheduling job {job.name}: {e}")
    
    def _scheduler_loop(self) -> None:
        """
        Main scheduler loop.
        """
        logger.info("Scheduler started")
        
        while self.running:
            try:
                # Run pending jobs
                schedule.run_pending()
                
                # Sleep for a short time
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                time.sleep(5)  # Sleep longer on error
    
    def start(self) -> None:
        """
        Start the scheduler.
        """
        if self.running:
            logger.warning("Scheduler is already running")
            return
        
        # Schedule all jobs
        self._schedule_all_jobs()
        
        # Set running flag
        self.running = True
        
        # Start scheduler thread
        self.scheduler_thread = threading.Thread(target=self._scheduler_loop)
        self.scheduler_thread.daemon = True
        self.scheduler_thread.start()
        
        logger.info("Scheduler started")
    
    def stop(self) -> None:
        """
        Stop the scheduler.
        """
        if not self.running:
            logger.warning("Scheduler is not running")
            return
        
        # Set running flag
        self.running = False
        
        # Wait for thread to terminate
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
            
        # Clear all scheduled jobs
        schedule.clear()
        
        logger.info("Scheduler stopped")
    
    def restart(self) -> None:
        """
        Restart the scheduler.
        """
        self.stop()
        self._load_jobs()  # Reload jobs from file
        self.start()
        
        logger.info("Scheduler restarted")