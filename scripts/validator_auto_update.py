import os
import subprocess
import time
import argparse
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('validator_autoupdate.log'),
        logging.StreamHandler()
    ]
)

def get_process_status(process_name):
    """Check if the validator process is running using pm2"""
    try:
        result = subprocess.run(['pm2', 'jlist'], capture_output=True, text=True)
        if result.returncode == 0:
            import json
            processes = json.loads(result.stdout)
            for proc in processes:
                if proc['name'] == process_name:
                    return proc['pm2_env']['status']
        return None
    except Exception as e:
        logging.error(f"Error checking process status: {e}")
        return None

def restart_process(process_name):
    """Restart the validator process using pm2"""
    try:
        subprocess.run(['pm2', 'restart', process_name], check=True)
        logging.info(f"Successfully restarted {process_name}")
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to restart {process_name}: {e}")

def should_update_local(local_commit, remote_commit):
    """Check if local repository needs updating"""
    return local_commit != remote_commit

def has_package_changes(remote_commit):
    """Check if there are changes in package configuration files between current and remote"""
    try:
        # Get list of changed files between current HEAD and remote
        diff_output = subprocess.getoutput(f"git diff HEAD..{remote_commit} --name-only")
        changed_files = diff_output.splitlines()

        # Only check for package configuration files
        package_related_changes = any(
            file in ['setup.py', 'requirements.txt', 'pyproject.toml']
            for file in changed_files
        )
        return package_related_changes
    except Exception as e:
        logging.error(f"Error checking package changes: {e}")
        return True  # Return True on error to be safe

def should_restart_self(remote_commit):
    """Check if this auto-updater script has been modified"""
    try:
        diff_output = subprocess.getoutput(f"git diff HEAD..{remote_commit} --name-only")
        changed_files = diff_output.splitlines()
        return "scripts/validator_auto_update.py" in changed_files
    except Exception as e:
        logging.error(f"Error checking for self updates: {e}")
        return False

def run_auto_updater(validator_process_name, process_name, check_interval=300):
    """Main auto-updater function"""
    logging.info("Starting validator auto-updater...")

    while True:
        try:
            logging.info("Checking for updates...")

            # Get current branch and commit information
            current_branch = subprocess.getoutput("git rev-parse --abbrev-ref HEAD")
            local_commit = subprocess.getoutput("git rev-parse HEAD")

            # Fetch latest changes
            subprocess.run(["git", "fetch"], check=True)
            remote_commit = subprocess.getoutput(f"git rev-parse origin/{current_branch}")

            if should_update_local(local_commit, remote_commit):
                logging.info("Updates available. Starting update process...")

                # Check if we need to restart ourselves
                self_update_needed = should_restart_self(remote_commit)

                # Stash any local changes
                subprocess.run(["git", "stash"], check=True)

                # Reset to latest commit
                subprocess.run(["git", "reset", "--hard", remote_commit], check=True)

                # Only reinstall if there are package-related changes
                if has_package_changes(remote_commit):
                    logging.info("Package changes detected, reinstalling...")
                    subprocess.run(["pip", "install", "-e", "."], check=True)
                else:
                    logging.info("No package changes detected, skipping reinstall")

                # Restart validator process
                restart_process(validator_process_name)

                # Check if process is running correctly
                time.sleep(15)  # Wait for process to stabilize
                status = get_process_status(validator_process_name)
                if status == "errored":
                    logging.warning(f"{validator_process_name} is in error state, attempting another restart...")
                    restart_process(validator_process_name)

                if self_update_needed:
                    logging.info("Auto-updater script has changed, restarting self...")
                    restart_process(process_name)
                    return  # Exit after requesting our own restart

                logging.info("Update completed successfully!")
            else:
                logging.info("Repository is up-to-date")

        except Exception as e:
            logging.error(f"Error during update process: {e}")

        time.sleep(check_interval)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Auto-updater for RedTeam Subnet validator")
    parser.add_argument("--validator-process-name", default="validator_snxxx",
                      help="PM2 process name of the validator")
    parser.add_argument("--process-name", default="validator_autoupdate",
                      help="PM2 process name of the auto-updater")
    parser.add_argument("--interval", type=int, default=3600,
                      help="Check interval in seconds (default: 3600)")

    args = parser.parse_args()

    run_auto_updater(args.validator_process_name, args.process_name, args.interval)