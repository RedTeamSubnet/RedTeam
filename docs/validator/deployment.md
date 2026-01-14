---
title: Deployment Options
---

# Deployment Options

The RedTeam Subnet supports two primary methods for running validator nodes:

### Docker Compose (Production - Recommended)

Docker Compose is the recommended method for production deployments. It provides isolation, automated updates, and easier management.

[**Docker Setup Reference →**](../manuals/installation/docker.md)

!!! info " Important: Do Not Use the 'Latest' Tag"
    When configuring your `docker-compose.yml`, **never** manually set the agent-validator image to `latest`.

    **Correct:**
    ```yaml
    image: redteamsubnet61/agent-validator:2.0.1-260107
    ```

    **Incorrect:**
    ```yaml
    image: redteamsubnet61/agent-validator:latest  #  DO NOT DO THIS
    ```

    **Why?** The validator utilizes WUD (What's Up Docker) to manage safe, automated updates. The system is specifically configured to track semantic versions (e.g., `2.0.1-xxxxxx`).

    - Using `latest` bypasses our safety checks and version control.
    - It may cause your validator to pull an incompatible or unstable build.
    - Let the `wud` service handle updates automatically—it will pull the newest supported version for you.

**For complete setup instructions and advanced configuration, see:**

**[→ Validator Repository README](https://github.com/RedTeamSubnet/validator/blob/main/README.md)**

---

### ⚡ PM2 Process Manager (Development/Advanced)

PM2 is suitable for development, testing, or when you need direct access to the Python environment with custom configurations.

[**PM2 Setup Reference →**](../manuals/installation/pm2.md)

!!! warning "Not Recommended"
    Running a validator with PM2 is not recommended due to limited isolation and absence of auto updater which risks validator to lost VTrust.

**Quick Start:**

```sh
# Clone the validator repository
git clone https://github.com/RedTeamSubnet/validator
cd validator

# Copy and configure PM2 settings
cp pm2-process.json.example pm2-process.json
nano pm2-process.json  # Edit with your wallet details

# Run the setup script
./scripts/run.sh
```

**For complete PM2 setup instructions and configuration options, see:**

**[→ Validator Repository](https://github.com/RedTeamSubnet/validator)**

---

## Quick Comparison

| Feature | Docker Compose | PM2 |
|---------|---|---|
| Recommended for | Production | Development/Custom |
| Setup Complexity | Simple | Moderate |
| Isolation | ✅ Yes | ❌ No |
| Auto-Update | ✅ Yes | ❌ No |
| Auto-restart | ✅ Yes | ✅ Yes |
| Log Management | ✅ Automatic | Manual |
| Monitoring | ✅ Built-in | ✅ PM2 native |
| Resource Limits | ✅ Yes | Limited |
