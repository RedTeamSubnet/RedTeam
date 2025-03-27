# -*- coding: utf-8 -*-

import time
import logging
from typing import Union, Any, Dict

from pydantic import HttpUrl
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from core.bot import run_bot


logger = logging.getLogger(__name__)


class WebUIAutomate:
    """Class to handle web UI automation tasks."""

    _VIEWPORT_WIDTH = 1440
    _VIEWPORT_HEIGHT = 900

    def __init__(self, web_url: HttpUrl, config: Dict[str, Any]):
        """
        Initialize WebUI automation.

        Args:
            web_url (str , required): URL to automate.
            config  (Dict, required): Configuration.
        """

        self.web_url = web_url
        self.config = config
        self.driver: Union[WebDriver, None] = None

    def setup_driver(self) -> None:
        """Initialize Chrome WebDriver."""

        try:
            _options = webdriver.ChromeOptions()
            _options.add_argument("--headless")
            _options.add_argument("--no-sandbox")
            _options.add_argument("--disable-gpu")
            # _options.add_argument("--disable-dev-shm-usage")
            _options.add_argument("--ignore-certificate-errors")
            _options.add_argument(
                f"--unsafely-treat-insecure-origin-as-secure={self.web_url}"
            )
            _options.add_argument(
                f"--window-size={self._VIEWPORT_WIDTH},{self._VIEWPORT_HEIGHT}"
            )

            self.driver = webdriver.Chrome(options=_options)
            self.driver.get(str(self.web_url))
            _wait = WebDriverWait(self.driver, 15)

            ## Ensure the page has fully loaded
            _wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, 'input[placeholder="Username"]')
                )
            )

        except WebDriverException as err:
            logger.error(f"WebDriver setup failed: {err}")
            raise

        return

    def get_local_storage_data(self) -> Union[str, None]:
        """
        Get local storage data.

        Returns:
            Union[str, None]: Data
        """

        try:
            _data = self.driver.execute_script(
                "return window.localStorage.getItem('data');"
            )
            if not _data:
                return None

            return _data
        except Exception as err:
            logger.error(f"Failed to get local storage: {err}")
            return None

    def cleanup(self) -> None:
        """Cleanup resources."""

        if self.driver:
            self.driver.delete_all_cookies()
            self.driver.execute_script("window.localStorage.clear();")
            self.driver.quit()

        return

    def __call__(self) -> Union[str, None]:
        """
        Run automation process with given URL.

        Args:
            web_url (str, optional): URL to automate.

        Returns:
            Union[str, None]: Data
        """

        if not self.web_url:
            raise RuntimeError("Web URL is empty, cannot proceed!")

        if not self.config:
            raise RuntimeError("Configuration is empty, cannot proceed!")

        try:
            self.setup_driver()

            if not run_bot(driver=self.driver, config=self.config):
                return None

            time.sleep(3)
            _data = self.get_local_storage_data()
            if not _data:
                return None

            return

        except Exception as err:
            logger.error(f"Automation failed: {err}")
            return None
        finally:
            self.cleanup()


__all__ = ["WebUIAutomate"]
