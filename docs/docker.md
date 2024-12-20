# Docker Guide


## Prerequisites
1. **Install Docker**: Ensure Docker is installed and running on your system.
   - Visit [Docker Install Documentation](https://docs.docker.com/engine/install/) for detailed instructions.

   **For Ubuntu**:
   ```bash
   for pkg in docker.io docker-doc docker-compose docker-compose-v2 podman-docker containerd runc; do sudo apt-get remove $pkg; done
   sudo apt-get update
   sudo apt-get install ca-certificates curl
   sudo install -m 0755 -d /etc/apt/keyrings
   sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
   sudo chmod a+r /etc/apt/keyrings/docker.asc
   echo \
   "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
   $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
   sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
   sudo apt-get update
   sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    ```


    To verify the installation, run:
    ```bash
    sudo docker run hello-world
    ```

2. **A Docker Hub Account**:
   - Sign up at https://hub.docker.com/ if you don’t already have an account.

3. **Log in to Docker Hub**:
   - Run the following command to log in to Docker Hub and enter your Docker Hub credentials:
    ```
    docker login
    ```

### Steps to Build, Tag, and Push a Docker Image:

1. **Build the Docker Image**
   - Navigate to the directory containing your `Dockerfile`:
     ```
     cd /path/to/your/project
     ```
     Example:
     ```
     cd redteam_core/miner/commits/text_detection
     ```

   - Build the Docker image:
     ```
     docker build -t <image_name>:<tag> .
     ```
     - Replace `<image_name>` with the desired name of your image (e.g., `challenge_name`).
     - Replace `<tag>` with a version or description for the image (e.g., `v1.0`, `latest`).

     Example:
     ```
     docker build -t challenge_name:0.0.1 .
     ```

2. **Tag the Docker Image**
   - Tag your image for Docker Hub by adding your Docker Hub username:
     ```
     docker tag <image_name>:<tag> <dockerhub_username>/<repository_name>:<tag>
     ```
     - Replace `<dockerhub_username>` with your Docker Hub username.
     - Replace `<repository_name>` with the repository name you want to push to.

     Example:
     ```
     docker tag challenge_name:0.0.1 redteam/challenge_name:0.0.1
     ```

3. **Push the Docker Image to Docker Hub**
   - Push the tagged image to Docker Hub:
     ```
     docker inspect --format='{{index .RepoDigests 0}}' <dockerhub_username>/<repository_name>:<tag>
     ```

     Example:
     ```
     docker inspect --format='{{index .RepoDigests 0}}' redteam/challenge_name:0.0.1
     ```

4. **Retrieve the SHA256 Digest**
   - After pushing the image, retrieve the digest by running:
     ```
     docker push <dockerhub_username>/<repository_name>:<tag>
     ```

     Example:
     ```
     docker push redteam/challenge_name:0.0.1
     ```

5. **Verify the Image on Docker Hub**
   - Log in to Docker Hub and navigate to your repository to ensure the image has been successfully uploaded.

### Notes:
- Ensure your `<repository_name>` already exists on Docker Hub or create it before pushing the image.
- Use descriptive tags to manage different versions of your Docker images effectively.
