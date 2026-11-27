# Bot Virus Challenge

Bot Virus evaluates a miner-supplied browser bot. You submit a containerized
bot (`bot.py` and `Dockerfile`). The platform evaluates it and returns a score
with feedback.

**Active version: [v2](v2.md).** Submissions for v1 are no longer accepted.

## How it works

1. You write `bot.py` and `Dockerfile` following the [v2 contract](v2.md#submission-contract).
2. You verify them locally with the miner commit example (see the [testing manual](testing_manuals.md)).
3. You build and publish your image, then submit it.
4. The platform evaluates your image and reports the score and feedback.

The evaluation environment is private and is not available to miners. Local
checks confirm that your submission meets the requirements, but a local pass
does not guarantee the production score.

## Submission at a glance

| File | Limit | Notes |
| --- | --- | --- |
| `bot.py` | 2,000 lines | Must pass Ruff. Must define `run_bot(url: str) -> bool`. |
| `Dockerfile` | 500 lines | Fetch only from the allowed package sources. Build for `linux/amd64`. |

Exactly these two files, with these exact names.

## Local testing

Use the miner commit example in the
[challenge repository](https://github.com/RedTeamSubnet/bot-virus-challenge/tree/main/examples/miner_commit):

```sh
git clone https://github.com/RedTeamSubnet/bot-virus-challenge.git
cd bot-virus-challenge/examples/miner_commit
```

The [testing manual](testing_manuals.md) covers the practice page, Ruff, the
local `/solve` check, and the image build.

## Resources

- [Bot Virus v2](v2.md): current contract and feedback
- [Testing manual](testing_manuals.md): local checks before submitting
- [Bot Virus v1 (deprecated)](depricated/v1.md): historical reference only
- [Building a submission commit](../../miner/workflow/3.build-and-publish.md)
- [Dashboard](../../miner/concepts/dashboard.md)
- [Challenge repository](https://github.com/RedTeamSubnet/bot-virus-challenge)
