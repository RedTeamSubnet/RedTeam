import logging
import threading
import requests
import time
from collections import deque

class ValidatorLogHandler(logging.Handler):
    def __init__(self, storage_url, api_key, buffer_size=10, flush_interval=5):
        """Custom log handler for Bittensor logger that buffers logs and sends them periodically."""
        super().__init__()
        self.storage_url = storage_url  # API endpoint for log storage
        self.api_key = api_key  # Authentication key
        self.buffer_size = buffer_size  # Max number of logs before sending
        self.flush_interval = flush_interval  # Time interval for forced flush
        self.buffer = deque()  # Buffer to store logs
        self.lock = threading.Lock()  # Prevent race conditions

        # Start the background flushing thread
        self.flush_thread = threading.Thread(target=self._flush_loop, daemon=True)
        self.flush_thread.start()

    def emit(self, record):
        """Capture log and add it to the buffer without reformatting."""
        log_entry = self.format(record) if self.formatter else record.getMessage()

        with self.lock:
            self.buffer.append(log_entry)

            # If buffer reaches size limit, send logs
            if len(self.buffer) >= self.buffer_size:
                self.flush_logs()

    def flush_logs(self):
        """Send buffered logs to storage."""
        with self.lock:
            if not self.buffer:
                return  # No logs to send

            logs_to_send = list(self.buffer)
            self.buffer.clear()  # Clear buffer after copying

        payload = {"logs": logs_to_send}
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

        try:
            response = requests.post(self.storage_url, json=payload, headers=headers)
            response.raise_for_status()
        except requests.RequestException as e:
            print(f"Failed to send logs: {e}")

    def _flush_loop(self):
        """Periodically flush logs to ensure they are sent even if buffer is not full."""
        while True:
            time.sleep(self.flush_interval)
            self.flush_logs()

    def close(self):
        """Flush remaining logs before shutting down."""
        self.flush_logs()
        super().close()
