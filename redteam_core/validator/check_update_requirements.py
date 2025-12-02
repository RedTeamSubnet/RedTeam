import os
import signal
import subprocess, sys
import time

import bittensor as bt


class UpdateRequirementsRestart:
    def __init__(self, requirements_path: str = None):
        if requirements_path:
            self.url = requirements_path
        else:
            self.url = "https://raw.githubusercontent.com/RedTeamSubnet/RedTeam/refs/heads/main/requirements.txt"

    def run(self):
        old_requirements = self._get_freeze_output()
        bt.logging.info("Installing updated requirements...")
        self._install_requirements(self.url)
        new_requirements = self._get_freeze_output()
        is_same, diff = self._is_package_same(old_requirements, new_requirements)
        if not is_same:
            bt.logging.info(
                "Requirements updated. The following packages were changed:"
            )
            for pkg in diff:
                bt.logging.info(f" - {pkg}")
            bt.logging.critical("Restarting to apply changes...")
            self._restart_process()
        else:
            bt.logging.info("No changes in requirements detected.")

    def _get_freeze_output(self):
        cmd = [
            sys.executable,
            "-m",
            "pip",
            "freeze",
            "--disable-pip-version-check",
            "--no-input",
        ]
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        return result.stdout

    def _install_requirements(self, url: str):
        cmd = [
            sys.executable,
            "-m",
            "pip",
            "install",
            "-r",
            str(self.url),
            "--disable-pip-version-check",
            "--no-input",
        ]
        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            bt.logging.error("\nPip install error output:")
            bt.logging.error(e.stderr)
        return result.stdout

    def _is_package_same(self, old: str, new: str) -> tuple[bool, list[str]]:
        old_packages = set(old.strip().splitlines())
        new_packages = set(new.strip().splitlines())
        return old_packages == new_packages, list(new_packages - old_packages)

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
