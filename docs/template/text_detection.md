
## Text Detection Submission Guide

Example code for the Text Detection Submission can be found in the `redteam_core/miner/commits/text_detection` directory. Follow the steps below to build, tag, push, and update the active commit:

### 1. Navigate to the Text Detection Commit Directory
```bash
cd redteam_core/miner/commits/text_detection
```

### 2. Build the Docker Image
To build the Docker image for the text detection submission, run:
```bash
docker build -t text_detection_submission:0.0.1 .
```

### 3. Tag the Docker Image
After building the image, tag it with your repository name:
```bash
docker tag text_detection_submission:0.0.1 myhub/text_detection_submission:0.0.1
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
docker push myhub/text_detection_submission:0.0.1
```

### 6. Retrieve the SHA256 Digest
After pushing the image, retrieve the digest by running:
```bash
docker inspect --format='{{index .RepoDigests 0}}' myhub/text_detection_submission:0.0.1
```

### 7. Update active_commit.yaml
Finally, go to the `neurons/miner/active_commit.yaml` file and update it with the new image tag:

```yaml
- text_detection---myhub/text_detection_submission@<sha256:digest>
```

