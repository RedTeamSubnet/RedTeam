# Bot Virus Testing Manual

## Prerequisites

- Docker Engine and Docker Compose
- Access to the Bot Virus challenge API
- Python 3.10+ for the score-submission helper

## Clone and prepare the challenge

Clone the dedicated challenge repository, then create local configuration:

```sh
git clone https://github.com/RedTeamSubnet/bot-virus-challenge.git
cd bot-virus-challenge
cp .env.example .env
```

Put your submission in this directory in the cloned repository:

```text
src/bv_challenge/challenge/commit/bot
```

Replace only these two files:

- `src/bv_challenge/challenge/commit/bot/bot.py`
- `src/bv_challenge/challenge/commit/bot/Dockerfile`

The score helper reads exactly these files. Do not rename them or add extra
submission files.

## Start the challenge

Start the local challenge stack from the repository root:

```sh
docker compose up -d
```

The default API port is `10001`. Confirm readiness and inspect the live
contract:

```sh
curl -s http://localhost:10001/health | jq
curl -s http://localhost:10001/openapi.json | jq
```

Swagger UI is available at `http://localhost:10001/docs`.

## Configure local checks

The local stack can run each evaluation layer independently. In `.env`, set the
following Boolean fields:

```dotenv
BV_CHALLENGE_SIMPLE_BOT_CHECK_ENABLED=true
BV_CHALLENGE_WEB_CHECK_ENABLED=true
```

Set a field to `false` to disable that layer during local development. Keep at
least one layer enabled. Simple Bot is the first, pass/fail layer and contains
the most common bot checks. Browser-web is the main layer and determines the
submission score.

## Simple Bot rate limit

Simple Bot permits **20 checks per hour**. Avoid repeatedly using it while
iterating locally. Disable it temporarily with
`BV_CHALLENGE_SIMPLE_BOT_CHECK_ENABLED=false` when you need to focus on the
browser-web check, then re-enable it before validating the complete flow.

## Test the API workflow

Use the included `bv-score-submission` skill helper to start scoring. It reads
`bot.py` and `Dockerfile`, obtains a fresh task from `GET /task`, and submits
them to `POST /score`.

`POST /score` requires API-key authentication. Set the same private key as
`BV_CHALLENGE_API_KEY` in `.env`, then make it available to the helper:

```sh
export BV_CHALLENGE_API_KEY='replace-with-authorized-key'
python3 skills/bv-score-submission/scripts/submit_score.py \
  --base-url http://localhost:10001
```

The helper sends the key as `X-API-Key`. It prints the score response but never
prints the key. Read the latest evaluator feedback at `GET /result`.

Never commit the API key or include it in a payload file. Store it in a local
environment variable or secret manager.

## Before publishing

- Test clean browser sessions and multiple supported runtime configurations.
- Verify `bot.py` and `Dockerfile` are the only submission files in the
  required commit directory.
- Re-enable both local checks before validating the complete flow.
- Check challenge API and runner logs together when a build, execution, or
  browser-web check fails.
- Remember local browser signals may differ from the production runner.
