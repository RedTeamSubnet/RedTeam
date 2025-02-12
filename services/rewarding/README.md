# RedTeam Subnet Rewarding Server

## Overview
The Rewarding Server is a centralized service designed to streamline the scoring process for RedTeam Subnet validators. Instead of each validator running their own scoring infrastructure, this server handles the evaluation of miner submissions centrally, ensuring consistent and efficient scoring across the network.

## Key Features
- Centralized scoring for all active challenges
- Automatic syncing with the subnet's metagraph
- Real-time submission processing and evaluation
- Prometheus metrics integration for monitoring
- Secure handling of encrypted miner submissions
- Daily scoring aggregation at predetermined hours

## Architecture & Workflow


1. **Submission Collection**
   - Fetches miner submissions from all active validators
   - Aggregates and deduplicates submissions based on timestamps
   - Decrypts submissions when appropriate (after 24-hour waiting period)

2. **Challenge Processing**
   - Groups submissions by challenge type
   - Runs submissions through challenge-specific controllers
   - Evaluates submissions in isolated environments
   - Maintains scoring logs for each submission

3. **Score Distribution**
   - Processes scores daily at a fixed hour (defined by SCORING_HOUR)
   - Normalizes scores across submissions
   - Updates challenge records for validator reference
   - Syncs results to storage for validator access

4. **API Endpoints**
   - `/get_scoring_logs`: Retrieve scoring logs for specific challenges
   - Prometheus metrics endpoint for monitoring

Please refer to the [services/rewarding/app.py](services/rewarding/app.py) for more details.

## Setup

### Prerequisites
- Python 3.8+
- Docker
- FastAPI
- Bittensor

### Logging in to Hugging Face
```bash
huggingface-cli login
```

### Environment Variables
```bash
REWARD_APP_KEY=<your-reward-app-key>
REWARD_APP_SS58=<your-reward-app-ss58-address>
```

### Running the Server
```bash
python services/rewarding/app.py \
    --port 10001 \
    --netuid 61 \
    --network finney \
    --cache_dir "cache_reward_app" \
    --hf_repo_id test_user/sn61-test-rewarding-app
```

## Integration for Validators
Validators can opt-in to use centralized scoring by adding the `--validator.use_centralized_scoring` flag when starting their validator node. This will make the validator fetch scores from this rewarding server instead of running the scoring locally.
