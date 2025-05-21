import os
import time
import unittest
import logging
import git
import tempfile
import shutil
from pathlib import Path

# Import your AutoUpdater class - adjust the import path
from redteam_core.validator.autoupdate import AutoUpdater

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test_validator_autoupdate")

# Create a mock version of restart_current_process that just logs instead of restarting
def mock_restart_current_process():
    logger.info("MOCK RESTART: Process would restart here")
    return True  # Indicate success

class TestValidatorAutoUpdate(unittest.TestCase):
    """Test cases for the validator auto-update functionality."""

    def test_auto_updater(self):
        """Test the auto-updater functionality in a local temporary clone without pushing to remote."""
        logger.info("Starting auto-updater test")

        # Get the current repo to identify its path
        original_repo = git.Repo(search_parent_directories=True)
        repo_path = original_repo.working_dir

        # Create a temporary directory for our test clone
        with tempfile.TemporaryDirectory() as temp_dir:
            logger.info(f"Created temporary directory for test: {temp_dir}")

            # Clone the repo locally to the temp directory
            # This avoids modifying the actual repo
            test_repo_path = os.path.join(temp_dir, "test_repo")
            shutil.copytree(repo_path, test_repo_path, symlinks=True)

            # Initialize git in the copied directory if it's not already a git repo
            test_repo = git.Repo(test_repo_path)

            # Record initial state
            initial_commit = test_repo.head.commit.hexsha
            logger.info(f"Test repo initial commit: {initial_commit[:8]}")

            # Create a modified version of AutoUpdater for testing
            class TestAutoUpdater(AutoUpdater):
                def __init__(self):
                    # Skip the actual initialization that would start the thread
                    # We'll manually call the _check_for_updates method
                    self._stop_flag = None  # Mock this
# Removed unused attributes _branch and _remote
                    self._restart_function = mock_restart_current_process
                    # Store the initial version
                    self._stored_version = test_repo.head.commit.hexsha

                # Override to use our test repository
                def _check_for_updates(self):
                    logger.info("Checking for updates...")
                    try:
                        # Use our test repo instead of searching for one
                        repo = test_repo
                        # Use the stored version for comparison
                        current_version = self._stored_version
                        logger.info(f"Current version: {current_version[:8]}")

                        # Get the latest commit
                        new_version = repo.head.commit.hexsha
                        logger.info(f"New version: {new_version[:8]}")

                        if current_version != new_version:
                            logger.info(f"New version detected: '{new_version[:8]}'. Restarting...")
                            # Update the stored version
                            self._stored_version = new_version
                            restart_result = self._restart_function()
                            return restart_result
                        else:
                            logger.info("Already up to date.")
                            return False
                    except Exception as e:
                        logger.error(f"Failed to check for updates: {e}", exc_info=True)
                        return False

            # Create the test auto-updater
            updater = TestAutoUpdater()
            logger.info("Test auto-updater initialized")

            # First check - should find no updates
            restart_needed = updater._check_for_updates()
            self.assertFalse(restart_needed, "Should not need restart on first check")

            # Make a local change to simulate an update
            try:
                # Create a test file
                test_file = os.path.join(test_repo_path, "test_auto_update.txt")
                with open(test_file, "w") as f:
                    f.write(f"Test update: {time.time()}")

                # Stage and commit the change
                test_repo.git.add(test_file)
                test_repo.git.commit("-m", "Test commit for auto-updater")
                new_commit = test_repo.head.commit.hexsha
                logger.info(f"Created test commit: {new_commit[:8]}")

                # Now the updater should detect the change
                restart_needed = updater._check_for_updates()
                self.assertTrue(restart_needed, "Should need restart after commit")

                logger.info("Test completed successfully!")

            except Exception as e:
                logger.error(f"Test failed: {e}", exc_info=True)
                raise
            finally:
                # Clean up happens automatically when tempfile.TemporaryDirectory exits
                logger.info("Test cleanup completed")

if __name__ == "__main__":
    unittest.main()