# CI/CD Versioning Standardization — Design Spec

**Date:** 2026-05-16
**Status:** Approved
**Repos in scope:** RedTeamSubnet/RedTeam · RedTeamSubnet/historical-fingerprinter-challenge · RedTeamSubnet/flowradar-challenge

---

## Problem

Three repositories in the RedTeam org use inconsistent versioning conventions across their CI/CD release pipelines:

- Docker image tags are missing the required date suffix.
- Git tags in challenge repos carry a `v` prefix while the version files do not.
- The workflow-2 push-tag trigger (`v*.*.*-*`) never fires because bump-version never creates a matching tag.
- bump-version in challenge repos omits the `-t` flag so no git tag is created at all.

---

## Target Standard

| Artifact | Pattern | Example |
|----------|---------|---------|
| Docker image tag | `major.minor.patch-yyyy-mm-dd` | `2.0.1-2026-05-16` |
| Python package | `major.minor.patch` | `4.6.1` |
| Git tag | `major.minor.patch` (no `v` prefix) | `2.0.1` |
| GitHub Release name | `major.minor.patch` | `2.0.1` |
| compose.yml image | `image:major.minor.patch` | `redteamsubnet61/historical_fingerprinter:2.0.1` |

---

## Audit Results

### RedTeam (main) — `RedTeamSubnet/RedTeam`

| Item | Current | Target | Action |
|------|---------|--------|--------|
| Python package version | `4.6.1` | `major.minor.patch` | None — already compliant |
| Version source | `src/redteam_core/__version__.py` | same | None |
| Git tag | `v4.6.1` | `4.6.1` | Fix `bump-version.sh` |
| Workflow-2 trigger | `v*.*.*` | `*.*.*` | Fix trigger pattern |
| GitHub release name | `v4.6.1` | `4.6.1` | Fix `release.sh` |
| Docker images | none | none | No action |

### historical-fingerprinter-challenge — `RedTeamSubnet/historical-fingerprinter-challenge`

| Item | Current | Target | Action |
|------|---------|--------|--------|
| Version source | `VERSION.txt` (`2.0.0`) | same | None |
| Docker image tag | `:2.0.0` | `:2.0.0-2026-05-16` | Add date step + tag |
| compose.yml image | `image:2.0.0` | `image:2.0.0` | None |
| Git tag | `v2.0.0` | `2.0.0` | Fix `bump-version.sh` |
| Workflow-1 bump call | `-c -p` (no tag) | `-c -t -p` | Add `-t` flag |
| Workflow-2 trigger | `v*.*.*-*` (broken) | `*.*.*` | Fix trigger pattern |

### flowradar-challenge — `RedTeamSubnet/flowradar-challenge`

Same issues and same fixes as `historical-fingerprinter-challenge`.

---

## Design Decisions

### Date source for Docker tags

The `yyyy-mm-dd` date is captured at CI build time via `date +%Y-%m-%d`. It is not stored in `VERSION.txt`, git tags, or compose files. This keeps version files clean and makes the date purely a deployment-time artifact.

### compose.yml not updated with date

compose.yml is used for local development and pinned deploys. It keeps `image:X.Y.Z` without a date. Only Docker Hub published images get the date suffix.

### No `v` prefix on git tags

All three repos will produce bare semver git tags (`2.0.1`) going forward. Existing tags (`v4.6.1`, `v2.0.0`, etc.) are not renamed — only future releases change.

### Three Docker tags per release

Each Docker build publishes three tags:
- `:latest` — always the newest build
- `:X.Y.Z` — pinned semver, no date
- `:X.Y.Z-yyyy-mm-dd` — pinned semver with build date for full traceability

---

## File Changes

### All three repos — `scripts/bump-version.sh`

Remove `v` prefix from tag creation and push:

```diff
- git tag "v${_new_version}"
+ git tag "${_new_version}"

- git push ... "v${_new_version}"
+ git push ... "${_new_version}"
```

### Main RedTeam repo — `scripts/release.sh`

Remove `v` prefix from GitHub release:

```diff
- gh release create "v${_current_version}" ./dist/* ...
+ gh release create "${_current_version}" ./dist/* ...
```

### Main RedTeam repo — `.github/workflows/2.build-publish.yml`

Fix push-tag trigger:

```diff
  push:
    tags:
-     - "v*.*.*"
+     - "*.*.*"
```

### Challenge repos — `.github/workflows/1.bump-version.yml`

Add `-t` flag to create git tags:

```diff
- ./scripts/bump-version.sh -b=${{ inputs.bump_type }} -c -p
+ ./scripts/bump-version.sh -b=${{ inputs.bump_type }} -c -t -p
```

### Challenge repos — `.github/workflows/2.build-publish.yml`

Fix push-tag trigger, add date step, add date-suffixed Docker tag:

```diff
  push:
    tags:
-     - "v*.*.*-*"
+     - "*.*.*"

  - name: Get version
    run: echo "_VERSION=$(./scripts/get-version.sh)" >> ${GITHUB_ENV}
+ - name: Get date
+   run: echo "_DATE=$(date +%Y-%m-%d)" >> ${GITHUB_ENV}

  tags: |
    ${{ secrets.DOCKERHUB_USERNAME }}/IMAGE_NAME:latest
    ${{ secrets.DOCKERHUB_USERNAME }}/IMAGE_NAME:${{ env._VERSION }}
+   ${{ secrets.DOCKERHUB_USERNAME }}/IMAGE_NAME:${{ env._VERSION }}-${{ env._DATE }}
```

---

## Out of Scope

- Renaming existing git tags (`v4.6.1`, `v2.0.0`)
- Updating `compose.yml` with date suffix
- Changes to Python publishing steps (commented out in main repo)
- Changes to `sync-versions.sh` (it correctly propagates semver without date to compose)
- Changes to `3.create-release.yml` or `4.update-changelog.yml` (not version-tag-related)

---

## Acceptance Criteria

- [ ] All three repos produce git tags as `X.Y.Z` (no `v` prefix) on next release
- [ ] Both challenge repos' Docker images on Docker Hub are tagged `:X.Y.Z-yyyy-mm-dd` on every release
- [ ] Workflow-2 push-tag trigger fires correctly after bump-version
- [ ] compose.yml image references remain as `image:X.Y.Z`
- [ ] Python package version in main repo remains `major.minor.patch`
- [ ] CI pipelines are green after changes
