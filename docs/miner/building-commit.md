# Building a Submission Commit

This guide shows how to build your challenge solution for RedTeam Subnet.

## Available Challenges

Choose a challenge from the [Challenge Menu](../challenges/README.md):

- **[AB Sniffer](../challenges/ab_sniffer/README.md)** - Detect automation frameworks (Node.js)
- **[Humanize Behaviour](../challenges/humanize_behaviour/README.md)** - Mimic human interaction (Python)
- **[Anti-Detect Automation Detection](../challenges/ada_detection/README.md)** - Detect bots in anti-detect browsers (JavaScript)
- **[Device Fingerprinter](../challenges/dev_fingerprinter/README.md)** *(Inactive)*

## Submission Process

### 1. Implement Your Solution

Clone the repository for the challenge you're participating in:

```bash
git clone https://github.com/RedTeamSubnet/<challenge>.git 
cd <challenge>/templates/commit
```

Place your solution files in the **dedicated path** specified in each challenge's README. You can find each challenge README in the [Challenge Menu](../challenges/README.md). 

Read documentation about submission example templates: [About Submission Examples](./components/submission_templates.md)

### 2. Test Locally

Validate your solution before submitting:

```bash
# Build and test the Docker image
docker build -t test:latest .
docker run -it test:latest

# For AB Sniffer: Use ESLint validation
# See: https://replit.com/@redteamsn61/absnifferv1eslintcheck
```

Refer to each challenge's testing manual for specific validation steps.

### 3. Build Docker Image

```bash
docker login

docker build -t <username>/<challenge>:<version> .
```

**Example:**

```bash
docker build -t myuser/ab_sniffer:1.0.0 .
```

### 4. Push to Docker Hub

```bash
docker push <username>/<challenge>:<version>
```

### 5. Get SHA256 Digest

```bash
docker inspect --format='{{index .RepoDigests 0}}' <username>/<challenge>:<version>
```

**Example Output:**

```bash
myuser/ab_sniffer@sha256:abc123def456...
```

## Complete Example

```bash
# Clone repository
git clone https://github.com/RedTeamSubnet/ab-sniffer-challenge.git
cd ab-sniffer-challenge/templates/commit

# Implement solution in src/detections/
# Place your .js detection files

# Build and push
docker login
docker build -t myuser/ab_sniffer:1.0.0 .
docker push myuser/ab_sniffer:1.0.0

# Get digest and register
docker inspect --format='{{index .RepoDigests 0}}' myuser/ab_sniffer:1.0.0
```

## Next Steps

- **[Submission Guide](https://github.com/RedTeamSubnet/miner/blob/main/README.md)** - Submit your commit
- **[Challenge Menu](../challenges/README.md)** - Explore all challenges
- **[Miner Repository](https://github.com/RedTeamSubnet/miner)** - Examples and templates
