---
title: Testing Manual
---

# FlowRadar v2 Testing Manual

## Prerequisites

- Docker
- Docker Compose
- Git
- Git LFS
- Python 3.10 or newer for direct script checks

## Clone and Download Data

```sh
git clone git@github.com:RedTeamSubnet/flowradar-challenge.git flowradar
cd flowradar
git lfs pull
```

Confirm these files exist:

```text
volumes/storage/flowradar-challenge/data/v2_train_data.csv
volumes/storage/flowradar-challenge/data/v2_test_data.csv
```

`v2_train_data.csv` is mandatory for training. Do not replace it with v1 data.

## Submission Files

Implement:

```text
src/flr_challenge/challenge/flowradar/src/train.py
src/flr_challenge/challenge/flowradar/src/submissions.py
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
  src/flr_challenge/challenge/flowradar/src/train.py \
  src/flr_challenge/challenge/flowradar/src/submissions.py
```

Run training directly:

```sh
python3 src/flr_challenge/challenge/flowradar/src/train.py \
  volumes/storage/flowradar-challenge/data/v2_train_data.csv \
  /tmp/flowradar_model.json
```

Validate the model:

```sh
python3 -m json.tool /tmp/flowradar_model.json >/dev/null
```

## Configure the Challenge

```sh
cp .env.example .env
```

Production-equivalent dataset configuration:

```dotenv
FLR_CHALLENGE_TRAIN_CSV_PATH="{data_dir}/v2_train_data.csv"
FLR_CHALLENGE_TEST_CSV_PATH="{data_dir}/v2_test_data.csv"
```

Set `FLR_CHALLENGE_API_KEY` in `.env`.

## Start and Score

```sh
docker compose up -d --build --remove-orphans
python3 skills/challenge-score/scripts/check_score.py
```

The helper reads both Python files, builds `miner_output.commit_files`, and
calls `/score`.

Useful endpoints:

```text
GET  http://localhost:10001/health
GET  http://localhost:10001/status
POST http://localhost:10001/score
GET  http://localhost:10001/results
GET  http://localhost:10001/telemetry
```

## Optional V1 Compatibility Test

V1 test data uses 34 columns and label `is_vpn`. Convert it to the v2 shape:

```sh
python3 - <<'PY'
from pathlib import Path

import pandas as pd

data_dir = Path("volumes/storage/flowradar-challenge/data")
v1 = pd.read_csv(data_dir / "v1_test_data.csv")
v2_columns = pd.read_csv(data_dir / "v2_train_data.csv", nrows=0).columns

v1 = v1.rename(columns={"is_vpn": "vpn_is_enabled"})
v1 = v1.reindex(columns=v2_columns)
v1.to_csv(data_dir / "v1_test_v2_shape.csv", index=False)
PY
```

Keep production training unchanged:

```dotenv
FLR_CHALLENGE_TRAIN_CSV_PATH="{data_dir}/v2_train_data.csv"
FLR_CHALLENGE_TEST_CSV_PATH="{data_dir}/v1_test_v2_shape.csv"
```

This is only a compatibility test. Restore `v2_test_data.csv` for final
production-equivalent scoring.

## Troubleshooting

Missing training data:

- Run `git lfs pull`.
- Confirm `v2_train_data.csv` is a real CSV, not a small LFS pointer file.

Invalid miner output:

- Include exactly `train.py` and `submissions.py`.
- Use `file_name` and `content`.
- Do not include additional files or path-based names.

Invalid model:

- Write valid JSON to the second trainer argument.
- Keep it within the configured size limit.

Inference errors:

- Return a Python boolean.
- Handle missing fields and JSON `null`.
- Do not expect `vpn_is_enabled` inside inference features.

Training timeout:

- Keep training within `FLR_CHALLENGE_TRAINING_TIMEOUT_SECONDS`.
- Increasing the local timeout does not change production limits.

Inspect logs:

```sh
docker compose logs -f challenge-api
```
