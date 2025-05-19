#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import bittensor as bt

from redteam_core.validator.autoupdate import AutoUpdater
from neurons.validator.base_validator import Validator

# The main function parses the configuration and runs the validator.
if __name__ == "__main__":
    # Initialize the auto-updater
    AutoUpdater()

    # Start the validator
    with Validator() as validator:
        while True:
            bt.logging.info("Validator running...")
            time.sleep(60)

            if validator.should_exit:
                bt.logging.warning("Ending validator...")
                break