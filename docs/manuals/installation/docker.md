---
title: Docker
tags: [docker, docker-hub, installation, linux]
---

# :simple-docker: Docker

RedTeam Subnet 61 leverages Docker to run validator nodes and miner node, packaging miner solutions as Docker images to ensure consistency and portability across different environments. This guide provides instructions on installing Docker on Linux systems and setting up a Docker Hub account.

## Official pages

- Install Docker: <https://docs.docker.com/engine/install>
- Install Docker on Ubuntu: <https://docs.docker.com/engine/install/ubuntu>
- Linux post-installation steps for Docker Engine: <https://docs.docker.com/engine/install/linux-postinstall>
- Docker install script: <https://github.com/docker/docker-install>

---

## 1. Setup Docker on Linux

### 1.1. Install Docker using installation script

```sh
# Download docker installer script:
curl -fsSL https://get.docker.com -o get-docker.sh
# Install docker by 'get-docker.sh' script:
DRY_RUN=1 sudo sh get-docker.sh

# Remove downloaded script:
rm -vrf get-docker.sh
```

### 1.2. Post-installation steps

```sh
# Check docker service status:
sudo systemctl status docker
# If docker is not running, start the docker service:
sudo systemctl start docker

# To avoid using 'sudo' for docker commands:
# Create a new 'docker' group:
sudo groupadd docker
# Add current user to the 'docker' group:
sudo usermod -aG docker $(whoami)

# Apply new group changes to the new shell session:
newgrp docker
# Or reboot the system to apply docker group changes:
sudo shutdown -r now

# Configure docker to start on reboot:
sudo systemctl enable docker.service
sudo systemctl enable containerd.service
```

Check docker is installed and running:

```sh
docker -v
docker info
docker images
```

### 1.3. [RECOMMENDED] Limit docker log file max size and max rotation

Edit the `/etc/docker/daemon.json` file:

```sh
sudo nano /etc/docker/daemon.json
```

and add the following `log-opts` into the `/etc/docker/daemon.json` file:

```json
{
    "log-opts":
    {
        "max-size": "10m",
        "max-file": "10"
    }
}
```

save changes and exit from the file editor.

```sh
# Restart docker service:
sudo systemctl restart docker.service
```

## 2. Docker Hub account

### 2.1. Create Docker Hub account

Sign up at <https://hub.docker.com>, if you don't have an account yet.

### 2.2. Log in to Docker Hub

Run the following command in your environment terminal, and provide your Docker Hub credentials:

```sh
docker login
```

---

## References

- Docker Hub: <https://hub.docker.com>
- Docker Documentation: <https://docs.docker.com>
- Docker Compose: <https://docs.docker.com/compose>
- Docker CLI Reference: <https://docs.docker.com/engine/reference/commandline/cli>
