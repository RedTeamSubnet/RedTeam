---
title: Testing Manual
---

# FlowPrint v1 Testing Manual

## Prerequisites

- Docker
- Docker Compose
- Git
- Git LFS
- Python 3.10 or newer for direct script checks

## Clone and Download Data

```sh
git clone git@github.com:RedTeamSubnet/flowprint_v1.git flowprint
cd flowprint
git lfs pull
```

Confirm the public training file exists:

```text
volumes/storage/flowprint-challenge/data/v1_train_data.csv
```

`v1_train_data.csv` is mandatory for training. Do not replace it with another
dataset. The label column is `device_os`.

`v1_test_data.csv` is available only inside the official scoring server and is
not published to miners, including for local testing, for security reasons.

## Submission Files

Implement:

```text
src/flp_challenge/challenge/flowprint/src/train.py
src/flp_challenge/challenge/flowprint/src/submissions.py
```

The miner output shape is:

```json
{
  "commit_files": [
    {"file_name": "train.py", "content": "..."},
    {"file_name": "submissions.py", "content": "..."}
  ]
}
```

## Fast Local Checks

Compile both scripts:

```sh
python3 -m py_compile \
  src/flp_challenge/challenge/flowprint/src/train.py \
  src/flp_challenge/challenge/flowprint/src/submissions.py
```

Run training directly:

```sh
python3 src/flp_challenge/challenge/flowprint/src/train.py \
  volumes/storage/flowprint-challenge/data/v1_train_data.csv \
  /tmp/flowprint_model.json
```

Validate the model:

```sh
python3 -m json.tool /tmp/flowprint_model.json >/dev/null
```

## Ruff Validation

Run from `src/challenges/flowprint/examples/miner_commit`:

```sh
ruff check --config=.ruff.toml --output-format=json --no-fix src/commit/submissions.py
ruff check --config=.ruff.toml --output-format=json --no-fix src/commit/train.py
```

## Configure the Challenge

```sh
cp .env.example .env
```

Production scoring-server dataset configuration:

```dotenv
FLP_CHALLENGE_TRAIN_CSV_PATH="{data_dir}/v1_train_data.csv"
FLP_CHALLENGE_TEST_CSV_PATH="{data_dir}/v1_test_data.csv"
```

Set `FLP_CHALLENGE_API_KEY` in `.env`.

Miners should not expect `FLP_CHALLENGE_TEST_CSV_PATH` to resolve locally. The
test CSV is mounted only in the official scoring environment.

## Start and Score

```sh
docker compose up -d --build --remove-orphans
```

Local challenge startup can verify that the API and container wiring work, but
miners cannot run production-equivalent scoring without the private
`v1_test_data.csv`.

Useful endpoints:

```text
GET  http://localhost:10001/health
GET  http://localhost:10001/status
POST http://localhost:10001/score
GET  http://localhost:10001/results
GET  http://localhost:10001/telemetry
```

## Scoring Check

The official scorer returns per-class precision, recall, F1, support, and the
final `macro_f1`.

Scores below `0.9` are below the emission threshold.
