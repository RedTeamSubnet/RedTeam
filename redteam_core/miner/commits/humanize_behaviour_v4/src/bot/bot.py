import json
import logging
import time
from typing import Any, Dict

from selenium.webdriver.common.by import By
from selenium.webdriver.common.actions.action_builder import ActionBuilder
from selenium.webdriver.common.actions.pointer_input import PointerInput

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


logger = logging.getLogger(__name__)


def run_bot(
    driver: WebDriver,
    username: str = "username",
    password: str = "password",
) -> bool:
    """Run bot to automate login.

    Args:
        driver   (WebDriver, required): Chrome WebDriver instance.
        config   (Dict[str, Any], required): Configuration dictionary containing actions.
        username (str, optional): Username to login. Defaults to "username".
        password (str, optional): Password to login. Defaults to "password".

    Returns:
        bool: True if login is successful, False otherwise.
    """
    try:
        _wait = WebDriverWait(driver, 15)

        # Find and fill username field
        _username_field = driver.find_element(
            By.CSS_SELECTOR, 'input[placeholder="Username"]'
        )
        _username_field.clear()
        _username_field.send_keys(username)

        # Find and fill password field
        _password_field = driver.find_element(
            By.CSS_SELECTOR, 'input[placeholder="Password"]'
        )
        _password_field.clear()
        _password_field.send_keys(password)
        mouse = PointerInput(kind="mouse", name="mouse")

        # Perform configured actions
        action_list = driver.execute_script("return window.ACTIONS_LIST;")
        _action_list = json.loads(action_list)
        for i, _action in enumerate(_action_list):
            if _action["type"] == "click":
                x = _action["args"]["location"]["x"]
                y = _action["args"]["location"]["y"]

                logger.info(f"Action {i+1}: Clicking at ({x}, {y})")

                try:
                    actions = ActionBuilder(driver, mouse=mouse)
                    actions.pointer_action.move_to_location(x, y)
                    actions.pointer_action.click()
                    actions.perform()

                    time.sleep(0.5)

                except Exception as e:
                    logger.error(f"Failed to perform action {i+1}: {e}")
                    continue

        # Click login button without scrolling
        _login_button = _wait.until(
            EC.presence_of_element_located((By.ID, "login-button"))
        )
        _login_button.click()

        return True

    except Exception as err:
        logger.error(f"Login failed: {err}")
        return False
