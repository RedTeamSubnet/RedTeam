import hashlib
import time
import datetime
import queue
import json
import logging
import traceback
import threading
from logging.handlers import QueueHandler, QueueListener

import requests

import bittensor as bt

from redteam_core.constants import constants


class BittensorLogHandler(logging.Handler):
    def __init__(
        self,
        validator_uid,
        validator_hotkey,
        keypair,
        buffer_size=100,
        level=logging.DEBUG,
    ):
        super().__init__(level)
        self.validator_uid = validator_uid
        self.validator_hotkey = validator_hotkey
        self.keypair = keypair
        self.buffer_size = buffer_size
        self.log_queue = queue.Queue()
        self.stop_event = threading.Event()  # Used to stop the thread gracefully

        self.api_key = None
        self.api_key_lock = threading.Lock()

        self._refresh_api_key()

        self.setFormatter(bt.logging._file_formatter)

        # Start the daemon thread for sending logs
        self.sender_thread = threading.Thread(target=self.process_logs, daemon=True)
        self.sender_thread.start()

    def _refresh_api_key(self):
        """Get a fresh API key from the storage server."""
        try:
            endpoint = f"{constants.STORAGE_API.URL}/get-api-key"
            data = {
                "validator_uid": self.validator_uid,
                "validator_hotkey": self.validator_hotkey,
            }
            body_hash = hashlib.sha256(json.dumps(data).encode("utf-8")).hexdigest()

            # Create signed headers for the API key request
            timestamp = str(int(time.time_ns()))
            signature = "0x" + self.keypair.sign(f"{body_hash}.{timestamp}").hex()

            headers = {
                "validator-uid": str(self.validator_uid),
                "validator-hotkey": self.validator_hotkey,
                "timestamp": timestamp,
                "signature": signature,
            }

            response = requests.post(endpoint, json=data, headers=headers, timeout=30)
            response.raise_for_status()

            with self.api_key_lock:
                self.api_key = response.json()["api_key"]

            bt.logging.success(f"[LOG HANDLER] Successfully refreshed API key")

        except Exception as e:
            bt.logging.error(f"[LOG HANDLER] Failed to refresh API key: {e}")

    def emit(self, record):
        """Capture log and enqueue it for asynchronous sending."""
        if record.levelno < self.level:
            return
        log_entry = {
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "level_no": record.levelno,
            "name": record.name,
            "file": record.filename,
            "line": record.lineno,
            "process": {"name": record.processName, "id": record.process},
            "thread": {"name": record.threadName, "id": record.thread},
        }
        self.log_queue.put(json.dumps(log_entry))

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
                if buffer:
                    self.flush_logs(buffer)
                    buffer.clear()

    def flush_logs(self, logs):
        """Send logs to the logging server with auto-retry on 401."""
        if not logs:
            return

        logging_endpoint = f"{constants.STORAGE_API.URL}/upload-log"
        payload = {"logs": logs}

        # Use current API key
        with self.api_key_lock:
            current_api_key = self.api_key

        if not current_api_key:
            bt.logging.warning(
                "[LOG HANDLER] No API key available, skipping log upload"
            )
            return

        headers = {"Authorization": current_api_key, "Content-Type": "application/json"}

        try:
            response = requests.post(
                logging_endpoint, json=payload, headers=headers, timeout=30
            )
            response.raise_for_status()
            bt.logging.debug(f"[LOG HANDLER] Successfully sent {len(logs)} logs")

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                # API key expired/invalid, refresh and retry once
                bt.logging.warning("[LOG HANDLER] API key expired (401), refreshing...")
                self._refresh_api_key()

                # Retry with new key
                with self.api_key_lock:
                    new_api_key = self.api_key

                if new_api_key:
                    headers["Authorization"] = new_api_key
                    try:
                        retry_response = requests.post(
                            logging_endpoint, json=payload, headers=headers, timeout=30
                        )
                        retry_response.raise_for_status()
                        bt.logging.debug(
                            f"[LOG HANDLER] Successfully sent {len(logs)} logs after API key refresh"
                        )
                    except Exception as retry_e:
                        bt.logging.error(
                            f"[LOG HANDLER] Failed to send logs even after API key refresh: {retry_e}"
                        )
                else:
                    bt.logging.error(
                        "[LOG HANDLER] Failed to refresh API key, logs will be lost"
                    )
            else:
                bt.logging.error(
                    f"[LOG HANDLER] HTTP error {e.response.status_code}: {e}"
                )

        except requests.RequestException as e:
            bt.logging.error(f"[LOG HANDLER] Failed to send logs: {e}")

    def close(self):
        bt.logging.warning(
            "[LOG HANDLER] Handler close() called, but we're ignoring it"
        )


def start_bittensor_log_listener(
    validator_uid, validator_hotkey, keypair, buffer_size=100
):
    """
    Starts a separate QueueListener that listens to Bittensor's logging queue.
    """
    bt_logger = bt.logging._logger  # The Bittensor logger

    # Add a new queue handler to the Bittensor logger
    log_queue = queue.Queue()  # Get the shared log queue
    bt_logger.addHandler(QueueHandler(log_queue))

    # Create our custom log handler
    custom_handler = BittensorLogHandler(
        validator_uid, validator_hotkey, keypair, buffer_size
    )

    # Create our own listener that listens to the same queue
    custom_listener = QueueListener(
        log_queue, custom_handler, respect_handler_level=True
    )

    # Start our custom listener
    custom_listener.start()

    bt.logging.success("Custom Bittensor log listener started!")
    return custom_listener  # Return the listener so we can stop it if needed
