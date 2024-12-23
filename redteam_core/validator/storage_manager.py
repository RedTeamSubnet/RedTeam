import os
import time
import json
import requests
import threading
import hashlib
from shutil import rmtree
from queue import Queue, Empty
from collections import defaultdict
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

import bittensor as bt
from diskcache import Cache
from huggingface_hub import HfApi

from ..constants import constants


class StorageManager:
    def __init__(self, cache_dir: str, hf_repo_id: str, sync_on_init=True):
        """
        Manages local cache, Hugging Face Hub storage, and centralized storage.

        Args:
            cache_dir (str): Path to the local cache directory.
            hf_repo_id (str): ID of the Hugging Face Hub repository.
            sync_on_init (bool): Whether to sync data from the Hub to the local cache during initialization.
        """

        # Decentralized storage on Hugging Face Hub
        self.hf_repo_id = hf_repo_id
        self.hf_api = HfApi()
        bt.logging.info(f"Authenticated as {self.hf_api.whoami()['name']}")
        self._validate_hf_repo()

        # Local cache with disk cache
        self.cache_dir = cache_dir
        self.cache_ttl = int(timedelta(days=14).total_seconds()) # TTL set equal to a decaying period
        self.local_caches: dict[Cache] = {}
        self.centralized_submission_storage_url = constants.STORAGE_URL + "/upload-submission"
        self.centralized_challenge_records_storage_url = constants.STORAGE_URL + "/upload-challenge-records"
        self.centralized_repo_id_storage_url = constants.STORAGE_URL + "/upload-hf-repo-id"
        # Queue and background thread for async updates
        self.storage_queue = Queue()
        self.storage_thread = threading.Thread(target=self._process_storage_queue, daemon=True)
        self.storage_thread.start()

        # Start periodic cache-to-hub synchronization
        self.sync_thread = threading.Thread(
            target=self._sync_cache_to_hub_periodically,
            kwargs={"interval": 3600},
            daemon=True
        )
        self.sync_thread.start()

        os.makedirs(self.cache_dir, exist_ok=True)

        # Sync data from Hugging Face Hub to local cache if required
        if sync_on_init:
            self.sync_hub_to_cache()

    def _validate_hf_repo(self):
        """
        Validates the Hugging Face repository:
        - Ensures the token has write permissions.
        - Confirms the repository exists and meets required attributes.
        - Creates a public repository if it does not exist.
        """
        # Step 1: Ensure token has write permissions
        permission = self.hf_api.get_token_permission()
        if permission != "write":
            raise PermissionError(f"Token does not have sufficient permissions for repository {self.hf_repo_id}. Current permission: {permission}.")
        bt.logging.info("Token has write permissions.")

        # Step 2: Check accessible namespaces (users/orgs)
        user_info = self.hf_api.whoami()
        allowed_namespaces = {user_info["name"]} | {org["name"] for org in user_info["orgs"] if org["roleInOrg"] == "write"}
        repo_namespace, _ = self.hf_repo_id.split("/")
        if repo_namespace not in allowed_namespaces:
            raise PermissionError(f"Token does not grant write access to the namespace '{repo_namespace}'. Accessible namespaces: {allowed_namespaces}.")
        bt.logging.info(f"Namespace '{repo_namespace}' is accessible with write permissions.")

        # Step 3: Validate or create the repository
        try:
            repo_info = self.hf_api.repo_info(repo_id=self.hf_repo_id)
            if repo_info.private:
                raise ValueError(f"Repository '{self.hf_repo_id}' is private but must be public.")
            bt.logging.info(f"Repository '{self.hf_repo_id}' exists and is public.")
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:  # Repo does not exist
                bt.logging.warning(f"Repository '{self.hf_repo_id}' does not exist. Attempting to create it.")
                try:
                    self.hf_api.create_repo(repo_id=self.hf_repo_id, private=False, exist_ok=True)
                    bt.logging.info(f"Repository '{self.hf_repo_id}' has been successfully created.")
                except Exception as create_err:
                    raise RuntimeError(f"Failed to create repository '{self.hf_repo_id}': {create_err}")
            else:
                raise RuntimeError(f"Error validating repository '{self.hf_repo_id}': {e}")

    def _get_cache(self, challenge_name: str) -> Cache:
        """
        Returns the diskcache instance for a specific challenge, with a expiration policy.

        Args:
            challenge_name (str): The name of the challenge.

        Returns:
            Cache: The cache instance.
        """
        if challenge_name not in self.local_caches:
            challenge_cache_path = os.path.join(self.cache_dir, challenge_name)
            cache = Cache(challenge_cache_path, eviction_policy="none")
            cache.expire = self.cache_ttl
            self.local_caches[challenge_name] = cache
        return self.local_caches[challenge_name]

    def sync_hub_to_cache(self, erase_local_cache=True):
        """
        Syncs data from Hugging Face Hub to the local cache.
        This method will fetch data from the last 14 days from the Hugging Face Hub and build the cache accordingly.

        Args:
            erase_local_cache (bool): Whether to erase the local cache before syncing.
        """
        # Erase the existing local cache if needed
        if erase_local_cache and os.path.exists(self.cache_dir):
            rmtree(self.cache_dir)
            os.makedirs(self.cache_dir, exist_ok=True)

        # Get the list of the last 14 days' date strings in the format 'YYYY-MM-DD' and create allow patterns
        date_strings = [(datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(14)]
        allow_patterns = [f"*{date_str}/*" for date_str in date_strings]
        # Download the snapshot
        repo_snapshot_path = self._snapshot_repo(erase_cache=False, allow_patterns=allow_patterns)

        if not os.path.isdir(repo_snapshot_path):
            bt.logging.info(f"No data on the Hub for the last 14 days, skip sync.")
            return

        # Build a temporary dict
        all_records = defaultdict(dict)
        for challenge_name in os.listdir(repo_snapshot_path):
            challenge_folder_path = os.path.join(repo_snapshot_path, challenge_name)
            
            if not os.path.isdir(challenge_folder_path):
                continue
            for date_str in date_strings:
                date_folder_path = os.path.join(challenge_folder_path, date_str)

                if not os.path.isdir(date_folder_path):
                    continue
                for filename in os.listdir(date_folder_path):
                    if filename.endswith(".json"):
                        key = os.path.splitext(filename)[0]
                        # Add the record to all_records if the key is not already in all_records for this challenge
                        if key not in all_records[challenge_name]:
                            file_path = os.path.join(date_folder_path, filename)
                            with open(file_path, "r") as file:
                                data = json.load(file)
                            all_records[challenge_name][key] = data

        # Populate the local cache with the collected records
        for challenge_name, records in all_records.items():
            cache = self._get_cache(challenge_name)
            for key, data in records.items():
                cache[key] = data

        bt.logging.info(f"Local cache successfully built from the last 14 days of the Hugging Face Hub.")

    def sync_cache_to_hub(self):
        """
        Syncs the local cache to the Hugging Face Hub in batches using `run_as_future`.

        This method ensures:
        1. Records found in the local cache are added to the Hub if not present.
        2. Records in the Hub are updated if they differ from the cache.
        3. Records in the Hub that are not in the cache are left untouched.

        This operation ensures only today's records are updated.

        WARNING: This operation may overwrite existing records in the Hub if differences are detected.

        Returns:
            None
        """
        bt.logging.warning("This operation may alter the Hub repository significantly!")

        # Take a snapshot of the Hugging Face Hub repository
        today = datetime.now().strftime("%Y-%m-%d")
        repo_snapshot_path = self._snapshot_repo(erase_cache=False, allow_patterns=[f"*{today}/*"])

        # Step 1: Build a set of records already in the Hub
        hub_records = {}  # {challenge_name: {key: data}}
        for dirpath, _, filenames in os.walk(repo_snapshot_path):
            relative_dir = os.path.relpath(dirpath, repo_snapshot_path)
            parts = relative_dir.split(os.sep)

            # Skip if not a valid challenge folder or doesn't match today's date
            if len(parts) < 2 or not parts[-2].endswith(today):
                continue

            challenge_name = parts[0]
            hub_records[challenge_name] = {today: {}}

            for filename in filenames:
                if filename.endswith(".json"):
                    file_path = os.path.join(dirpath, filename)
                    with open(file_path, "r") as file:
                        hub_data = json.load(file)

                    key = os.path.splitext(filename)[0]  # Use filename without ".json"
                    hub_records[challenge_name][today][key] = hub_data

        # Step 2: Compare the local cache with the Hub and prepare updates
        upload_futures = []
        for challenge_name, cache in self.local_caches.items():
            for key in cache.iterkeys():
                value = cache[key]
                filepath = f"{challenge_name}/{today}/{key}.json"

                # Determine whether to add or update
                if (
                    challenge_name not in hub_records
                    or today not in hub_records[challenge_name]
                    or key not in hub_records[challenge_name][today]
                    or hub_records[challenge_name][today][key] != value
                ):
                    # Schedule the file upload as a future
                    upload_futures.append(
                        self.hf_api.upload_file(
                            path_or_fileobj=json.dumps(value, indent=4).encode("utf-8"),
                            path_in_repo=filepath,
                            repo_id=self.hf_repo_id,
                            commit_message=f"Sync record {key} for {challenge_name}",
                            run_as_future=True,  # Non-blocking
                        )
                    )

        # Step 3: Wait for all uploads to complete and handle results
        if upload_futures:
            for future in as_completed(upload_futures):
                try:
                    result = future.result()
                    bt.logging.info(f"Uploaded to Hub successfully: {result}")
                except Exception as e:
                    bt.logging.error(f"Failed to upload file to Hub: {e}")
        else:
            bt.logging.info("No updates required. Hub is already in sync with the local cache.")

    def _sync_cache_to_hub_periodically(self, interval: int):
        """
        Periodically syncs the local cache to the Hugging Face Hub.

        Args:
            interval (int): Time interval in seconds between consecutive syncs.
        """
        while True:
            time.sleep(interval)

            try:
                self.sync_cache_to_hub()
                bt.logging.info("Periodic sync to Hugging Face Hub completed successfully.")
            except Exception as e:
                bt.logging.error(f"Error during periodic cache sync: {e}")

    def _snapshot_repo(self, erase_cache: bool, allow_patterns=None, ignore_patterns=None) -> str:
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
            ignore_patterns=ignore_patterns
        )
    
    def update_batch(self, challenge_name: str, records: list[dict]):
        """
        Processes a batch of records, ensuring updates across all storages.

        Args:
            challenge_name (str): The challenge name.
            records (list[dict]): A list of record data dictionaries.
        """
        for record in records:
            try:
                self.update_record(challenge_name, record)
            except ValueError as e:
                bt.logging.error(f"Invalid record skipped: {e}")

    def update_record(self, data: dict, async_update=True):
        """
        Updates or inserts a record across all storages: centralized, local, and decentralized.

        Args:
            data (dict): The record data. Must include "encrypted_commit" and "challenge_name".
            async_update (bool): Whether to process the update asynchronously.
        """
        # Validate required fields in data
        if "encrypted_commit" not in data:
            bt.logging.error("Data must include 'encrypted_commit' as a unique identifier.")
            return
        if "challenge_name" not in data:
            bt.logging.error("Data must include 'challenge_name'.")
            return

        if async_update:
            # Enqueue the task for the background thread
            self.storage_queue.put(data)
            bt.logging.info(f"Record with encrypted_commit={data['encrypted_commit']} queued for storage.")
            return

        # Process the record immediately
        challenge_name = data["challenge_name"]
        hashed_encrypted_commit = self.hash_encrypted_commit(data["encrypted_commit"])

        # Track success for all storage operations
        success = True
        errors = []

        cache_data = self._sanitize_data_for_storage(data=data)
        # Step 1: Upsert in Local Cache
        try:
            cache = self._get_cache(challenge_name)
            cache[hashed_encrypted_commit] = cache_data
        except Exception as e:
            success = False
            errors.append(f"Local cache update failed: {e}")

        # Step 2: Upsert in Centralized Storage
        try:
            response = requests.post(
                self.centralized_submission_storage_url,
                json=data,
                timeout=20,
            )
            response.raise_for_status()
        except requests.RequestException as e:
            success = False
            errors.append(f"Centralized storage update failed: {e}")

        # Step 3: Sync to Decentralized Storage (Hugging Face Hub)
        today = datetime.now().strftime("%Y-%m-%d")
        try:
            filepath = f"{challenge_name}/{today}/{hashed_encrypted_commit}.json"
            self.hf_api.upload_file(
                path_or_fileobj=json.dumps(cache_data, indent=4).encode("utf-8"),
                path_in_repo=filepath,
                repo_id=self.hf_repo_id,
            )
        except KeyError:
            success = False
            errors.append(f"Record with key {hashed_encrypted_commit} not found in local cache for decentralized sync.")
        except Exception as e:
            success = False
            errors.append(f"Decentralized storage sync failed: {e}")

        # Final Logging
        if success:
            bt.logging.success(f"Record successfully updated across all storages: {hashed_encrypted_commit}")
        else:
            bt.logging.error(f"Failed to update record {hashed_encrypted_commit} across all storages. Errors: {errors}")

    def update_batch(self, records: list[dict], async_update=True):
        """
        Processes a batch of records efficiently across all storages.

        Args:
            records (list[dict]): A list of record data dictionaries.
            async_update (bool): Whether to process the batch asynchronously.
        """
        if async_update:
            # Enqueue the entire batch for the background thread
            self.storage_queue.put(records)
            bt.logging.info(f"Batch of size {len(records)} queued for storage.")
            return
        
        # Process each record synchronously
        with ThreadPoolExecutor(max_workers=5) as executor:
            executor.map(lambda record: self.update_record(record, async_update=False), records)

    def _process_storage_queue(self):
        """
        Background thread function to process storage tasks from the queue.
        Handles both single records and batches.
        """
        while True:
            try:
                data = self.storage_queue.get(timeout=1)  # Wait for a task
                if isinstance(data, list):
                    self.update_batch(data, async_update=False)
                elif isinstance(data, dict):
                    self.update_record(data, async_update=False)
                else:
                    bt.logging.warning("Unknown submission type in storage queue.")
                self.storage_queue.task_done()
            except Empty:
                pass  # No tasks in the queue, keep looping
            time.sleep(1)  # Prevent the thread from consuming too much CPU

    def _sanitize_data_for_storage(self, data: dict) -> dict:
        """
        Sanitizes the data by removing the 'log' field and filtering sensitive information 
        (e.g., 'miner_input' and 'miner_output') from the nested 'log' dictionaries.
        """
        # Create a deep copy of the data to avoid modifying the original in-place
        cache_data = data.copy()
        
        # Remove the 'log' field and sanitize the nested 'log' dictionaries
        cache_data.pop("log", None)
        if "log" in data:
            cache_data["log"] = {
                date: [{
                    key: value for key, value in log_value.items() if key not in ["miner_input", "miner_output"]
                } for log_value in logs_value] for date, logs_value in data["log"].items()
            }
            
        return cache_data

    def _update_centralized_storage(self, data: dict, url: str):
        """
        Generic method to update data in centralized storage.
        
        Args:
            data (dict): Data to update
            url (str): URL endpoint to send data to
        """
        try:
            response = requests.post(
                url,
                json=data, 
                timeout=20,
            )
            response.raise_for_status()
        except requests.RequestException as e:
            bt.logging.error(f"Centralized storage update {url} failed: {e}")

    def update_challenge_records(self, data: dict):
        """Updates the challenge records in the centralized storage."""
        self._update_centralized_storage(
            data,
            self.centralized_challenge_records_storage_url,
        )

    def update_repo_id(self, data: dict):
        """Updates the repository ID in the centralized storage."""
        self._update_centralized_storage(
            data,
            self.centralized_repo_id_storage_url,
        )

    def hash_encrypted_commit(self, encrypted_commit: str) -> str:
        """
        Hashes the encrypted commit using SHA-256 to avoid Filename too long error.
        """
        return hashlib.sha256(encrypted_commit.encode()).hexdigest()