import os
import time
import json
import requests
import threading
import hashlib
from shutil import rmtree
from queue import Queue, Empty
from collections import defaultdict
import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

import bittensor as bt
from diskcache import Cache
from huggingface_hub import HfApi

from .. import challenge_pool
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
        self.active_challenges = challenge_pool.ACTIVE_CHALLENGES

        # Decentralized storage on Hugging Face Hub
        self.hf_repo_id = hf_repo_id
        self.hf_api = HfApi()
        bt.logging.info(f"Authenticated as {self.hf_api.whoami()['name']}")
        self._validate_hf_repo()

        # Local cache with disk cache
        self.cache_dir = cache_dir
        self.cache_ttl = int(datetime.timedelta(days=14).total_seconds()) # TTL set equal to a decaying period
        self.local_caches: dict[Cache] = {}

        # Centralized storage URLs
        self.centralized_submission_storage_url = constants.STORAGE_URL + "/upload-submission"
        self.centralized_challenge_records_storage_url = constants.STORAGE_URL + "/upload-challenge-records"
        self.centralized_repo_id_storage_url = constants.STORAGE_URL + "/upload-hf-repo-id"

        # Queue and background thread for async updates
        self.storage_queue = Queue()
        self.storage_thread = threading.Thread(target=self._process_storage_queue, daemon=True)
        self.storage_thread.start()

        os.makedirs(self.cache_dir, exist_ok=True)
        # Sync data from Hugging Face Hub to local cache if required
        if sync_on_init:
            self.sync_hub_to_cache()

    # MARK: Sync Methods
    def sync_hub_to_cache(self, erase_local_cache=True):
        """
        Syncs data from Hugging Face Hub to the local cache.
        This method will fetch data from the last 14 days from the Hugging Face Hub and build the cache accordingly.
        Note: This method only syncs submission records (active challenges), not challenge records.

        Args:
            erase_local_cache (bool): Whether to erase the local cache before syncing.
        """
        # Erase the existing local cache if needed
        if erase_local_cache and os.path.exists(self.cache_dir):
            rmtree(self.cache_dir)
            os.makedirs(self.cache_dir, exist_ok=True)

        # Get the list of the last 14 days' date strings in the format 'YYYY-MM-DD' and create allow patterns
        date_strings = [(datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=i)).strftime("%Y-%m-%d") for i in range(14)]
        allow_patterns = [f"*{date_str}/*" for date_str in date_strings]
        # Download the snapshot
        repo_snapshot_path = self._snapshot_repo(erase_cache=False, allow_patterns=allow_patterns)

        if not os.path.isdir(repo_snapshot_path):
            bt.logging.info(f"No data on the Hub for the last 14 days, skip sync.")
            return

        # Build a temporary dict
        all_records = defaultdict(dict)
        for challenge_name in os.listdir(repo_snapshot_path):
            # Skip non-active challenges and non challenge submissions
            if challenge_name not in self.active_challenges:
                continue

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
        Note: This method only syncs submission records (active challenges).

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
        today = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d")
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
            # Skip non-active challenges and non challenge submissions
            if challenge_name not in self.active_challenges:
                continue
            
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

    # MARK: Update Methods
    def update_record(self, data: dict, async_update=True, retry_config=None):
        """
        Updates or inserts a submission record across all storages with independent retries.

        Args:
            data (dict): The record data. Must include "encrypted_commit" and "challenge_name".
            async_update (bool): Whether to process the update asynchronously.
            retry_config (dict, optional): Retry configuration for each storage type.
        """
        # Validate required fields
        required_fields = ["miner_ss58_address", "encrypted_commit", "challenge_name"]
        if not all(field in data for field in required_fields):
            bt.logging.error(f"Data must include all required fields: {required_fields} in update_record()")
            return

        if async_update:
            self.storage_queue.put(data)
            bt.logging.info(f"Record with encrypted_commit={data["encrypted_commit"]} queued for storage.")
            return
        
        # Process the record immediately
        if retry_config is None:
            retry_config = {"local": 3, "centralized": 5, "decentralized": 5}

        challenge_name = data["challenge_name"]
        hashed_cache_key = self.hash_cache_key(data["encrypted_commit"])
        cache_data = self._sanitize_data_for_storage(data=data)
        
        # Track success for all storage operations
        success = True
        errors = []

        # Step 1: Local Cache with retry
        def local_operation():
            cache = self._get_cache(challenge_name)
            cache[hashed_cache_key] = cache_data

        local_success, error = self._retry_operation(local_operation, retry_config["local"], "Local cache update")
        if not local_success:
            success = False
            errors.append(error)

        # Step 2: Centralized Storage with retry
        def centralized_operation():
            response = requests.post(
                self.centralized_submission_storage_url,
                json=data,
                timeout=20
            )
            response.raise_for_status()

        central_success, error = self._retry_operation(centralized_operation, retry_config["centralized"], "Centralized storage update")
        if not central_success:
            success = False
            errors.append(error)

        # Step 3: HuggingFace Hub with retry
        today = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d")
        hf_filepath = f"{challenge_name}/{today}/{hashed_cache_key}.json"

        def decentralized_operation():
            self.hf_api.upload_file(
                path_or_fileobj=json.dumps(cache_data, indent=4).encode("utf-8"),
                path_in_repo=hf_filepath,
                repo_id=self.hf_repo_id,
                commit_message=f"Update submission record {hashed_cache_key}"
            )

        hf_success, error = self._retry_operation(decentralized_operation, retry_config["decentralized"], "Decentralized storage update")
        if not hf_success:
            success = False
            errors.append(error)

        # Final Logging
        if success:
            bt.logging.success(f"Record successfully updated across all storages: {hashed_cache_key}")
        else:
            bt.logging.error(f"Failed to update record {hashed_cache_key}. Errors: {errors}")

    def update_challenge_record(self, data: dict, async_update=True, retry_config=None):
        """
        Updates challenge records across all storages with independent retries.
        
        Args:
            data (dict): The challenge records data.
            async_update (bool): Whether to process the update asynchronously.
            retry_config (dict, optional): Retry configuration for each storage type.
        """
        # Validate required fields
        required_fields = ["challenge_name", "date"]
        if not all(field in data for field in required_fields):
            bt.logging.error(f"Data must include all required fields: {required_fields} in update_challenge_record()")
            return
        
        if async_update:
            self.storage_queue.put(data)
            return

        # Process the record immediately
        if retry_config is None:
            retry_config = {"local": 3, "centralized": 5, "decentralized": 5}

        # Track success for all storage operations
        success = True
        errors = []

        # Step 1: Local Cache with retry
        def local_operation():
            challenge_cache = self._get_cache("_challenge_records")
            cache_key = f"{data["challenge_name"]}---{data["date"]}" # TODO: MAYBE RECONSIDER THIS KEY
            challenge_cache[cache_key] = data

        local_success, error = self._retry_operation(local_operation, retry_config["local"], "Local cache update")
        if not local_success:
            success = False
            errors.append(error)

        # Step 2: Centralized Storage with retry
        def centralized_operation():
            response = requests.post(
                self.centralized_challenge_records_storage_url,
                json=data,
                timeout=20
            )
            response.raise_for_status()

        central_success, error = self._retry_operation(centralized_operation, retry_config["centralized"], "Centralized storage update")
        if not central_success:
            success = False
            errors.append(error)

        # Step 3: HuggingFace Hub with retry
        def decentralized_operation():
            hf_filepath = f"_challenge_records/{data["challenge_name"]}/{data["date"]}.json"
            self.hf_api.upload_file(
                path_or_fileobj=json.dumps(data, indent=4).encode("utf-8"),
                path_in_repo=hf_filepath,
                repo_id=self.hf_repo_id,
                commit_message=f"Update challenge record {data["challenge_name"]} for {data["date"]}"
            )

        hf_success, error = self._retry_operation(decentralized_operation, retry_config["decentralized"], "Decentralized storage update")
        if not hf_success:
            success = False
            errors.append(error)

        # Final Logging
        if success:
            bt.logging.success(f"Challenge records successfully updated across all storages for validator {data["validator_uid"]}")
        else:
            bt.logging.error(f"Failed to update challenge records. Errors: {errors}")

    def update_batch(self, records: list[dict], update_method: str = "update_record", async_update=True):
        """
        Processes a batch of records efficiently across all storages.

        Args:
            records (list[dict]): A list of record data dictionaries.
            process_method (str): The method to use for processing each record ("update_record" or "update_challenge_record")
            async_update (bool): Whether to process the batch asynchronously.
        """
        if async_update:
            # Enqueue the entire batch along with the processing method
            self.storage_queue.put((records, update_method))
            bt.logging.info(f"Batch of size {len(records)} queued for storage using {update_method}")
            return
        
        # Get the appropriate processing method
        processor = getattr(self, update_method)
        
        # Process each record synchronously
        with ThreadPoolExecutor(max_workers=5) as executor:
            executor.map(lambda record: processor(record, async_update=False), records)

    def update_repo_id(self, data: dict):
        """ 
        Updates repository ID to the centralized storage. 
        """
        try:
            response = requests.post(
                self.centralized_repo_id_storage_url,
                json=data, 
                timeout=20,
            )
            response.raise_for_status()
            bt.logging.info(f"Successfully updated repo_id in centralized storage")
        except Exception as e:
            bt.logging.error(f"Error updating repo_id to centralized storage: {e}")
            raise

    # def _update_centralized_storage(self, data: dict, url: str):
    #     """
    #     Generic method to update data in centralized storage.
        
    #     Args:
    #         data (dict): Data to update
    #         url (str): URL endpoint to send data to
    #     """
    #     try:
    #         response = requests.post(
    #             url,
    #             json=data, 
    #             timeout=20,
    #         )
    #         response.raise_for_status()
    #     except requests.RequestException as e:
    #         bt.logging.error(f"Centralized storage update {url} failed: {e}")

    # def update_challenge_records(self, data: dict):
    #     """Updates the challenge records in the centralized storage."""
    #     self._update_centralized_storage(
    #         data,
    #         self.centralized_challenge_records_storage_url,
    #     )

    # MARK: Helper Methods
    def hash_cache_key(self, cache_key: str) -> str:
        """
        Hashes the cache key using SHA-256 to avoid Filename too long error.
        """
        return hashlib.sha256(cache_key.encode()).hexdigest()
    
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

    def _get_cache(self, cache_name: str) -> Cache:
        """
        Returns the diskcache instance for a specific name.
        Sets TTL only for challenge caches, no expiration for other caches.

        Args:
            cache_name (str): The name of the cache (e.g., challenge name, "_challenge_records", "_repo_ids")

        Returns:
            Cache: The cache instance
        """
        if cache_name not in self.local_caches:
            cache_path = os.path.join(self.cache_dir, cache_name)
            cache = Cache(cache_path, eviction_policy="none")
            
            # Set TTL only if it's an active challenge
            if cache_name in self.active_challenges:
                cache.expire = self.cache_ttl
                
            self.local_caches[cache_name] = cache
        return self.local_caches[cache_name]
    
    def _process_storage_queue(self):
        """
        Background thread function to process storage tasks from the queue.
        Handles both single records and batches with their processing methods.
        """
        while True:
            try:
                data = self.storage_queue.get(timeout=1)  # Wait for a task
                
                if isinstance(data, tuple) and isinstance(data[0], list):  # Batch update with method
                    records, process_method = data
                    self.update_batch(records, process_method=process_method, async_update=False)
                elif isinstance(data, dict):
                    self.update_record(data, async_update=False)
                else:
                    bt.logging.warning(f"Unknown submission type in storage queue: {type(data)} with data: {data}")
                self.storage_queue.task_done()
            except Empty:
                pass  # No tasks in the queue, keep looping
            time.sleep(1)  # Prevent the thread from consuming too much CPU

    def _sanitize_data_for_storage(self, data: dict) -> dict:
        """
        Sanitizes the data by replacing sensitive information in logs with placeholder values
        while maintaining the required schema structure.
        """
        # Create a deep copy of the data to avoid modifying the original in-place
        cache_data = data.copy()
        
        # Sanitize the nested 'log' dictionaries with placeholder values
        if "log" in data:
            cache_data["log"] = {
                date: [{
                    **{key: value for key, value in log_value.items() if key not in ["miner_input", "miner_output"]},
                    **{"miner_input": {} if "miner_input" in log_value else None},  # Only add placeholder if exists
                    **{"miner_output": {} if "miner_output" in log_value else None}  # Only add placeholder if exists
                } for log_value in logs_value] for date, logs_value in data["log"].items()
            }
            
        return cache_data
    
    def _retry_operation(self, operation, max_retries: int, operation_name: str) -> tuple[bool, str]:
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
                wait_time = min(2 ** attempt, 32)  # Exponential backoff, max 8 seconds
                bt.logging.warning(f"{operation_name} attempt {attempt + 1} failed, retrying in {wait_time}s: {last_error}")
                time.sleep(wait_time)
        
        error_msg = f"{operation_name} failed after {max_retries} attempts. Last error: {last_error}"
        return False, error_msg