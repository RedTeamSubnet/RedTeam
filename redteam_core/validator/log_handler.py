import logging
import time
from logging.handlers import QueueListener
import json
import requests
import traceback

import bittensor as bt
from redteam_core.constants import constants

class JSONLogFormatter(logging.Formatter):
    """
    A log formatter optimized for structured logging, ensuring UTC timestamps.
    """

    def __init__(self):
        super().__init__()
        self.converter = time.gmtime  # Force UTC timestamps

    def format(self, record: logging.LogRecord) -> str:
        """Convert a log record into a structured JSON format with UTC time."""

        log_entry = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",  # ISO 8601 UTC format
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "trace": record.exc_info is not None,  # True if exception exists
        }

        # Include exception details if any
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry)  # Convert dictionary to JSON string


class BittensorLogHandler(logging.Handler):
    def __init__(self, api_key, buffer_size=10, level=logging.INFO):
        super().__init__(level)
        self.api_key = api_key
        self.buffer_size = buffer_size
        self.buffer = []

        # Use the optimized JSON formatter for network logs
        self.setFormatter(JSONLogFormatter())

    def emit(self, record):
        """Capture log, convert to JSON, and flush when buffer is full."""
        if record.levelno < self.level:
            return

        log_entry = self.format(record)  # Now JSON-formatted

        self.buffer.append(log_entry)

        if len(self.buffer) >= self.buffer_size:
            self.flush_logs()

    def flush_logs(self):
        """Send buffered logs as a batch to the log storage server."""
        logging_endpoint = f"{constants.STORAGE_URL}/upload-log"

        if not self.buffer:
            return

        payload = {"logs": self.buffer}
        headers = {
            "Authorization": self.api_key,
            "Content-Type": "application/json"
        }

        try:
            response = requests.post(logging_endpoint, json=payload, headers=headers)
            response.raise_for_status()
        except requests.RequestException as e:
            bt.logging.error(f"[LOG HANDLER] Failed to send logs: {traceback.format_exc()}")

        self.buffer.clear()


def start_bittensor_log_listener(api_key, buffer_size=10):
    """
    Starts a separate QueueListener that listens to Bittensor's logging queue.
    """
    bt_logger = bt.logging  # The Bittensor logging machine
    log_queue = bt_logger.get_queue()  # Get the shared log queue

    # Create our custom log handler
    custom_handler = BittensorLogHandler(api_key, buffer_size)

    # Create our own listener that listens to the same queue
    custom_listener = QueueListener(log_queue, custom_handler, respect_handler_level=True)

    # Start our custom listener
    custom_listener.start()

    bt.logging.success("Custom Bittensor log listener started!")
    return custom_listener  # Return the listener so we can stop it if needed
