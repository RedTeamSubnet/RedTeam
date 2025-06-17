import datetime
import queue
import logging
import traceback
import threading
from logging.handlers import QueueHandler, QueueListener

import requests

import bittensor as bt

from redteam_core.constants import constants


class BittensorLogHandler(logging.Handler):
    def __init__(self, api_key, buffer_size=100, level=logging.DEBUG):
        super().__init__(level)
        self.api_key = api_key
        self.buffer_size = buffer_size
        self.log_queue = queue.Queue()
        self.stop_event = threading.Event()  # Used to stop the thread gracefully

        # Use the optimized JSON formatter for network logs
        self.setFormatter(bt.logging._file_formatter)

        # Start the daemon thread for sending logs
        self.sender_thread = threading.Thread(target=self.process_logs, daemon=True)
        self.sender_thread.start()

    def emit(self, record):
        """Capture log and enqueue it for asynchronous sending."""
        if record.levelno < self.level:
            return
        log_entry = {
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "name": record.name,
            "file": record.filename,
            "line": record.lineno,
            "process": {"name": record.processName, "id": record.process},
            "thread": {"name": record.threadName, "id": record.thread},
        }
        self.log_queue.put(str(log_entry))

    def process_logs(self):
        """Daemon thread function: Collect logs and send in batches."""
        buffer = []

        while not self.stop_event.is_set() or not self.log_queue.empty():
            try:
                log_entry = self.log_queue.get(timeout=7)  # Wait for logs
                buffer.append(log_entry)

                if len(buffer) >= self.buffer_size:
                    self.flush_logs(buffer)
                    buffer.clear()

            except queue.Empty:
                # If queue is empty, periodically flush remaining logs
                if buffer:
                    self.flush_logs(buffer)
                    buffer.clear()

    def flush_logs(self, logs):
        """Send logs to the logging server."""
        if not logs:
            return

        logging_endpoint = f"{constants.STORAGE_API.URL}/upload-log"
        payload = {"logs": logs}
        headers = {"Authorization": self.api_key, "Content-Type": "application/json"}

        try:
            response = requests.post(logging_endpoint, json=payload, headers=headers)
            response.raise_for_status()
        except requests.RequestException:
            bt.logging.error(
                f"[LOG HANDLER] Failed to send logs: {traceback.format_exc()}"
            )

        bt.logging.debug(f"[LOG HANDLER] Successfully sent {len(logs)} logs")

    def close(self):
        bt.logging.warning(
            "[LOG HANDLER] Handler close() called, but we're ignoring it"
        )


def start_bittensor_log_listener(api_key, buffer_size=100):
    """
    Starts a separate QueueListener that listens to Bittensor's logging queue.
    """
    bt_logger = bt.logging._logger  # The Bittensor logger

    # Add a new queue handler to the Bittensor logger
    log_queue = queue.Queue()  # Get the shared log queue
    bt_logger.addHandler(QueueHandler(log_queue))

    # Create our custom log handler
    custom_handler = BittensorLogHandler(api_key, buffer_size)

    # Create our own listener that listens to the same queue
    custom_listener = QueueListener(
        log_queue, custom_handler, respect_handler_level=True
    )

    # Start our custom listener
    custom_listener.start()

    bt.logging.success("Custom Bittensor log listener started!")
    return custom_listener  # Return the listener so we can stop it if needed
