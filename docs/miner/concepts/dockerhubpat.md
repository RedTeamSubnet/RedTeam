---
title: Docker Hub Registry
tags:
  - miner
  - docker
  - registry
  - pat
---

# 🐳 Docker Hub Registry

!!! note ""
    Need to install Docker first? See the [Docker installation guide](https://docs.theredteam.io/latest/manuals/installation/docker/).

---

## 🔑 One Username Policy

Your `active_commit` must reference images from a **single Docker Hub username**. All image references should follow this format:

```
<your-username>/<repository>:<tag>
```

Using multiple usernames will cause authentication failures during the validation process because only one set of credentials is used for pulling.

!!! warning "Common mistake"
    If you collaborate with others, make sure everyone pushes to repositories under the **same** Docker Hub username. Mixing usernames like `alice/solver` and `bob/detector` in one `active_commit` will break image pulls.

---

## 🔒 Private Repositories

Your Docker Hub repository should be set to **private**. Public repositories expose your solution to other participants.

### Making a repository private

1. Go to [hub.docker.com](https://hub.docker.com) and sign in.
2. Navigate to **Repositories** and select the repository.
3. Click **Settings**.
4. Under **Visibility**, select **Private**.
5. Click **Save**.

??? tip "Set private as default for new repositories"
    You can avoid accidentally creating public repos by changing your default visibility:

    1. Go to **Account Settings** → **Default privacy**.
    2. Set it to **Private**.

    Now every time you `docker push` to a new repository, it will be created as private automatically.

---

## 🎫 Generating a Personal Access Token (PAT)

A PAT is a secure alternative to your Docker Hub password. It can be scoped to specific permissions and revoked at any time — much safer than sharing your account password.

### Step 1 — Sign in to Docker Hub

Head over to [hub.docker.com](https://hub.docker.com) and log in with the account that owns your miner image repositories.

### Step 2 — Open the PAT settings

You can get there in two ways:

- **Direct link:** [hub.docker.com/settings/security](https://hub.docker.com/settings/security)
- **Via UI:** Click your **profile avatar** (top-right) → **Account settings** → **Personal access tokens** (under **Security** in the sidebar)

### Step 3 — Create a new token

1. Click **Generate new token**.
2. Give it a clear name (e.g., `redteam-miner-pat`).
3. Set **Access permissions** to **Read-only**.
4. Click **Generate**.

!!! tip "Why Read-only?"
    Read-only is all you need for image pulls during validation. Following the principle of least privilege keeps your account safer — if the token is ever leaked, the damage is minimal.

### Step 4 — Copy and save the token

Your token will be shown **only once**. Copy it immediately and store it somewhere safe.

!!! danger "Don't lose your token!"
    Docker Hub will **never** show this token value again. If you lose it, you'll need to revoke it and generate a new one. Store it in a password manager or an encrypted file.

### Step 5 — Verify it works

Before plugging the PAT into your miner config, quickly verify it from your terminal:

```bash
docker login -u <your-username>
```

When prompted for a password, paste your **PAT** (not your Docker Hub password). You should see:

```
Login Succeeded
```

??? example "One-liner for scripts"
    If you prefer a non-interactive login (useful in CI/CD or automation scripts):

    ```bash
    echo "<your-pat>" | docker login -u <your-username> --password-stdin
    ```

### Step 6 — Use the token in your miner

Provide your credentials in the miner configuration:

| Field | Value |
|---|---|
| `docker_hub_username` | Your Docker Hub username |
| `docker_hub_pat` | The PAT you generated |

!!! warning "Keep your PAT out of version control"
    Never hardcode your PAT in source code or commit it to Git. Use environment variables or a `.env` file:

    ```bash
    export DOCKER_HUB_USERNAME="your-username"
    export DOCKER_HUB_PAT="dckr_pat_xxxxxxxxxxxxx"
    ```

    Add `.env` to your `.gitignore` if you use a dotenv file.

---

## 🛠 Managing Your Tokens

You can manage all your tokens from the [security settings page](https://hub.docker.com/settings/security).

??? info "Available actions"
    | Action | When to use |
    |---|---|
    | **Revoke** | Token has been compromised or is no longer needed |
    | **Regenerate** | You want a new value but keep the same name and permissions |
    | **Create new** | You need a separate token for a different purpose |

    You can have multiple tokens, but only **one** should be used for your miner configuration.

---

## ❓ Troubleshooting

??? question "Authentication failed during image pull"
    - Double-check that the PAT is correct and hasn't been revoked.
    - Make sure you're using the PAT, not your Docker Hub password.
    - Verify the token hasn't expired — check the [security settings page](https://hub.docker.com/settings/security).

??? question "Repository not found"
    - Confirm the image name matches exactly: `<username>/<repo>:<tag>`.
    - Ensure the PAT belongs to the same account that owns the repository.
    - Check that the repository actually exists on Docker Hub.

??? question "Multiple username errors in `active_commit`"
    - All images in your `active_commit` must use the **same** Docker Hub username.
    - If you need images from different sources, push them all under one account first.

??? question "My images are publicly visible"
    - Go to each repository's **Settings** → **Visibility** → switch to **Private**.
    - Set your default visibility to private to prevent this in the future (see the tip above).
