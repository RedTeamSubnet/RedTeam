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
                if current_time.tm_min % constants.VALIDATOR.UPDATE_RATE_MINUTES == 0:
                    self._check_for_updates()
                    time.sleep(60)
                else:
                    sleep_minutes = (
                        constants.VALIDATOR.UPDATE_RATE_MINUTES
                        - current_time.tm_min % constants.VALIDATOR.UPDATE_RATE_MINUTES
                    )
                    bt.logging.info(f"Sleeping for {sleep_minutes} minutes")
                    time.sleep(sleep_minutes * 60 - current_time.tm_sec)
            except Exception as e:
                bt.logging.error(f"Error occurred while checking for updates: {e}")
                max_retries = 5
                backoff_time = 1  # Start with 1 second
                for attempt in range(1, max_retries + 1):
                    bt.logging.info(
                        f"Retrying in {backoff_time} seconds (attempt {attempt}/{max_retries})..."
                    )
                    time.sleep(backoff_time)
                    try:
                        self._check_for_updates()
                        bt.logging.info("Retry successful.")
                        break
                    except Exception as retry_error:
                        bt.logging.error(f"Retry {attempt} failed: {retry_error}")
                        backoff_time *= 2  # Exponential backoff
                else:
                    bt.logging.error("All retry attempts failed. Restarting process.")
                    self._stop_flag.set()
                    self._restart_process()

    def _check_for_updates(self):
        try:
            repo = git.Repo(search_parent_directories=True)
            current_version = repo.head.commit.hexsha

            # Fetch latest changes
            repo.remotes.origin.fetch()
            branch_name = constants.VALIDATOR.UPDATE_BRANCH_NAME
            new_version = repo.remotes.origin.refs[branch_name].commit.hexsha

            if current_version != new_version:
                bt.logging.info(f"New version detected: '{new_version}'. Restarting...")
                try:
                    # Attempt a clean pull first
                    repo.git.pull("origin", branch_name, strategy_option="theirs")
                except Exception as e:
                    bt.logging.warning(f"Pull failed: {e}. Trying soft reset.")
                    # Force update to remote state if pull fails
                    try:
                        repo.git.reset("--soft", f"origin/{branch_name}")
                        repo.remotes.origin.fetch()
                        repo.git.merge(
                            f"origin/{branch_name}", "--no-edit", "-X", "theirs"
                        )

                    except Exception as e:
                        bt.logging.warning(
                            f"Soft reset failed: {e}. Trying hard reset."
                        )
                        repo.git.reset("--hard", f"origin/{branch_name}")
                        repo.git.clean("-fd")  # Remove untracked files if needed
                        repo.remotes.origin.fetch()
                        repo.git.merge(
                            f"origin/{branch_name}", strategy_option="theirs"
                        )
                final_version = repo.head.commit.hexsha
                if final_version != new_version:
                    bt.logging.warning("Update did not complete successfully.")
                self._stop_flag.set()
                self._restart_process()
            else:
                bt.logging.info(
                    f"Already up to date. Branch: `{branch_name}` Version: {current_version}"
                )
        except Exception as e:
            bt.logging.error(f"Update check failed: {e}")

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
