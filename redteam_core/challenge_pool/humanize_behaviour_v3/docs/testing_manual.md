# Humanize Behaviour v3 Testing Manual

This manual provides instructions for testing the Humanize Behaviour v3 challenge using Docker.

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

### Step 2: Setup

```bash
# Clone the repository
git clone https://github.com/RedTeamSubnet/RedTeam.git
cd RedTeam/redteam_core/challenge_pool/humanize_behaviour_v3

# Copy and configure the compose override file
cp ./templates/compose/compose.override.dev.yml ./compose.override.yml
```

### Step 3: Configure Docker

Uncomment the following line in [compose.override.yml](../compose.override.yml):

```yml
command: ["/bin/bash"]
```

### Step 4: Start the Challenge Server

```bash
./compose.sh start -l
./compose.sh enter
```

### Step 5: Run Endpoints

```bash
sudo service docker start
sg docker "python -u ./main.py"
```

### Step 6: Test Your Bot

- Visit <https://localhost:10001/docs>
- Test your bot using the `/score` endpoint

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
