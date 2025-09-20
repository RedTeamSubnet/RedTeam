# Device Fingerprinter V1 Challenge - Miner

This is miner fingerprinter script repo for the Device Fingerprinter V1 Challenge. This is sandboxed sample code for the challenge, you can use this code to test and dockerize your fingerprinter script.

## ✨ Features

- Base fingerprinter script
- Health check endpoint
- FastAPI
- Web service

---

## 🛠 Installation

### 1. 🚧 Prerequisites

- Install **Python (>= v3.10)** and **pip (>= 23)**:
    - **[RECOMMENDED] [Miniconda (v3)](https://docs.anaconda.com/miniconda)**
    - *[arm64/aarch64] [Miniforge (v3)](https://github.com/conda-forge/miniforge)*
    - *[Python virutal environment] [venv](https://docs.python.org/3/library/venv.html)*

[OPTIONAL] For **DEVELOPMENT** environment:

- Install [**git**](https://git-scm.com/downloads)
- Setup an [**SSH key**](https://docs.github.com/en/github/authenticating-to-github/connecting-to-github-with-ssh)

### 2. 📥 Download or clone the repository

> [!TIP]
> Skip this step, if you have already downloaded the source code.

**2.1.** Prepare projects directory (if not exists):

```sh
# Create projects directory:
mkdir -pv ~/workspaces/projects

# Enter into projects directory:
cd ~/workspaces/projects
```

**2.2.** Follow one of the below options **[A]**, **[B]** or **[C]**:

**OPTION A.** Clone the repository:

```sh
git clone https://github.com/RedTeamSubnet/RedTeam.git && \
    cd RedTeam/redteam_core/miner/commits/dev_fingerprinter_v1
```

**OPTION B.** Clone the repository (for **DEVELOPMENT**: git + ssh key):

```sh
git clone --recursive git@github.com:RedTeamSubnet/RedTeam.git && \
    cd RedTeam/redteam_core/miner/commits/dev_fingerprinter_v1
```

### 3. 📦 Install dependencies

```sh
pip install -r ./requirements.txt
```

### 4. 🏁 Start the server

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
docker build -t myhub/rest.dfp-miner:0.0.1 .

# For MacOS (Apple Silicon) to build AMD64:
DOCKER_BUILDKIT=1 docker build --platform linux/amd64 -t myhub/rest.dfp-miner:0.0.1 .
```

---

## 📑 References

- FastAPI - <https://fastapi.tiangolo.com>
- Docker - <https://docs.docker.com>
