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

### Step 2: Setup

```bash
# Clone the repository
git clone https://github.com/RedTeamSubnet/RedTeam.git
cd RedTeam/redteam_core/challenge_pool/ab_sniffer_v1

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

### Step 6: Test Your Script

- Run the following command to test your script to test your script if it can detect seleniumdriverless:

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

- The server runs on port 10001 by default
- Make sure port 10001 is available on your system
- All interactions are logged for analysis

## Troubleshooting

If you encounter issues:

1. Check if Docker is running
2. Verify port 10001 is not in use
3. Check Docker logs using `docker compose logs`
4. Ensure you have proper permissions to run Docker commands
