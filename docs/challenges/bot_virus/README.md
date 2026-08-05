# Bot Virus Challenge

Bot Virus evaluates whether a miner-supplied browser bot can complete the
challenge while avoiding configured bot-detection checks. It is an active
challenge. Submit exactly two files: `bot.py` and `Dockerfile`.

## How it works

1. The miner receives a task from the challenge API.
2. The miner returns `bot.py` and `Dockerfile` in the task's required output
   schema.
3. The challenge builds the submitted container in an isolated runner.
4. The runner applies the simple-bot gate and browser-web checks, then returns
   feedback and a score.

The challenge is evaluated in an environment different from a typical local
browser. Test across supported browsers, operating systems, and headed/headless
configurations; local success does not guarantee the production score.

## Submission contract

`miner_output.commit_files` must contain exactly these files:

- `bot.py` — bot implementation.
- `Dockerfile` — image definition used by the isolated runner.

Do not add files, change the file names, or assume a fixed task payload. Read
the request/response schemas from the deployed challenge's OpenAPI document
before integrating.

## Resources

- [Bot Virus v1](v1.md)
- [Testing manual](testing_manuals.md)
- [Building a submission commit](../../miner/workflow/3.build-and-publish.md)
- [Dashboard](../../miner/concepts/dashboard.md)
- [Challenge repository](https://github.com/RedTeamSubnet/bot-virus-challenge)
