# Humanize Behaviour v4 Testing Manual

This manual provides instructions for testing the Humanize Behaviour v4 challenge using Docker.

## Overview

- Tests bot script's ability to mimic human interaction with a Web UI form
- Includes trajectory similarity check between sessions
- Uses Docker for easy submission and testing

## Quick Start Guide

### Prerequisites

- Docker and Docker Compose installed
- Git (for cloning the repository)

### Step 1: Provide Your Scripts

- Paste your bot script into [bot.py](../src/bot/src/core/bot.py)
- Add your requirements to [requirements.txt](../src/bot/requirements.txt)

### Step 2: Setup Challenge Environment

```bash
git clone https://github.com/RedTeamSubnet/RedTeam.git
cd RedTeam
```

- Run the following commands in **separate terminal** and **leave it as is** to see the logs:

```bash
bash ./redteam_core/challenge_pool/humanize_behaviour_v4/scripts/setup-testing.sh
```

#### Step 3: Setup Testing Environment

- In a **separate terminal**, run the following commands to set up miner environment:

```bash
bash ./redteam_core/miner/commits/humanize_behaviour_v4/scripts/setup-testing.sh
```

### Step 4: Test Your Script

- Run the following command to eslint test and run your script to get the score by simulating staging environment
- You can see the logs in the first terminal where you ran the setup script

```bash
bash ./redteam_core/miner/commits/humanize_behaviour_v4/scripts/test-script.sh
```

## Important Notes

- The server runs on port 10001 by default
- Make sure port 10001 is available on your system
- The challenge includes trajectory similarity checks between sessions
- All interactions are logged for analysis

## Troubleshooting

If you encounter issues:

1. Check if Docker is running
2. Verify port 10001 is not in use
3. Check Docker logs using `docker compose logs`
4. Ensure you have proper permissions to run Docker commands
