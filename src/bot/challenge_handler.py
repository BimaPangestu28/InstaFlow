"""
Instagram login challenge handler module.

This module provides functionality to handle various Instagram login challenges
such as suspicious login attempts, 2FA verification, etc.
"""

import logging
import re
import time
from typing import Optional, Tuple

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from .utils import random_delay

# Setup logger
logger = logging.getLogger(__name__)


class ChallengeHandler:
    """
    Handles Instagram login challenges and security verifications.
    """
    
    def __init__(self, driver: WebDriver, wait: WebDriverWait):
        """
        Initialize the challenge handler.
        
        Args:
            driver: Selenium WebDriver instance
            wait: WebDriverWait instance for timeouts
        """
        self.driver = driver
        self.wait = wait
    
    def check_for_challenge(self) -> bool:
        """
        Check if a login challenge is present.
        
        Returns:
            bool: True if a challenge is detected, False otherwise
        """
        try:
            # Check for challenge page indicators
            challenge_indicators = [
                "//form[contains(@id, 'challenge')]",
                "//div[contains(text(), 'suspicious login attempt')]",
                "//div[contains(text(), 'suspicious activity')]",
                "//p[contains(text(), 'security code')]",
                "//p[contains(text(), 'confirmation code')]",
                "//p[contains(text(), 'verify your account')]",
                "//h3[contains(text(), 'We Detected An Unusual Login Attempt')]"
            ]
            
            for indicator in challenge_indicators:
                try:
                    if self.driver.find_element(By.XPATH, indicator).is_displayed():
                        logger.warning("Login challenge detected")
                        return True
                except NoSuchElementException:
                    continue
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking for challenge: {e}")
            return False
    
    def handle_challenge(self) -> bool:
        """
        Handle the detected challenge.
        
        Returns:
            bool: True if challenge was successfully handled, False otherwise
        """
        try:
            # First, identify which type of challenge we're dealing with
            if self._is_two_factor_challenge():
                return self._handle_two_factor()
                
            elif self._is_email_verification():
                return self._handle_email_verification()
                
            elif self._is_phone_verification():
                return self._handle_phone_verification()
                
            elif self._is_unusual_login_challenge():
                return self._handle_unusual_login()
                
            else:
                logger.error("Unknown challenge type")
                return False
                
        except Exception as e:
            logger.error(f"Error handling challenge: {e}")
            return False
    
    def _is_two_factor_challenge(self) -> bool:
        """
        Check if this is a two-factor authentication challenge.
        
        Returns:
            bool: True if it's a 2FA challenge, False otherwise
        """
        try:
            return bool(self.driver.find_elements(By.XPATH, 
                "//h2[contains(text(), 'Two-Factor') or contains(text(), '2-Factor')]"
            ))
        except Exception:
            return False
    
    def _is_email_verification(self) -> bool:
        """
        Check if this is an email verification challenge.
        
        Returns:
            bool: True if it's an email verification, False otherwise
        """
        try:
            email_indicators = [
                "//div[contains(text(), 'sent an email to')]",
                "//label[contains(text(), 'Email')]//following::input",
                "//div[contains(text(), 'email confirmation')]"
            ]
            
            for indicator in email_indicators:
                if self.driver.find_elements(By.XPATH, indicator):
                    return True
            
            return False
            
        except Exception:
            return False
    
    def _is_phone_verification(self) -> bool:
        """
        Check if this is a phone verification challenge.
        
        Returns:
            bool: True if it's a phone verification, False otherwise
        """
        try:
            phone_indicators = [
                "//div[contains(text(), 'sent a text message with a code')]",
                "//label[contains(text(), 'Phone')]//following::input",
                "//div[contains(text(), 'SMS confirmation')]"
            ]
            
            for indicator in phone_indicators:
                if self.driver.find_elements(By.XPATH, indicator):
                    return True
            
            return False
            
        except Exception:
            return False
    
    def _is_unusual_login_challenge(self) -> bool:
        """
        Check if this is an unusual login attempt challenge.
        
        Returns:
            bool: True if it's an unusual login challenge, False otherwise
        """
        try:
            return bool(self.driver.find_elements(By.XPATH, 
                "//h3[contains(text(), 'Unusual Login Attempt')]"
            ))
        except Exception:
            return False
    
    def _handle_two_factor(self) -> bool:
        """
        Handle two-factor authentication challenge.
        
        Returns:
            bool: True if successfully handled, False otherwise
        """
        logger.info("Handling two-factor authentication challenge")
        
        try:
            # Find the code input field
            code_input = self.wait.until(
                EC.presence_of_element_located((By.XPATH, "//input[@name='verificationCode']"))
            )
            
            # Get the code from the user
            verification_code = self._request_verification_code("two-factor")
            
            if not verification_code:
                logger.error("No verification code provided")
                return False
            
            # Enter the code
            code_input.clear()
            code_input.send_keys(verification_code)
            
            # Submit the form
            submit_button = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Confirm') or contains(text(), 'Submit')]")
            submit_button.click()
            
            # Wait for successful login
            try:
                self.wait.until(
                    EC.presence_of_element_located((By.XPATH, "//a[contains(@href, '/direct/inbox/')]"))
                )
                logger.info("Two-factor authentication successful")
                return True
            except TimeoutException:
                logger.error("Failed to verify two-factor code")
                return False
                
        except Exception as e:
            logger.error(f"Error in two-factor handling: {e}")
            return False
    
    def _handle_email_verification(self) -> bool:
        """
        Handle email verification challenge.
        
        Returns:
            bool: True if successfully handled, False otherwise
        """
        logger.info("Handling email verification challenge")
        
        try:
            # Check if we need to select email option first
            try:
                email_option = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Email')]")
                email_option.click()
                random_delay(1, 2)
            except NoSuchElementException:
                pass  # Email might already be selected
            
            # If there's a "Send Security Code" button, click it
            try:
                send_button = self.driver.find_element(By.XPATH, 
                    "//button[contains(text(), 'Send Security Code') or contains(text(), 'Send Code')]"
                )
                send_button.click()
                random_delay(1, 2)
            except NoSuchElementException:
                pass  # Code might have been sent automatically
            
            # Extract email address if shown
            try:
                email_text = self.driver.find_element(By.XPATH, 
                    "//div[contains(text(), '@') and contains(text(), '.')]"
                ).text
                email = re.search(r'[\w.+-]+@[\w-]+\.[\w.-]+', email_text)
                email_hint = email.group(0) if email else "your email"
            except Exception:
                email_hint = "your email"
            
            # Find the code input field
            code_input = self.wait.until(
                EC.presence_of_element_located((By.XPATH, "//input[@name='security_code' or @name='email_confirmation_code']"))
            )
            
            # Get the code from the user
            verification_code = self._request_verification_code("email", email_hint)
            
            if not verification_code:
                logger.error("No verification code provided")
                return False
            
            # Enter the code
            code_input.clear()
            code_input.send_keys(verification_code)
            
            # Submit the form
            submit_button = self.driver.find_element(By.XPATH, 
                "//button[contains(text(), 'Confirm') or contains(text(), 'Submit') or contains(text(), 'Next')]"
            )
            submit_button.click()
            
            # Wait for successful verification
            try:
                self.wait.until(
                    EC.presence_of_element_located((By.XPATH, "//a[contains(@href, '/direct/inbox/')]"))
                )
                logger.info("Email verification successful")
                return True
            except TimeoutException:
                logger.error("Failed to verify email code")
                return False
                
        except Exception as e:
            logger.error(f"Error in email verification handling: {e}")
            return False
    
    def _handle_phone_verification(self) -> bool:
        """
        Handle phone verification challenge.
        
        Returns:
            bool: True if successfully handled, False otherwise
        """
        logger.info("Handling phone verification challenge")
        
        try:
            # Check if we need to select phone option first
            try:
                phone_option = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Phone') or contains(text(), 'Text')]")
                phone_option.click()
                random_delay(1, 2)
            except NoSuchElementException:
                pass  # Phone might already be selected
            
            # If there's a "Send Security Code" button, click it
            try:
                send_button = self.driver.find_element(By.XPATH, 
                    "//button[contains(text(), 'Send Security Code') or contains(text(), 'Send Code')]"
                )
                send_button.click()
                random_delay(1, 2)
            except NoSuchElementException:
                pass  # Code might have been sent automatically
            
            # Extract phone number if shown
            try:
                phone_text = self.driver.find_element(By.XPATH, 
                    "//div[contains(text(), '+') or contains(text(), '(')]"
                ).text
                phone = re.search(r'[\d\+\-\(\) ]{7,}', phone_text)
                phone_hint = phone.group(0) if phone else "your phone"
            except Exception:
                phone_hint = "your phone"
            
            # Find the code input field
            code_input = self.wait.until(
                EC.presence_of_element_located((By.XPATH, "//input[@name='security_code' or @name='sms_confirmation_code']"))
            )
            
            # Get the code from the user
            verification_code = self._request_verification_code("phone", phone_hint)
            
            if not verification_code:
                logger.error("No verification code provided")
                return False
            
            # Enter the code
            code_input.clear()
            code_input.send_keys(verification_code)
            
            # Submit the form
            submit_button = self.driver.find_element(By.XPATH, 
                "//button[contains(text(), 'Confirm') or contains(text(), 'Submit') or contains(text(), 'Next')]"
            )
            submit_button.click()
            
            # Wait for successful verification
            try:
                self.wait.until(
                    EC.presence_of_element_located((By.XPATH, "//a[contains(@href, '/direct/inbox/')]"))
                )
                logger.info("Phone verification successful")
                return True
            except TimeoutException:
                logger.error("Failed to verify phone code")
                return False
                
        except Exception as e:
            logger.error(f"Error in phone verification handling: {e}")
            return False
    
    def _handle_unusual_login(self) -> bool:
        """
        Handle unusual login attempt challenge.
        
        Returns:
            bool: True if successfully handled, False otherwise
        """
        logger.info("Handling unusual login attempt challenge")
        
        try:
            # Try to find and click "This Was Me" button
            try:
                this_was_me = self.driver.find_element(By.XPATH, 
                    "//button[contains(text(), 'This Was Me')]"
                )
                this_was_me.click()
                
                # Wait for successful verification
                try:
                    self.wait.until(
                        EC.presence_of_element_located((By.XPATH, "//a[contains(@href, '/direct/inbox/')]"))
                    )
                    logger.info("Unusual login challenge resolved")
                    return True
                except TimeoutException:
                    pass  # Fall through to other methods
                    
            except NoSuchElementException:
                pass
            
            # If "This Was Me" didn't work, look for other verification options
            # This usually falls back to email or phone verification
            if self._is_email_verification():
                return self._handle_email_verification()
            elif self._is_phone_verification():
                return self._handle_phone_verification()
            else:
                logger.error("Could not resolve unusual login challenge")
                return False
                
        except Exception as e:
            logger.error(f"Error handling unusual login: {e}")
            return False
    
    def _request_verification_code(self, verification_type: str, hint: str = "") -> Optional[str]:
        """
        Request verification code from the user.
        
        In a real implementation, this might send a notification to the admin,
        use an email API to fetch codes, or use other automated methods.
        
        Args:
            verification_type: Type of verification (email, phone, two-factor)
            hint: Additional information to help user locate the code
            
        Returns:
            str: Verification code or None if unavailable
        """
        # This implementation just logs the request - in real usage, this would need to
        # be implemented according to your verification code retrieval strategy
        logger.warning(
            f"MANUAL INTERVENTION REQUIRED: {verification_type.upper()} verification code needed for {hint}. "
            f"Please check your device and provide the code."
        )
        
        # In a production implementation, you might:
        # 1. Send a notification to admin
        # 2. Use an email API to fetch verification codes
        # 3. Use a SMS gateway API to get codes from texts
        # 4. Integrate with a notification service
        
        # For now, we'll simulate waiting for manual input by pausing
        # In a real implementation, replace this with your actual code retrieval logic
        logger.warning("Waiting 60 seconds for manual code entry (simulated)")
        time.sleep(60)
        
        # Return None to indicate we couldn't get a code
        # In a real implementation, you would return the actual code here
        return None