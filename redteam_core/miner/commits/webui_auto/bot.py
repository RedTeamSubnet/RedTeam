#!/usr/bin/env python3
"""
Web UI Automation Script with standardized input/output models.
"""

import json
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


class WebUIAutomate:
    """Class to handle web UI automation tasks."""

    def __init__(
        self,
        username: str = "username",
        password: str = "password",
        # score_url: str = "http://localhost:10001/score",
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
        # self.score_url = score_url
        self.driver: Optional[WebDriver] = None
        self.logger = logging.getLogger(__name__)
        self._setup_logger()

    def _setup_logger(self) -> None:
        """Configure logging."""
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    def setup_driver(self) -> None:
        """Initialize Chrome WebDriver."""
        try:
            options = webdriver.ChromeOptions()
            options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            self.driver = webdriver.Chrome(options=options)
        except WebDriverException as e:
            self.logger.error(f"WebDriver setup failed: {e}")
            raise

    def automate_login(self, url: HttpUrl) -> bool:
        """Automate the login process."""
        try:
            self.driver.get(str(url))
            wait = WebDriverWait(self.driver, 10)

            # Fill in login form
            username_field = wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, 'input[placeholder="Username"]')
                )
            )
            password_field = wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, 'input[placeholder="Password"]')
                )
            )

            username_field.send_keys(self.username)
            password_field.send_keys(self.password)

            # Checkboxes
            checkboxes = self.driver.find_elements(
                By.CSS_SELECTOR, 'input[type="checkbox"]'
            )
            for checkbox in checkboxes:
                if not checkbox.is_selected():
                    checkbox.click()

            # Submit
            login_button = self.driver.find_element(By.ID, "login-button")
            login_button.click()

            return True

        except Exception as e:
            self.logger.error(f"Login failed: {e}")
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
            self.logger.error(f"Failed to get local storage: {e}")
            return None

    # def send_data_to_endpoint(self, data: MinerOutput) -> bool:
    #     """Send MinerOutput data to endpoint."""
    #     try:
    #         response = requests.post(self.score_url, json=data.model_dump(), timeout=10)
    #         response.raise_for_status()
    #         return True
    #     except Exception as e:
    #         self.logger.error(f"Failed to send data: {e}")
    #         return False

    def cleanup(self) -> None:
        """Cleanup resources."""
        if self.driver:
            self.driver.quit()

    def __call__(self, input_data: MinerInput) -> Optional[MinerOutput]:
        """
        Run automation process with given URL.

        Args:
            input_data: MinerInput containing the web URL

        Returns:
            MinerOutput if successful, None otherwise

        Example:
            automator = WebUIAutomate(username="user", password="pass")
            miner_input = MinerInput(web_url="http://localhost:10001/web")
            result = automator(miner_input)
            if result:
                print(f"Ciphertext: {result.ciphertext}")
        """
        try:
            self.setup_driver()

            if not self.automate_login(input_data.web_url):
                return None

            data = self.get_local_storage_data()
            if not data:
                return None

            # if self.send_data_to_endpoint(data):
            #     return data
            # return None

            return data

        except Exception as e:
            self.logger.error(f"Automation failed: {e}")
            return None
        finally:
            self.cleanup()
