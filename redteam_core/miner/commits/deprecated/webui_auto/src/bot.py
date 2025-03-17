#!/usr/bin/env python3
"""
Web UI Automation Script with standardized input/output models.
"""
import json
import time
import logging
from typing import Optional

from pydantic import HttpUrl
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from data_types import MinerInput, MinerOutput


logger = logging.getLogger(__name__)


class WebUIAutomate:
    """Class to handle web UI automation tasks."""

    _VIEWPORT_WIDTH = 1920
    _VIEWPORT_HEIGHT = 1080

    def __init__(
        self,
        username: str = "username",
        password: str = "password",
        web_url: Optional[HttpUrl] = None,
    ):
        """
        Initialize WebUI automation.

        Args:
            username: Login username
            password: Login password
            score_url: URL for sending mining results
        """
        self.username = username
        self.password = password
        self.web_url = None
        self.driver: Optional[WebDriver] = None

    def setup_driver(self) -> None:
        """Initialize Chrome WebDriver."""
        try:
            options = webdriver.ChromeOptions()

            options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-gpu")
            # options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--ignore-certificate-errors")
            options.add_argument(
                f"--unsafely-treat-insecure-origin-as-secure={self.web_url}"
            )
            options.add_argument(
                f"--window-size={self._VIEWPORT_WIDTH},{self._VIEWPORT_HEIGHT}"
            )

            self.driver = webdriver.Chrome(options=options)

        except WebDriverException as e:
            logger.error(f"WebDriver setup failed: {e}")
            raise

    def automate_login(self) -> bool:
        """Automate the login process."""
        try:
            self.driver.get(str(self.web_url))
            wait = WebDriverWait(self.driver, 15)

            # Ensure the page has fully loaded
            wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, 'input[placeholder="Username"]')
                )
            )
            # Scroll to make elements interactable
            username_field = self.driver.find_element(
                By.CSS_SELECTOR, 'input[placeholder="Username"]'
            )
            self.driver.execute_script(
                "arguments[0].scrollIntoView(true);", username_field
            )
            username_field.clear()
            username_field.send_keys(self.username)

            password_field = self.driver.find_element(
                By.CSS_SELECTOR, 'input[placeholder="Password"]'
            )
            self.driver.execute_script(
                "arguments[0].scrollIntoView(true);", password_field
            )
            password_field.clear()
            password_field.send_keys(self.password)

            # Interact with checkboxes
            checkboxes = self.driver.find_elements(
                By.CSS_SELECTOR, 'input[type="checkbox"]'
            )
            for checkbox in checkboxes:
                self.driver.execute_script("arguments[0].click();", checkbox)

            # Submit login
            login_button = wait.until(
                EC.element_to_be_clickable((By.ID, "login-button"))
            )
            login_button.click()

            return True

        except Exception as e:
            logger.error(f"Login failed: {e}")
            return False

    def get_local_storage_data(self) -> Optional[MinerOutput]:
        """
        Get local storage data and convert to MinerOutput.

        Returns:
            MinerOutput if successful, None otherwise
        """
        try:
            data = self.driver.execute_script(
                "return window.localStorage.getItem('data');"
            )
            if not data:
                return None

            parsed_data = json.loads(data)

            return MinerOutput(
                ciphertext=parsed_data.get("ciphertext"),
                key=parsed_data.get("key"),
                iv=parsed_data.get("iv"),
            )
        except Exception as e:
            logger.error(f"Failed to get local storage: {e}")
            return None

    def cleanup(self) -> None:
        """Cleanup resources."""
        if self.driver:
            self.driver.delete_all_cookies()
            self.driver.execute_script("window.localStorage.clear();")
            self.driver.quit()

    def __call__(self, input_data: MinerInput) -> Optional[MinerOutput]:
        """
        Run automation process with given URL.

        Args:
            input_data: MinerInput containing the web URL

        Returns:
            MinerOutput if successful, None otherwise
        """
        self.web_url = input_data.web_url

        try:
            self.setup_driver()

            if not self.automate_login():
                return None

            time.sleep(3)
            data = self.get_local_storage_data()
            if not data:
                return None

            return data

        except Exception as e:
            logger.error(f"Automation failed: {e}")
            return None
        finally:
            self.cleanup()
