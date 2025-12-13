# Anti-Detect Automation Detection - Miner

This is miner detection script repo for the ada_detection_v1 challenge. This is sandboxed sample code for the challenge, you can use this code to test and dockerize your detection script.

## ✨ Features

- Base detection script
- Health check endpoint
- FastAPI
- Web service

---

## 🛠 Installation

### 1. 🚧 Prerequisites

- Install **Python (>= v3.10)** and **pip (>= 23)**:

[OPTIONAL] For **DEVELOPMENT** environment:

- Install [**git**](https://git-scm.com/downloads)
- Setup an [**SSH key**](https://docs.github.com/en/github/authenticating-to-github/connecting-to-github-with-ssh)

### 2. 📦 Install dependencies

```sh
pip install -r ./requirements.txt
```

### 3. 🏁 Start the server

```sh
cd src
uvicorn app:app --host="0.0.0.0" --port=10002 --no-access-log --no-server-header --proxy-headers --forwarded-allow-ips="*"

# For DEVELOPMENT:
cd src
uvicorn app:app --host="0.0.0.0" --port=10002 --no-access-log --no-server-header --proxy-headers --forwarded-allow-ips="*" --reload
```

### 5. ✅ Check server is running

Check with CLI (curl):

```sh
# Send a ping request with 'curl' to API server and parse JSON response with 'jq':
curl -s http://localhost:10002/ping
```

Check with web browser:

- Health check: <http://localhost:10002/health>
- Swagger: <http://localhost:10002/docs>
- Redoc: <http://localhost:10002/redoc>
- OpenAPI JSON: <http://localhost:10002/openapi.json>

---

## 🏗️ Build Docker Image

To build the docker image, run the following command:

```sh
docker build -t myhub/rest.rt-ada-miner:0.0.1 .

# For MacOS (Apple Silicon) to build AMD64:
DOCKER_BUILDKIT=1 docker build --platform linux/amd64 -t myhub/rest.rt-ada-miner:0.0.1 .
```

---

## 📑 References

- FastAPI - <https://fastapi.tiangolo.com>
- Docker - <https://docs.docker.com>
