import time
from threading import Event, Thread
import git
import bittensor as bt
import os
import signal
from redteam_core.constants import constants


class AutoUpdater:
    def __init__(self):
        self._stop_flag = Event()
        self._thread = Thread(target=self._monitor, daemon=True)
        self._check_for_updates()
        self._thread.start()

    def _monitor(self):
        while not self._stop_flag.is_set():
            bt.logging.info("Checking for updates...")

            try:
                current_time = time.localtime()
                if current_time.tm_min % constants.UPDATE_RATE_MINUTES == 0:
                    self._check_for_updates()
                    time.sleep(60)
                else:
                    sleep_minutes = (
                        constants.UPDATE_RATE_MINUTES
                        - current_time.tm_min % constants.UPDATE_RATE_MINUTES
                    )
                    bt.logging.info(f"Sleeping for {sleep_minutes} minutes")
                    time.sleep(sleep_minutes * 60 - current_time.tm_sec)
            except Exception as e:
                bt.logging.error(f"Error occurred while checking for updates: {e}")
                self._stop_flag.set()
                self._restart_process()

    def _check_for_updates(self):
        repo = git.Repo(search_parent_directories=True)
        current_version = repo.head.commit.hexsha

        # Fetch latest changes from remote
        repo.remotes.origin.fetch()

        # Get the latest commit hash from origin/main
        new_version = repo.remotes.origin.refs.main.commit.hexsha

        if current_version != new_version:
            repo.remotes.origin.pull("validator-autoupdate", strategy_option="theirs")
            bt.logging.info(f"New version detected: '{new_version}'. Restarting...")
            self._stop_flag.set()
            self._restart_process()
        else:
            bt.logging.info("Already up to date.")

    def _restart_process(self):
        """Restart the current process by sending SIGTERM to itself"""
        time.sleep(5)
        os.kill(os.getpid(), signal.SIGTERM)

        bt.logging.info("Waiting for process to terminate...")
        for _ in range(60):
            time.sleep(1)
            try:
                os.kill(os.getpid(), 0)
            except ProcessLookupError:
                break

        # If we're still running after 60 seconds, use SIGKILL
        os.kill(os.getpid(), signal.SIGKILL)
