# RedTeam Subnet Rewarding Server

## Overview

The Rewarding Server is a specialized validator node that provides centralized scoring for the RedTeam Subnet (netuid 61). It extends the standard Validator functionality but focuses exclusively on scoring and comparing miner submissions rather than querying miners or setting weights directly.

## Key Features

- Centralized scoring infrastructure for all subnet validators
- Aggregation of miner submissions from all active validators
- Automatic deduplication and versioning of submissions
- Challenge-specific scoring and comparison controllers
- Daily score processing at predetermined hours (SCORING_HOUR constant)
- In-memory and persistent caching of scoring results
- RESTful API for validators to retrieve scoring results
- Prometheus metrics for monitoring

## Technical Architecture

### State Management

The rewarding server maintains several important state variables:

- `validators_miner_commits`: Stores current miner commits from all validators, indexed by validator UID and hotkey
- `miner_commits`: Aggregated miner commits from all validators, indexed by miner UID and hotkey
- `miner_commits_cache`: Quick lookup cache mapping challenge+encrypted_commit to commit objects
- `scoring_results`: Cache for scored submissions with scoring logs and comparison logs
- `is_scoring_done`: Tracks scoring completion status for each challenge

### Processing Workflow

1. **Validation Loop (`forward` method)**
   - Updates validator and miner commit state
   - Scores new submissions
   - Finalizes daily scoring at the designated scoring hour
   - Stores results in persistent storage

2. **Submission Collection**
   - `_update_validators_miner_commits`: Fetches commits from all validators with sufficient stake
   - `_update_miner_commits`: Aggregates commits from all validators, keeping the latest versions
   - Maintains submission history and versioning based on commit timestamps

3. **Scoring Process**
   - `_score_and_compare_new_miner_commits`: Scores new submissions using challenge controllers
   - `_compare_miner_commits`: Compares submissions for similarity detection
   - Caches scoring results for each docker_hub_id to prevent duplicate processing
   - Handles both daily incremental scoring and final scoring at the designated hour

4. **Storage Integration**
   - `_store_centralized_scoring`: Persists scoring results to storage service
   - `_fetch_centralized_scoring`: Retrieves scoring results from storage
   - `_sync_scoring_results_from_storage_to_cache`: Syncs storage data to local cache
   - Maintains local backup in `scoring_results.json`

5. **API Interface**
   - FastAPI server running in a separate thread
   - `/get_scoring_result`: Returns scoring and comparison results for specific challenge and commits, validator can use this endpoint to get the scoring results of the miner commits
   - Prometheus metrics for monitoring

## API Endpoints

### `/get_scoring_result`

- **Method**: POST
- **Parameters**:
    - `challenge_name`: Name of the challenge
    - `encrypted_commits`: List of encrypted commits to look up
- **Response**:

    ```json
    {
    "status": "success",
    "message": "Scoring results retrieved successfully",
    "data": {
        "commits": {
        "<encrypted_commit>": {
            "miner_uid": 123,
            "miner_hotkey": "...",
            "challenge_name": "...",
            "scoring_logs": [...],
            "comparison_logs": {...},
            "score": 0.95,
            "penalty": 0.0
        }
        },
        "is_done": true/false
    }
    }
    ```

## Setup

Setup steps for the rewarding server are the same as the validator node, please refer to the [validator README](../../docs/1.validator.md) for more details.

### Running the Server

```bash
python services/rewarding/app.py \
    --reward_app.port 47920 \
    --reward_app.epoch_length 60 \
    --netuid 61 \
    --network finney \
    --subtensor.chain_endpoint <subtensor-endpoint> \
    --wallet.name <wallet-name> \
    --wallet.hotkey <hotkey-name>
```

#### Command Line Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `--reward_app.port` | Port for the FastAPI server | 47920 |
| `--reward_app.epoch_length` | Processing cycle duration (seconds) | 60 |
| `--netuid` | Subnet ID to connect to | Required |
| `--network` | Bittensor network (finney, test) | Required |
| `--subtensor.chain_endpoint` | Custom subtensor endpoint | Required |
| `--wallet.name` | Wallet name | Required |
| `--wallet.hotkey` | Wallet hotkey name | Required |
| `--validator.cache_dir` | Directory for caching scoring results | `./.cache` |
| `--validator.hf_repo_id` | Hugging Face repo ID for model weights | `my_username/rt.reward-storage` |

## Integration for Validators

Validators can use the centralized scoring service by:

1. Adding the `--validator.use_centralized_scoring` flag to their validator command
2. The validator will automatically fetch scoring results from the rewarding server
3. This eliminates the need for each validator to run scoring infrastructure

## Development & Troubleshooting

### Monitoring

- Check the Prometheus metrics endpoint for performance monitoring
- Review logs for scoring errors and processing delays
- The `scoring_results.json` file provides a backup of all scoring data

### Common Issues

- If scoring results aren't being updated, check network connectivity to storage service
- Verify that the reward app has sufficient stake in the metagraph
- Ensure the REWARD_APP_HOTKEY environment variable matches the wallet.hotkey

### Security Considerations

- The reward app has access to all validator submissions and must maintain data integrity
- Uses validation headers for secure communication with storage service
- Maintains proper synchronization between memory cache and persistent storage
