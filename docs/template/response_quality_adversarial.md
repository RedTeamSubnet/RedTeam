
## Response Quality Adversarial Submission Guide

Example code for the Response Quality Adversarial Submission can be found in the `redteam_core/miner/commits/response_quality_adversarial` directory. Follow the steps below to build, tag, push, and update the active commit:

### 1. Navigate to the Text Detection Commit Directory
```bash
cd redteam_core/miner/commits/response_quality_adversarial
```

### 2. Build the Docker Image
To build the Docker image for the text detection submission, run:
```bash
docker build -t response_quality_adversarial:0.0.1 .
```

### 3. Tag the Docker Image
After building the image, tag it with your repository name:
```bash
docker tag response_quality_adversarial:0.0.1 myhub/response_quality_adversarial:0.0.1
```

### 4. Log in to Docker
Log in to your Docker Hub account using the following command:
```bash
docker login
```
Enter your Docker Hub credentials when prompted.

### 5. Push the Docker Image
Push the tagged image to your Docker Hub repository:
```bash
docker push myhub/response_quality_adversarial:0.0.1
```

### 6. Update active_commit.yaml
Finally, go to the `neurons/miner/active_commit.yaml` file and update it with the new image tag:

```yaml
- response_quality_adversarial---myhub/response_quality_adversarial:0.0.1
```

