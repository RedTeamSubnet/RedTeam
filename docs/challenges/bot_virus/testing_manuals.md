---
title: Testing Manual
---
# Testing Manual

This manual covers how to check your [Bot Virus v2](v2.md) submission locally
before you publish it.

The evaluation environment is private and not available to miners, so you
cannot run the full evaluation locally. Use the **miner commit example** to
check the parts you can verify yourself. Scoring happens on the platform.

Full example documentation:
[`examples/miner_commit/README.md`](https://github.com/RedTeamSubnet/bot-virus-challenge/blob/main/examples/miner_commit/README.md).

## Prerequisites

- Python 3.10+ and pip 23+
- Ruff (for the lint check)
- Docker Engine with Buildx (for `linux/amd64` builds)
- A web browser (for the practice page)
- `curl` and `jq` (optional, for the API check)

## 1. Get the example

```sh
git clone https://github.com/RedTeamSubnet/bot-virus-challenge.git
cd bot-virus-challenge/examples/miner_commit
```

## 2. Put your submission in place

Your submission lives in `src/commit/` and must contain exactly two files:

```text
src/commit/bot.py
src/commit/Dockerfile
```

- Do not add other files. The example service reads every entry in
  `src/commit/`, so extra files or subdirectories (such as `__pycache__/`) break
  the check.
- Use the exact names `bot.py` and `Dockerfile`.

## 3. Check the page actions with the practice page

1. Open `practice/index.html` in a browser.
2. Run your bot's steps against it.
3. Press **Submit** on the page. Every requirement must show **PASS**.

The practice page checks behaviour only. It does not check your code.

## 4. Lint `bot.py`

```sh
pip install ruff
ruff check --config .ruff.toml src/commit/bot.py
```

Fix every finding.

## 5. Check line limits and structure with the local API

The example includes a FastAPI service that reads `src/commit/` and returns the
`miner_output` it would send.

```sh
pip install -r ./requirements.txt
cd src
uvicorn app:app --host="0.0.0.0" --port=10002 --no-access-log --no-server-header
```

In a second terminal:

```sh
curl -s http://localhost:10002/health | jq
curl -s -X POST http://localhost:10002/solve -H "Content-Type: application/json" -d '{}' | jq
```

A successful `/solve` returns both files in `commit_files`. Swagger UI is at
`http://localhost:10002/docs` while the service runs.

Line limits:

| File | Maximum lines |
| --- | ---: |
| `bot.py` | 2,000 |
| `Dockerfile` | 500 |

## 6. Build the image

From `examples/miner_commit`, build for `linux/amd64`:

```sh
DOCKER_BUILDKIT=1 docker build --platform linux/amd64 -t myhub/rest-bv-commit:2.0.0 .
```

On Apple Silicon, the `--platform linux/amd64` flag is required.

Check your `src/commit/Dockerfile` against the allowed sources in
[v2.md](v2.md#dockerfile-sources). A download from any other source fails the
build, so a build that works on your machine can still fail if it uses a
disallowed source.

## 7. Final check before publishing

- [ ] `ruff check --config .ruff.toml src/commit/bot.py` reports no findings.
- [ ] `bot.py` is at most 2,000 lines; `Dockerfile` is at most 500 lines.
- [ ] The practice page shows PASS for every requirement.
- [ ] `bot.py` defines `run_bot(url: str) -> bool` and closes every browser it opens.
- [ ] `src/commit/` contains only `bot.py` and `Dockerfile`, with exact names.
- [ ] `POST /solve` returns both files without error.
- [ ] The image builds with `--platform linux/amd64`.
- [ ] The Dockerfile fetches only from the allowed sources.

Once these pass, publish and submit as described in the [v2 contract](v2.md).
Read the score and feedback from the platform. Local success does not guarantee
the production score.

## Troubleshooting

| Symptom | Likely cause |
| --- | --- |
| Ruff findings | Fix them; they block evaluation. |
| `/solve` returns `500` | Extra file or subdirectory in `src/commit/`, such as `__pycache__/`. Remove it. |
| `/solve` returns `422` | Wrong file name, or a file over the line limit. |
| Practice page shows FAIL | Re-check the requirement that failed on the page. |
| Image build fails | Dockerfile fetches from a disallowed source, or uses a base image that is not available. |
