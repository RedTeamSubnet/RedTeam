# Bot Virus Testing Manual

## Prerequisites

- Docker Engine and Docker Compose
- Access to the Bot Virus challenge API
- Python 3.10+ only when developing the challenge locally

## Validate the submission image

Your submission must provide exactly `bot.py` and `Dockerfile`. Build for the
same platform used by the evaluator:

```sh
docker build --platform linux/amd64 -t bot-virus-submission .
```

Run the image locally using the entrypoint and environment expected by your
bot. Confirm that it starts from a clean session and that required dependencies
are included in the image rather than relying on host files or host services.

## Run a local challenge stack

From the Bot Virus challenge repository:

```sh
cp .env.example .env
./compose.sh validate
./compose.sh start -l
```

The default API port is `10001`. Confirm readiness and inspect the live
contract:

```sh
curl -s http://localhost:10001/health | jq
curl -s http://localhost:10001/openapi.json | jq
```

Swagger UI is available at `http://localhost:10001/docs`.

## Test the API workflow

1. Retrieve a task from `GET /task`.
2. Build a score request using the live OpenAPI schema.
3. Send it to `POST /score` with `X-API-Key`.
4. Read evaluation feedback from `GET /result`.

Never commit the API key or include it in a payload file. Store it in a local
environment variable or secret manager.

## Before publishing

- Test clean browser sessions and multiple supported runtime configurations.
- Verify final image is `linux/amd64` and fully tagged.
- Check challenge API and runner logs together when a build, execution, or
  browser-web check fails.
- Remember local browser signals may differ from the production runner.
