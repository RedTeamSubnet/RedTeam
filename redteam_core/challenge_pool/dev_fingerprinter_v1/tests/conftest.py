# -*- coding: utf-8 -*-

import logging

import pytest


logger = logging.getLogger(__name__)


@pytest.fixture(scope="session", autouse=True)
def setup_and_teardown():
    # Equivalent of setUp
    logger.info("Setting up...")

    yield  # This is where the testing happens!

    # Equivalent of tearDown
    logger.info("Tearing down!")
