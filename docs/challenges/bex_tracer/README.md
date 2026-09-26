# BEX Tracer Challenge

BEX Tracer is an active browser-extension classification challenge. A scoring
round launches Chrome with a secret subset of real extensions and asks
miner-supplied JavaScript to identify which extension names are active.

## Current version

[BEX Tracer v1](v1.md) uses these production defaults:

| Setting | Value |
|---|---:|
| Published pool | 89 extension names in 8 groups |
| Enabled per round | 12 |
| Rounds per score | 6, sequential |
| Script budget | 10 seconds |
| Metric | Mean of per-round Matthews correlation coefficients |

Runtime configuration can change. Treat the deployed `GET /task` response as
authoritative for extension names, group names, and required submission files.

## Submission

Submit exactly one JavaScript file per group returned by `GET /task`. Name
each file `<group>.js` and define `window.detect_<group>`. Each detector
returns an object mapping the extension names in its own group to booleans.

Store IDs are not part of the miner contract. Chrome assigns fresh unpacked
extension IDs from secret staging paths every round, so static
`chrome-extension://<store-id>/...` lookup tables do not work.

## Resources

- [BEX Tracer v1 specification](v1.md)
- [Testing manual](testing_manuals.md)
- [Building a submission commit](../../miner/workflow/3.build-and-publish.md)
- [Dashboard](../../miner/concepts/dashboard.md)
- [Challenge repository](https://github.com/RedTeamSubnet/bex-tracer-challenge)
