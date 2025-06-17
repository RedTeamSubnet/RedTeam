# Auto Browser Sniffer v1 Testing Manual

This manual provides instructions for testing the Auto Browser Sniffer v1 challenge using Docker.

## Overview

- Build a single script which should detect the type of the driver bot is using
- Uses Docker for easy submission and testing

## Quick Start Guide

### Prerequisites

- Docker and Docker Compose installed
- Git (for cloning the repository)

### Step 1: Provide Your Scripts

- Paste your detection script into [detection.js](../src/templates/static/detection/detection.js)

### Step 2: Setup Challenge Environment

```bash
git clone https://github.com/RedTeamSubnet/RedTeam.git
cd RedTeam
```

- Run the following commands in **separate terminal** and **leave it as is** to see the logs:

```bash
bash ./redteam_core/challenge_pool/ab_sniffer_v1/scripts/setup.sh
```

#### Step 3: Setup Testing Environment

- In a **separate terminal**, run the following commands to set up miner environment:

```bash
bash ./redteam_core/miner/commits/ab_sniffer_v1/scripts/setup.sh
```

### Step 4: Test Your Script

- Run the following command to eslint test and run your script to get the score by simulating staging environment
- You can see the logs in the first terminal where you ran the setup script

```bash
bash ./redteam_core/miner/commits/ab_sniffer_v1/scripts/test-script.sh
```

- Run the following command to test your script if it can detect driver specific bots:

```bash
docker run --network=host \                                                            
  -e ABS_WEB_URL=http://127.0.0.1:10001/_web \
  redteamsubnet61/seleniumdriverless
```

- Change the driver type in the URL to test different scenarios:
- For example you can change the image name to available drivers:
    - redteamsubnet61/seleniumdriverless
    - redteamsubnet61/seleniumbase
    - redteamsubnet61/nodriver
    - redteamsubnet61/patchright

## Important Notes

- The server runs on port 10001 by default and the miner-api runs on port 10002
- Make sure port 10001 and 10002 are available on your system
- All interactions are logged for analysis

## Troubleshooting

If you encounter issues:

1. Check if Docker is running
2. Verify port 10001 is not in use
3. Check Docker logs using `docker compose logs`
4. Ensure you have proper permissions to run Docker commands
5. You can also check the logs in `/var/lib/docker/volumes/ab_sniffer_v1_api-logs/_data`
