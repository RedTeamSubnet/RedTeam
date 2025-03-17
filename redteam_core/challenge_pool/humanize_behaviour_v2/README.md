# Humanize Behaviour v2 Challenge

The **Humanize Behaviour v2** is designed to test the ability of a bot script to mimic human interaction with a Web UI form. The challenge measures how well the bot script can interact with the form and submit the required information.

## ✨ Features

- Basic mode: Simple checkbox form submission
- Validator mode: Includes hidden UI metrics collection
- Scoring based on interaction patterns
- API server for challenge interaction
- Health check endpoint
- Dockerfile for deployment
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

[TIP] Skip this step, if you have already downloaded the source code.

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
    cd RedTeam/redteam_core/challenge_pool/humanize_behaviour_v2
```

**OPTION B.** Clone the repository (for **DEVELOPMENT**: git + ssh key):

```sh
git clone --recursive git@github.com:RedTeamSubnet/RedTeam.git && \
    cd RedTeam/redteam_core/challenge_pool/humanize_behaviour_v2 && \
    git submodule update --init --recursive && \
    git submodule foreach --recursive git checkout main
```

### 3. 📦 Install dependencies

[TIP] Skip this step, if you're going to use **docker** runtime

```sh
pip install -r ./requirements.txt
```

### 4. 🏁 Start the server

#### Standalone runtime (Python)

**OPTION A.** Run server as **python module**:

```sh
python -u -m src.api

# Or:
cd src
python -u -m api
```

**OPTION B.** Run server as **python script**:

```sh
cd src
python -u ./main.py
```

**OPTION C.** Run with **uvicorn** cli:

```sh
uvicorn src.main:app --host=[BIND_HOST] --port=[PORT] --no-access-log --no-server-header --proxy-headers --forwarded-allow-ips="*"
# For example:
uvicorn src.main:app --host="0.0.0.0" --port=10001 --no-access-log --no-server-header --proxy-headers --forwarded-allow-ips="*"


# Or:
cd src
uvicorn main:app --host="0.0.0.0" --port=10001 --no-access-log --no-server-header --proxy-headers --forwarded-allow-ips="*"

# For DEVELOPMENT:
uvicorn main:app --host="0.0.0.0" --port=10001 --no-access-log --no-server-header --proxy-headers --forwarded-allow-ips="*" --reload --reload-include="*.yml" --reload-include=".env"
```

#### Docker runtime

**OPTION D.** Run with **docker compose**:

```sh
## 1. Configure 'compose.override.yml' file.

# Copy 'compose.override.[ENV].yml' file to 'compose.override.yml' file:
cp -v ./templates/compose/compose.override.[ENV].yml ./compose.override.yml
# For example, DEVELOPMENT environment:
cp -v ./templates/compose/compose.override.dev.yml ./compose.override.yml
# For example, STATGING or PRODUCTION environment:
cp -v ./templates/compose/compose.override.prod.yml ./compose.override.yml

# Edit 'compose.override.yml' file to fit in your environment:
nano ./compose.override.yml


## 2. Check docker compose configuration is valid:
./compose.sh validate
# Or:
docker compose config


## 3. Start docker compose:
./compose.sh start -l
# Or:
docker compose up -d --remove-orphans --force-recreate && \
    docker compose logs -f --tail 100
```

### 5. ✅ Check server is running

Check with CLI (curl):

```sh
# Send a ping request with 'curl' to API server and parse JSON response with 'jq':
curl -s -k https://localhost:10001/ping | jq
```

Check with web browser:

- Health check: <https://localhost:10001/health>
- Swagger: <https://localhost:10001/docs>
- Redoc: <https://localhost:10001/redoc>
- OpenAPI JSON: <https://localhost:10001/openapi.json>

### 6. 🛑 Stop the server

Docker runtime:

```sh
# Stop docker compose:
./compose.sh stop
# Or:
docker compose down --remove-orphans
```

👍

---

## ⚙️ Configuration

### 🌎 Environment Variables

[**`.env.example`**](https://github.com/RedTeamSubnet/RedTeam/blob/feat/webui-auto-challenge/redteam_core/challenge_pool/webui_auto/.env.example):

```sh
## --- Environment variable --- ##
ENV=LOCAL
DEBUG=false


## -- API configs -- ##
HBC_API_PORT=10001
# HBC_API_LOGS_DIR="/var/log/rest.rt-hb-challenger"
# HBC_API_DATA_DIR="/var/lib/rest.rt-hb-challenger"

# HBC_API_VERSION="1"
# HBC_API_PREFIX=""
# HBC_API_DOCS_ENABLED=true
# HBC_API_DOCS_OPENAPI_URL="{api_prefix}/openapi.json"
# HBC_API_DOCS_DOCS_URL="{api_prefix}/docs"
# HBC_API_DOCS_REDOC_URL="{api_prefix}/redoc"
```

## 🏗️ Build Docker Image

To build the docker image, run the following command:

```sh
# Build docker image:
./scripts/build.sh
# Or:
docker compose build
```

---

## 📑 References

- FastAPI - <https://fastapi.tiangolo.com>
- Docker - <https://docs.docker.com>
- Docker Compose - <https://docs.docker.com/compose>
