import os
import json
import time
import random
import hashlib
import datetime
import threading
import traceback
from queue import Empty, Queue
from typing import Callable, Union, Optional
from concurrent.futures import ThreadPoolExecutor

import requests
import bittensor as bt
from diskcache import Cache
from pydantic import BaseModel
from huggingface_hub import HfApi

from redteam_core.validator.models import MinerChallengeCommit

from .. import challenge_pool
from ..constants import constants


class StorageManager:
    def __init__(
        self,
        cache_dir: str,
        validator_request_header_fn: Callable[
            [Union[bytes, str, dict, BaseModel]], str
        ],
        hf_repo_id: str,
        sync_on_init=True,
        squash_hf_repo_on_init=True,
    ):
        """
        Manages local cache, Hugging Face Hub storage, and centralized storage.

        Args:
            cache_dir (str): Path to the local cache directory.
            hf_repo_id (str): ID of the Hugging Face Hub repository.
            sync_on_init (bool): Whether to sync data from the Hub to the local cache during initialization.
        """
        self.active_challenges = challenge_pool.ACTIVE_CHALLENGES
        self.validator_request_header_fn = validator_request_header_fn

        # Decentralized storage on Hugging Face Hub
        self.hf_repo_id = hf_repo_id
        self.hf_api = HfApi()
        bt.logging.info(f"[STORAGE] Authenticated as {self.hf_api.whoami()['name']}")
        self._validate_hf_repo()
        self.update_repo_id()

        # Local cache with disk cache
        os.makedirs(cache_dir, exist_ok=True)
        self.cache_dir = cache_dir
        self.local_caches: dict[Cache] = {}

        # Queue and background thread for async updates
        self._storage_queue = Queue()  # Queue of tuples (data, processing_method)
        self.storage_thread = threading.Thread(
            target=self._process_storage_queue, daemon=True, name="storage_thread"
        )
        self.storage_thread.start()
        bt.logging.info("[STORAGE] Started storage thread in the background")

        # Sync data from Hugging Face Hub to local cache if required
        if sync_on_init:
            bt.logging.info(
                "[STORAGE] Syncing data from Hugging Face Hub to local cache"
            )
            self.sync_storage_to_cache()

        # Squash the HF repo on init if requested to pressure to HF
        if squash_hf_repo_on_init:
            bt.logging.info("[STORAGE] Squashing history of Hugging Face repo")
            self.hf_api.super_squash_history(repo_id=self.hf_repo_id)
            bt.logging.success(
                "[STORAGE] Successfully squashed commit history of Hugging Face repo"
            )

    # MARK: Sync Methods
    def sync_storage_to_cache(self):
        # TODO: Implement sync_storage_to_cache
        pass

    # MARK: Get Methods
    def get_latest_validator_state_from_cache(
        self, validator_uid: int, validator_hotkey: str
    ) -> Optional[dict]:
        """
        Retrieves the latest validator state from local cache for a specific validator.
        Uses the most recent date key to find the latest state.

        Returns:
            Optional[dict]: The latest validator state if found, None otherwise
        """
        try:
            cache = self._get_cache("_validator_state")
            # Get all date keys and sort them in descending order
            validator_keys = [
                key
                for key in cache.iterkeys()
                if key.startswith(f"{validator_hotkey}_")
            ]
            validator_keys.sort(reverse=True)
            if validator_keys:
                return cache[validator_keys[0]]
            return None
        except Exception as e:
            bt.logging.error(f"[STORAGE] Error retrieving latest validator state: {e}")
            return None

    def get_latest_validator_state_from_storage(
        self, validator_uid: int, validator_hotkey: str
    ) -> Optional[dict]:
        """
        Retrieves the latest validator state from centralized storage.
        """
        body = {"validator_uid": validator_uid, "validator_hotkey": validator_hotkey}

        try:
            # First try to fetch state from centralized scoring server with a dummy body tp get latest state from centralized scoring server
            dummy_body = {"subnet": "Redteam"}
            response = requests.post(
                url=f"{constants.STORAGE_API.URL}/fetch-validator-state",
                headers=self.validator_request_header_fn(dummy_body),
                json=dummy_body,
                timeout=60,
            )

            # If that fails, fall back to fetching the state using our own body
            if response.status_code != 200:
                bt.logging.warning(
                    "[STORAGE] Failed to fetch validator state from centralized scoring server, trying fallback."
                )

                response = requests.post(
                    url=f"{constants.STORAGE_API.URL}/fetch-validator-state",
                    headers=self.validator_request_header_fn(body),
                    json=body,
                    timeout=60,
                )

            # If successful, return the state
            response.raise_for_status()
            state = response.json().get("data")
            if state:
                bt.logging.success(
                    f"[STORAGE] Successfully retrieved validator state from centralized storage for validator {validator_uid}, hotkey: {validator_hotkey}"
                )
                return state
            else:
                bt.logging.error(
                    f"[STORAGE] Validator state not found in centralized storage for validator {validator_uid}, hotkey: {validator_hotkey}"
                )
        except Exception as e:
            bt.logging.error(
                f"[STORAGE] Error retrieving validator state from centralized storage: {e}"
            )

        return None

    # MARK: Update Methods
    def update_commit(
        self,
        commit: MinerChallengeCommit,
        async_update: bool = True,
        retry_config: dict = None,
    ):
        """
        Updates or inserts a commit across all storages with independent retries.

        Args:
            commit (MinerChallengeCommit): The commit data to be updated.
            async_update (bool): Whether to process the update asynchronously.
            retry_config (dict, optional): Retry configuration for each storage type.
        """
        if async_update:
            self._storage_queue.put((commit, "update_commit"))
            bt.logging.debug(
                f"[STORAGE] Commit with encrypted_commit={commit.encrypted_commit} queued for storage."
            )
            return

        # Process the commit immediately
        if retry_config is None:
            retry_config = {"local": 3, "centralized": 3, "decentralized": 3}

        challenge_name = commit.challenge_name
        hashed_cache_key = self.hash_cache_key(commit.encrypted_commit)
        data_dict = commit.model_dump()  # Convert to serializable dict

        # Check if update is needed
        if self._compare_record_to_cache(challenge_name, hashed_cache_key, data_dict):
            # 20% chance to update anyway
            if random.random() < 0.2:
                bt.logging.debug(
                    f"[STORAGE] Commit {hashed_cache_key} already exists in local cache for challenge {challenge_name}, but updating anyway."
                )
            else:
                bt.logging.debug(
                    f"[STORAGE] Commit {hashed_cache_key} already exists in local cache for challenge {challenge_name}, skipping update."
                )
                return

        # Track success for all storage operations
        success = True
        errors = []

        # Step 1: Local Cache with retry
        def local_operation():
            cache = self._get_cache(challenge_name)
            cache[hashed_cache_key] = data_dict

        local_success, error = self._retry_operation(
            local_operation, retry_config["local"], "Local cache update"
        )
        if not local_success:
            success = False
            errors.append(error)

        # Step 2: Centralized Storage with retry
        def centralized_operation():
            response = requests.post(
                url=f"{constants.STORAGE_API.URL}/upload-commit",
                headers=self.validator_request_header_fn(data_dict),
                json=data_dict,
                timeout=60,
            )
            response.raise_for_status()

        central_success, error = self._retry_operation(
            centralized_operation,
            retry_config["centralized"],
            "Centralized storage update",
        )
        if not central_success:
            success = False
            errors.append(error)

        # Step 3: HuggingFace Hub with retry
        today = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
        hf_filepath = f"{challenge_name}/{today}/{hashed_cache_key}.json"

        def decentralized_operation():
            self.hf_api.upload_file(
                path_or_fileobj=json.dumps(
                    commit.public_view().model_dump(), indent=4
                ).encode(
                    "utf-8"
                ),  # Hide sensitive data
                path_in_repo=hf_filepath,
                repo_id=self.hf_repo_id,
                commit_message=f"Update commit {hashed_cache_key}",
            )

        hf_success, error = self._retry_operation(
            decentralized_operation,
            retry_config["decentralized"],
            "Decentralized storage update",
        )
        if not hf_success:
            success = False
            errors.append(error)

        # Final Logging
        if success:
            bt.logging.success(
                f"[STORAGE] Commit from challege: {challenge_name}, encrypted_commit: {commit.encrypted_commit}, successfully updated across all storages with key: {hashed_cache_key}"
            )
        else:
            bt.logging.error(
                f"[STORAGE] Failed to update commit from challenge: {challenge_name}, encrypted_commit: {commit.encrypted_commit}, key: {hashed_cache_key}. Errors: {errors}"
            )

    def update_commit_batch(
        self,
        commits: list[MinerChallengeCommit],
        async_update: bool = True,
    ):
        """
        Update a batch of commits across all storages.

        Args:
            commits (list[MinerChallengeCommit]): A list of commits.
            async_update (bool): Whether to process the batch asynchronously.
        """
        if async_update:
            # Enqueue the entire batch along with the processing method
            self._storage_queue.put((commits, "update_commit_batch"))
            bt.logging.debug(
                f"[STORAGE] Batch of size {len(commits)} commits queued for storage"
            )
            return

        # Process each commit synchronously
        def safe_update_commit(commit: MinerChallengeCommit):
            try:
                self.update_commit(commit, async_update=False)
            except Exception:
                bt.logging.error(
                    f"[STORAGE] Error updating commit: {traceback.format_exc()}"
                )

        with ThreadPoolExecutor(max_workers=5) as executor:
            executor.map(safe_update_commit, commits)

    def update_validator_state(self, data: dict, async_update: bool = True):
        """
        Updates validator state in centralized storage and local cache.
        This method does not store data in the HF repo as it contains sensitive information.
        States are stored with UTC date-based keys for better organization and recovery.

        Args:
            data (dict): The validator state data to store
            async_update (bool): Whether to process the update asynchronously
        """
        if async_update:
            self._storage_queue.put((data, "update_validator_state"))
            bt.logging.debug("[STORAGE] Validator state queued for storage")
            return

        # Get current UTC date and time for the key
        current_utc = datetime.datetime.now(datetime.timezone.utc)
        date = current_utc.strftime(
            "%Y-%m-%d_%H-%M-%S"
        )  # Include time for more granular state tracking
        validator_state_key = f"{data['validator_hotkey']}_{date}"

        # Process the state immediately
        retry_config = {"local": 3, "centralized": 3}

        # Step 1: Local Cache with retry
        def local_operation():
            cache = self._get_cache("_validator_state")
            cache[validator_state_key] = data

        local_success, error = self._retry_operation(
            local_operation, retry_config["local"], "Local validator state update"
        )
        if not local_success:
            bt.logging.error(
                f"[STORAGE] Failed to update local validator state: {error}"
            )
            return

        # Step 2: Centralized Storage with retry
        def centralized_operation():
            response = requests.post(
                url=f"{constants.STORAGE_API.URL}/upload-validator-state",
                headers=self.validator_request_header_fn(data),
                json=data,
                timeout=60,
            )
            response.raise_for_status()

        central_success, error = self._retry_operation(
            centralized_operation,
            retry_config["centralized"],
            "Centralized validator state update",
        )
        if not central_success:
            bt.logging.error(
                f"[STORAGE] Failed to update centralized validator state: {error}"
            )
            return

        bt.logging.success(
            f"[STORAGE] Validator state successfully updated in all storages with key {validator_state_key}"
        )

    def update_repo_id(self):
        """
        Updates repository ID to the centralized storage.
        """
        data = {"hf_repo_id": self.hf_repo_id}
        try:
            response = requests.post(
                url=f"{constants.STORAGE_API.URL}/upload-hf-repo-id",
                headers=self.validator_request_header_fn(data),
                json=data,
                timeout=60,
            )
            response.raise_for_status()
            bt.logging.info(
                "[STORAGE] Successfully updated repo_id in centralized storage"
            )
        except Exception as e:
            bt.logging.error(
                f"[STORAGE] Error updating repo_id to centralized storage: {e}"
            )
            raise

    # MARK: Helper Methods
    def hash_cache_key(self, cache_key: str) -> str:
        """
        Hashes the cache key using SHA-256 to avoid Filename too long error.
        """
        return hashlib.sha256(cache_key.encode()).hexdigest()

    def _snapshot_repo(
        self, erase_cache: bool, allow_patterns=None, ignore_patterns=None
    ) -> str:
        """
        Creates a snapshot of the Hugging Face Hub repository in a temporary cache directory.
        """
        hf_cache_dir = os.path.join(self.cache_dir, ".hf_cache/")
        os.makedirs(hf_cache_dir, exist_ok=True)

        # Download the repository snapshot
        return self.hf_api.snapshot_download(
            repo_id=self.hf_repo_id,
            cache_dir=hf_cache_dir,
            force_download=erase_cache,
            allow_patterns=allow_patterns,
            ignore_patterns=ignore_patterns,
        )

    def _validate_hf_repo(self):
        """
        Validates the Hugging Face repository:
        - Ensures the token has write permissions.
        - Confirms the repository exists and meets required attributes.
        - Creates a public repository if it does not exist.
        """
        # Get user info and auth details
        user_info = self.hf_api.whoami()
        auth_info = user_info.get("auth", {}).get("accessToken", {})
        token_role = auth_info.get("role")
        repo_namespace, repo_name = self.hf_repo_id.split("/")

        # Step 1: Check permissions and accessible namespaces
        if token_role == "write":
            allowed_namespaces = {user_info["name"]} | {
                org["name"]
                for org in user_info.get("orgs", [])
                if org.get("roleInOrg") == "write"
            }
            if repo_namespace not in allowed_namespaces:
                raise PermissionError(
                    f"Token does not grant write access to the namespace '{repo_namespace}'. Accessible namespaces: {allowed_namespaces}."
                )
        elif token_role == "fineGrained":
            # For fine-grained tokens, check permissions hierarchically
            fine_grained = auth_info.get("fineGrained", {})
            has_write_access = False

            # Check there's a specific permission for this repo
            for scope in fine_grained.get("scoped", []):
                entity = scope.get("entity", {})
                entity_name = entity.get("name", "")

                # Exact repo match has highest priority
                if entity_name == self.hf_repo_id:
                    has_write_access = "repo.write" in scope.get("permissions", [])
                    break
                # Namespace match (user/org) is checked if no exact match is found
                elif entity_name == repo_namespace:
                    has_write_access = "repo.write" in scope.get("permissions", [])

            # Only check global permissions if no scoped permissions were found
            if not has_write_access:
                has_write_access = "repo.write" in fine_grained.get("global", [])

            if not has_write_access:
                raise PermissionError(
                    f"Fine-grained token does not have write permissions for repository '{self.hf_repo_id}'"
                )
        else:
            raise PermissionError(
                f"Token has insufficient permissions. Expected 'write' or 'fineGrained', got '{token_role}'"
            )

        bt.logging.info(
            f"[STORAGE] Token has write permissions for repository '{self.hf_repo_id}'"
        )

        # Step 2: Validate or create the repository
        try:
            repo_info = self.hf_api.repo_info(repo_id=self.hf_repo_id)
            if repo_info.private or repo_info.disabled:
                raise ValueError(
                    f"Repository '{self.hf_repo_id}' be public and not disabled."
                )
            bt.logging.info(
                f"[STORAGE] Repository '{self.hf_repo_id}' exists and is public."
            )
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:  # Repo does not exist
                bt.logging.warning(
                    f"[STORAGE] Repository '{self.hf_repo_id}' does not exist. Attempting to create it."
                )
                try:
                    self.hf_api.create_repo(
                        repo_id=self.hf_repo_id, private=False, exist_ok=True
                    )
                    bt.logging.info(
                        f"[STORAGE] Repository '{self.hf_repo_id}' has been successfully created."
                    )
                except Exception as create_err:
                    raise RuntimeError(
                        f"Failed to create repository '{self.hf_repo_id}': {create_err}"
                    )
            else:
                raise RuntimeError(
                    f"Error validating repository '{self.hf_repo_id}': {e}"
                )

    def _get_cache(self, cache_name: str) -> Cache:
        """
        Returns the diskcache instance for a specific name.
        Sets TTL only for challenge caches, no expiration for other caches.

        Args:
            cache_name (str): The name of the cache (e.g., challenge name, "_repo_ids", "_validator_state")

        Returns:
            Cache: The cache instance
        """
        if cache_name not in self.local_caches:
            cache_path = os.path.join(self.cache_dir, cache_name)
            cache = Cache(cache_path, eviction_policy="none")
            self.local_caches[cache_name] = cache
        return self.local_caches[cache_name]

    def _process_storage_queue(self):
        """
        Background thread function to process storage tasks from the queue.
        All tasks are tuples of (data, method) where method is a string identifier.
        """
        while True:
            try:
                data, method = self._storage_queue.get(timeout=1)  # Wait for a task

                if method == "update_commit":
                    self.update_commit(data, async_update=False)
                elif method == "update_validator_state":
                    self.update_validator_state(data, async_update=False)
                elif method == "update_commit_batch":
                    self.update_commit_batch(data, async_update=False)
                else:
                    bt.logging.warning(f"[STORAGE] Unknown processing method: {method}")
            except Empty:
                bt.logging.debug(
                    "[STORAGE] No tasks in the queue, keeping the thread alive"
                )
            except Exception:
                bt.logging.warning(
                    f"[STORAGE] Error processing storage queue: {traceback.format_exc()} when processing task: {method}, abort this one"
                )

            time.sleep(1)  # Prevent the thread from consuming too much CPU

    def _compare_record_to_cache(
        self, cache_name: str, cache_key: str, record: dict
    ) -> bool:
        """
        Compares a record to the cache and returns True if the record is already in the cache with the same data, False otherwise.
        """
        try:
            # Get cache and existing record
            cache = self._get_cache(cache_name)
            existing_record = cache.get(cache_key)

            # Early return if no existing record or wrong type
            if not isinstance(existing_record, dict) or not isinstance(record, dict):
                return False

            # Compare serialized versions
            existing_record_str = json.dumps(existing_record, sort_keys=True)
            record_str = json.dumps(record, sort_keys=True)
            return existing_record_str == record_str

        except (TypeError, KeyError, json.JSONDecodeError) as e:
            bt.logging.error(f"[STORAGE] Error comparing records: {str(e)}")
            return False
        except Exception as e:
            bt.logging.error(f"[STORAGE] Unexpected error comparing records: {str(e)}")
            return False

    def _retry_operation(
        self, operation, max_retries: int, operation_name: str
    ) -> tuple[bool, str]:
        """
        Helper method to retry operations with exponential backoff.

        Args:
            operation (callable): Function to retry
            max_retries (int): Maximum number of retry attempts
            operation_name (str): Name of operation for logging

        Returns:
            tuple[bool, str]: (success status, error message if any)
                - First element is True if operation succeeded, False otherwise
                - Second element is empty string on success, error message on failure
        """
        last_error = None
        for attempt in range(max_retries):
            try:
                operation()
                return True, ""
            except Exception as e:
                last_error = str(e)
                if attempt == max_retries - 1:
                    break
                wait_time = min(5**attempt, 32)  # Exponential backoff
                bt.logging.warning(
                    f"[STORAGE] {operation_name} attempt {attempt + 1} failed, retrying in {wait_time}s: {last_error}"
                )
                time.sleep(wait_time)

        error_msg = f"{operation_name} failed after {max_retries} attempts. Last error: {last_error}"
        return False, error_msg
