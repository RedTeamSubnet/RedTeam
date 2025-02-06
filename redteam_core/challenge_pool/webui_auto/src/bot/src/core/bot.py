# -*- coding: utf-8 -*-

import logging
from typing import Any, Dict

from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


logger = logging.getLogger(__name__)


def run_bot(
    driver: WebDriver,
    config: Dict[str, Any],
    username: str = "username",
    password: str = "password",
) -> bool:
    """Run bot to automate login.

    Args:
        driver   (WebDriver, required): Selenium WebDriver instance.
        username (str      , optional): Username to login. Defaults to "username".
        password (str      , optional): Password to login. Defaults to "password".

    Returns:
        bool: True if login is successful, False otherwise.
    """

    try:
        _wait = WebDriverWait(driver, 15)
        _actions = ActionChains(driver)

        # Ensure the page has fully loaded
        _wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, 'input[placeholder="Username"]')
            )
        )

        # Scroll to make elements interactable
        _username_field = driver.find_element(
            By.CSS_SELECTOR, 'input[placeholder="Username"]'
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", _username_field)
        _username_field.clear()
        _username_field.send_keys(username)

        _password_field = driver.find_element(
            By.CSS_SELECTOR, 'input[placeholder="Password"]'
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", _password_field)
        _password_field.clear()
        _password_field.send_keys(password)

        # Interact with checkboxes
        for _action in config["actions"]:
            if _action["type"] == "click":
                x, y = (
                    _action["args"]["location"]["x"],
                    _action["args"]["location"]["y"],
                )
                print(f"Clicking at ({x}, {y})")
                _actions.move_by_offset(x, y).click().perform()
                _actions.move_by_offset(-x, -y).perform()

        checkboxes = driver.find_elements(By.CSS_SELECTOR, 'input[type="checkbox"]')
        for checkbox in checkboxes:
            driver.execute_script("arguments[0].click();", checkbox)

        # Submit login
        _login_button = _wait.until(EC.element_to_be_clickable((By.ID, "login-button")))
        _login_button.click()

        return True

    except Exception as err:
        logger.error(f"Login failed: {err}")
        return False


__all__ = ["run_bot"]
