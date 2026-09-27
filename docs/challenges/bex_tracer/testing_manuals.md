# BEX Tracer Testing Manual

Test the same container and HTTP contract used for scoring. Put detector files
in the challenge's dedicated path, build the container, then submit and inspect
runs through Swagger UI or an automated API client.

## Prerequisites

- Docker with Docker Compose
- At least 8 GiB of memory available to the container
- An `amd64` host, or `amd64` emulation on ARM
- A checkout of the
  [BEX Tracer challenge repository](https://github.com/RedTeamSubnet/bex-tracer-challenge)

Run every command below from the repository root.

## 1. Add the detector files

Put the submission in:

```text
src/bex_tracer/challenge/templates/static/detections/
```

The current pool requires these files:

```text
ad_blockers.js
capture_recording.js
developer_tools.js
identity_security.js
media_video.js
network_vpn.js
save_research.js
tabs_workflow.js
```

Replace the existing stubs; do not add arbitrary names. Each
`<group>.js` file must define `window.detect_<group>` and return booleans
for names owned by that group:

```js
window.detect_ad_blockers = async function () {
  return {
    "uBlock Origin Lite": true,
    "AdGuard AdBlocker": false,
  };
};
```

The deployed `GET /task` response remains authoritative. If its `groups`
map differs from this list, update the local files to match it exactly.

!!! info "Why this path matters"
    The API reads these files when it creates the Swagger `POST /score`
    example. They are baked into the image during `docker compose build`.
    The path does not bypass the API contract: `/score` still evaluates the
    code in `miner_output.commit_files`.

## 2. Configure the API key

Create the local environment file:

```sh
cp .env.example .env
```

Generate a key, for example:

```sh
openssl rand -hex 16
```

Put the generated value in `.env`:

```dotenv
BEX_CHALLENGE_API_KEY=replace-with-your-generated-key
```

The key must contain 9–128 letters, digits, or hyphens. Keep it private. The
same value is entered in Swagger UI or sent as the `X-API-Key` header.

## 3. Build and start the challenge

```sh
docker compose up --build -d challenge-api
```

Detector changes require a rebuild because the files are copied into the
image. Watch startup and scoring logs with:

```sh
docker compose logs -f challenge-api
```

The API is ready at `http://localhost:10001` by default. If
`BEX_API_PORT` was changed in `.env`, use that port instead.

## 4. Authorize Swagger UI

Open:

```text
http://localhost:10001/docs
```

1. Select **Authorize**.
2. Enter the `BEX_CHALLENGE_API_KEY` value only—do not include
   `X-API-Key:` in the field.
3. Select **Authorize**, then close the dialog.

Swagger sends the value as the `X-API-Key` header. `POST /score` and
`GET /results` require it; `GET /task` is public.

## 5. Get the current task

Expand **GET /task**, select **Try it out**, then **Execute**. Its response
contains:

- `extension_names`: every label scored by the challenge;
- `groups`: required file names and the extension names each file owns;
- `random_val`: the cache-busting value used by the scoring protocol.

Keep the complete response. The `POST /score` request includes it as
`miner_input`.

## 6. Run a score

Expand **POST /score** and select **Try it out**. Swagger pre-fills
`miner_output.commit_files` from the JavaScript files that were present when
the image started.

Before selecting **Execute**, verify:

- `miner_input` contains the complete object returned by `GET /task`;
- `miner_output.commit_files` contains exactly one file for every task group;
- every `file_name` is `<group>.js`;
- every `content` value contains the intended detector source.

The request has this shape:

```json
{
  "miner_input": {
    "random_val": "value-from-get-task",
    "extension_names": ["..."],
    "groups": {
      "ad_blockers": ["..."]
    }
  },
  "miner_output": {
    "commit_files": [
      {
        "file_name": "ad_blockers.js",
        "content": "window.detect_ad_blockers = async function () { return {}; };"
      }
    ]
  }
}
```

The shortened example above shows the structure only. A real request must
include all names, groups, and required files. Scoring launches six sequential
Chrome rounds and can take time. A successful response is the final float in
`[0, 1]`.

Only one score can run at once. Another simultaneous request receives HTTP
429.

## 7. Read the detailed result

After `POST /score` completes, expand authenticated **GET /results**, select
**Try it out**, then **Execute**.

The endpoint returns the latest run's full public report:

- pool size and configured round count;
- completed and scored round counts;
- final score;
- per-round status and score;
- enabled-count, duration, failure flag, and names detected by the miner.

It intentionally does not expose the enabled extension names, expected labels,
or internal error text. Before any completed scoring run, `/results` returns
HTTP 404. A newer run replaces the previous report.

## Automate the same flow

Swagger UI is optional. An automated client can call the same endpoints:

```sh
curl -sS http://localhost:10001/task

curl -sS \
  -X POST http://localhost:10001/score \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  --data @score-request.json

curl -sS \
  -H "X-API-Key: your-api-key" \
  http://localhost:10001/results
```

An automation script should:

1. fetch `GET /task`;
2. derive the required `<group>.js` list from `groups`;
3. read and JSON-encode each local detector file;
4. send `{miner_input, miner_output}` to `POST /score`;
5. wait for the response before requesting `GET /results`.

Do not hardcode task data or send overlapping score requests.

## Common errors

| Status | Meaning |
|---|---|
| 401 | API key missing, malformed, or incorrect |
| 404 from `/results` | No score has completed since startup |
| 422 | Missing, duplicate, or unexpected group file; invalid request body; file limit exceeded |
| 429 | Another scoring run is already active |
| 500 | Browser, pool, or other challenge infrastructure failed; inspect container logs |

## Stop the container

```sh
docker compose down
```

For production submission packaging, see
[Building a submission commit](../../miner/workflow/3.build-and-publish.md).
