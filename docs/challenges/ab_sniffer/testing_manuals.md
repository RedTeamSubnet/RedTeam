---
title: Testing Manual
---
# AB Sniffer v6 Testing Manual

This manual covers local miner testing. Local results help improve a submission, but the
official score is produced by the production scoring environment.

## Prerequisites

- Docker with the Docker Compose plugin
- A normal browser for human checks
- Miner-controlled runners for all eight target frameworks
- A bot-runner service compatible with the challenge scoring API when using `/score`
- Test hosts or virtual machines for the operating systems being evaluated
- Network access from each runner to the challenge API

The challenge repository does not provide miner-side framework runners. Miners must create
and configure their own.

## 1. Add And Validate The Detectors

Clone the current repository and enter it:

```bash
git clone https://github.com/RedTeamSubnet/ab-sniffer.git
cd ab-sniffer
```

Place the eight framework files and `headless.js` in:

```text
src/abs_challenge/challenge/templates/static/detections/
```

Keep every filename and exported `window` function unchanged. Validate the submission:

```bash
python3 skills/validate-submission/scripts/validate_submission.py
```

The validator checks the exact nine files, required exports, the 500-line limit, and the
repository ESLint configuration.

## 2. Configure And Start The Challenge

Create the environment file:

```bash
cp .env.example .env
```

Set a private API key and the local port in `.env`:

```dotenv
ABS_CHALLENGE_API_KEY=replace_with_your_private_api_key
ABS_CHALLENGE_API_PORT=10001
```

The included Compose file starts the challenge API only. To use `/score`, deploy your
bot-runner separately and configure at least:

```dotenv
ABS_CHALLENGE_BOT_RUNNER__SERVERS=[{"url":"http://bot-runner-host:8080","device_type":"linux"}]
ABS_CHALLENGE_BOT_RUNNER__API_KEY=replace_with_your_bot_runner_api_key
ABS_CHALLENGE_BOT_RUNNER__PUBLIC_BASE_URL=http://challenge-host:10001
```

The bot-runner URL must be reachable from the challenge container. The public base URL must
be reachable from browsers launched by the bot-runner. Use addresses appropriate to your
network rather than copying the example hostnames unchanged.

Start the challenge:

```bash
docker compose up -d
docker compose logs -f challenge-api
```

Confirm that it is healthy:

```bash
docker compose ps
curl http://localhost:10001/health
```

Protected endpoints such as `/score` and `/results` require the API key in the `X-API-Key`
header.

## 3. Choose A Reachable URL

The detection page is:

```text
http://<challenge-host>:<port>/_web
```

Use `localhost` only when the browser runner and challenge are on the same host. A runner in
another container or machine must use a reachable service name, LAN address, or DNS name.
Do not use `0.0.0.0` as a destination address.

## 4. Test Framework And Headless Classification

Run every target framework in headed and headless modes where supported:

- `seleniumbase`
- `seleniumdriverless`
- `pydoll`
- `patchright`
- `zendriver`
- `nodriver`
- `botasaurus`
- `puppeteerextra`

For each test, start a clean browser session, open `/_web`, wait for detection to complete,
record the results, close the browser, and repeat the run.

A correct headed automation result has:

```text
active framework: true
all other frameworks: false
Headless: false
Human: false
```

A correct headless automation result has:

```text
active framework: true
all other frameworks: false
Headless: true
Human: false
```

`headless.js` detects the browser's execution mode independently from the framework files.
It must not rely only on the user-agent string.

## 5. Test Human Sessions

Open `/_web` manually in a normal headed browser without an automation framework. A correct
human result has:

```text
all frameworks: false
Headless: false
Human: true
```

Human is inferred from the absence of framework and headless detections; it is not a
separate detector file. Test multiple clean sessions with normal navigation, typing,
scrolling, pointer movement, and developer tools usage where relevant.

Any framework or headless detection during a production human task makes the final score
zero. Human false-positive testing is therefore mandatory.

## 6. Run Local Scoring

After configuring a compatible bot-runner, submit the nine files to the authenticated
`/score` endpoint using the API documentation or your own client. Scoring schedules
automation runs and human verification in a shuffled order. When the logs request human
verification, open the displayed `/_web` URL before the human timeout expires.

After scoring, inspect authenticated `/results` output for:

- expected and submitted frameworks;
- missed detections;
- framework collisions;
- expected and reported headless state;
- headless failures; and
- missing or failed tasks.

Do not optimize only for framework recall. A broad detector may increase local recall while
creating collisions or human false positives that reduce or zero the official score.

## Testing Versus Production

Local testing does not reproduce production exactly.

| Testing environment | Production scoring environment |
| --- | --- |
| Miner-created framework runners | Private RedTeam framework runners and presets |
| Locally installed browser, driver, and framework versions | Versions installed in production runner images |
| Miner-selected OS, hardware, flags, patches, extensions, locale, timing, and network | Production infrastructure, device types, launch settings, resource limits, timing, and network |
| Run counts and configurations selected for development | Run schedule and configuration controlled by the scorer |
| Full access to local browser and service diagnostics | Only the official score and permitted result details determine the outcome |

Noticeable score differences are expected when these environments expose different
automation signals. Passing local tests does not guarantee the same production result.
Build robust detectors by testing multiple versions, operating systems, launch modes, and
runner configurations. Avoid signals that identify only one local setup.

## Test Matrix

Record repeated framework and human sessions:

| OS | Framework/session | Browser version | Mode | Expected | Actual true | Headless | Collision | Pass |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Linux | nodriver | Chromium version | Headed | nodriver | nodriver | false | No | Yes |
| Linux | human | Chromium version | Headed | human | none | false | No | Yes |

## Troubleshooting

- **Page is unreachable:** check Compose status, port mapping, firewall rules, and the URL
  used by remote runners.
- **Changes do not appear:** rebuild or recreate the container and use a fresh browser
  session without cached assets.
- **No detector runs:** inspect browser console output and challenge logs for JavaScript
  errors.
- **Multiple framework results are true:** remove shared or overly broad signals.
- **Human is false:** a framework detector or `headless.js` produced a false positive.
- **Headless is unstable:** repeat clean sessions across browser versions and launch modes.

Stop the environment when testing is complete:

```bash
docker compose down --remove-orphans
```
