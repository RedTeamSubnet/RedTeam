---
title: Testing Manual
---
# ADA-3 Testing Manual

This manual covers local miner testing for ADA-3. Testing is primarily semi-automated: miners
run each supported anti-detect browser against the challenge page and inspect whether the page
classifies the browser, the browser mode, and human sessions correctly. Local results help
improve a submission, but the official score is produced by the production scoring
environment.

## Prerequisites

- Docker with the Docker Compose plugin
- A normal browser for human checks
- Miner-controlled installations of the configured anti-detect browsers, each with a valid
  licence and a local profile
- Test hosts or virtual machines for Linux, macOS, and Windows
- Network access from each test host to the challenge API

Miners are responsible for licensing, configuring, and running their own anti-detect browser
installations. The challenge repository does not provide them, and each is a paid product.

!!! warning "Runner differences"
    Miner installations may differ from the private runners used by the challenge because of
    product versions, operating systems, profile settings, launch arguments, and patches. Do
    not rely on one runner configuration or one observed signal. Test multiple
    implementations, launch modes, browser versions, and operating systems to make detection
    logic robust.

The active target list lives in
[`challenge.yml`](https://github.com/RedTeamSubnet/ada-detection-challenge/blob/main/src/aad_challenge/challenge/api/configs/challenge.yml).
Current targets: `ads_power`, `dolphin_anty`, `gologin`, `multilogin`, `octo`.

## 1. Add Detection Scripts

Place all six JavaScript files in:

```text
src/aad_challenge/challenge/templates/static/detections/
```

Keep the expected filenames and exported function names. Validate before testing:

```bash
python3 skills/validate-submission/scripts/validate_submission.py
```

## 2. Configure The Challenge

```bash
cp .env.example .env
```

Set a private challenge API key in `.env`:

```dotenv
AAD_CHALLENGE_API_KEY=replace_with_your_private_api_key
AAD_CHALLENGE_API_PORT=10001
```

The API key must be longer than eight characters and contain only letters, numbers,
underscores, and hyphens. Protected endpoints require it in the `X-API-Key` header. If port
`10001` is unavailable, change both port variables to the same available port.

## 3. Start The Challenge Container

```bash
docker compose up -d
```

or:

```bash
./compose.sh start -l
```

Confirm the service is running:

```bash
docker compose ps
curl http://localhost:${AAD_CHALLENGE_API_PORT:-10001}/health
```

## 4. Choose A Reachable Test URL

The detection page is served at `http://<challenge-host>:<port>/_web`.

- Runner on the same machine: `http://localhost:10001/_web`
- Runner in another container: use a reachable Compose service name or host address
- Runner on another machine: use the challenge host's LAN IP or DNS name, for example
  `http://192.168.1.20:10001/_web`

`0.0.0.0` is a bind address. Do not use it as a destination from another machine. Ensure the
port is reachable through host firewalls and container port mapping.

## 5. Test Every Anti-Detect Browser

Run every configured browser against the `/_web` URL in both headed and headless mode where
the product supports both, and repeat on Linux, macOS, and Windows. If a browser or mode is
unsupported on an operating system, record that limitation rather than silently skipping it.

For each browser and mode:

1. Start a clean browser session.
2. Navigate to the `/_web` URL.
3. Wait for the page to show `Done`, or select **Run detections**.
4. Capture the displayed results.
5. Close the session and repeat enough times to detect unstable behavior.

## 6. Interpret The Results

A correct anti-detect browser run has the active browser set to `true`, every other browser
set to `false`, **Human** set to `false`, and **Headless** matching the actual browser mode.

```text
ads_power: true
all other browsers: false
Human: false
Headless: false        # true for a headless run
```

A collision occurs when more than one browser detector returns `true`. Remove collisions
before submission — they reduce browser accuracy and can create human false positives.

## 7. Test Human Sessions

Open `/_web` manually in a normal headed browser without an anti-detect browser. A correct
human result has all browsers `false`, **Human** `true`, and **Headless** `false`.

Human testing is mandatory. Any browser or headless detector firing during a human task can
reduce the complete challenge score to zero. Test multiple fresh human sessions across
operating systems, including normal interaction such as navigation, pointer movement, typing,
and scrolling.

## 8. Check Headless Results

Headless testing is semi-automated. Two possible approaches:

- **Screenshot approach**: run the browser headless, wait for detection to complete, take a
  screenshot of the page, and inspect the browser cards and the **Headless** result.
- **Miner-implemented result capture**: place detection results in `localStorage` and retrieve
  them through your anti-detect browser. This is a suggestion only — it is not implemented or
  supported by the challenge, and RedTeam is not responsible for its accuracy.

Do not include testing-only storage or extraction logic in the final submission.

## 9. Record A Test Matrix

Record at least the following, including repeated runs and human sessions:

| OS    | Anti-detect browser | Engine version   | Mode   | Expected  | Actual true | Headless | Collision | Pass |
| ----- | ------------------- | ---------------- | ------ | --------- | ----------- | -------- | --------- | ---- |
| Linux | ads_power           | Chromium version | Headed | ads_power | ads_power   | false    | No        | Yes  |

A submission is ready only when results are stable, browser-specific, collision-free, and
correct for headed and headless modes.

## Troubleshooting

- **Page is unreachable**: verify `docker compose ps`, port mapping, firewall rules, and the
  host address used by the runner.
- **Remote runner uses `localhost`**: replace it with the challenge host's reachable IP or DNS
  name.
- **Changes do not appear**: rebuild or recreate the challenge container, then start a fresh
  browser session without cache.
- **No detector runs**: inspect the browser console and challenge logs for JavaScript errors.
- **Multiple detectors are true**: isolate shared signals and tighten browser-specific
  conditions.
- **Human is false in a manual browser**: at least one browser detector or the headless
  detector produced a false positive.
- **Headless result is unstable**: repeat clean sessions across browser versions and inspect
  screenshots before changing the detector.

Stop the environment when testing is complete:

```bash
docker compose down --remove-orphans
```
