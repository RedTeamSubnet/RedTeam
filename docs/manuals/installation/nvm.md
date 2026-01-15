---
title: "NVM - Node.js"
tags: [nvm, node, node.js, npm, js, javascript, linux, macos]
---

# :simple-nvm: Install NVM (Node Version Manager) and Node.js

**NVM** is a tool for managing multiple versions of **Node.js**. It allows you to install, switch between, and manage different versions of Node.js and NPM (Node Package Manager) easily.

## Official pages

- **NVM**: <https://github.com/nvm-sh/nvm>

---

## Install on **Linux** or **macOS**

### 1. Download and install **NVM**

#### 1.1 Prepare the runtime directory for NVM

```sh
# Create runtime directory for NVM:
mkdir -vp ~/workspaces/runtimes/.nvm

# Set and export `NVM_DIR` environment variable:
export NVM_DIR="${HOME}/workspaces/runtimes/.nvm"
```

#### 1.2 Install NVM

```sh
# Get the latest release version of NVM:
export NVM_VERSION=$(curl -s https://api.github.com/repos/nvm-sh/nvm/releases/latest | grep "tag_name" | cut -d\" -f4)

# Install or update NVM:
curl -o- "https://raw.githubusercontent.com/nvm-sh/nvm/${NVM_VERSION}/install.sh" | bash

## Load NVM into the current shell session:
# For bash:
source ~/.bashrc
# For zsh:
source ~/.zshrc
```

#### 1.3 Verify NVM installation

```sh
# Check installed NVM version:
nvm --version
```

### 2. Install **Node.js** and **NPM**

#### 2.1 Create a new Node.js environment

```sh
# Install Node.js, update NPM to latest, and set environment name to `default` (change node.js version as needed):
nvm install --latest-npm --alias=default 24.12.0

# Set nvm to use `default` node.js environment:
nvm use default

# Clean NVM caches:
nvm cache clear
```

#### 2.2 Verify Node.js and NPM installation

```sh
# Check installed Node.js and NPM version:
node -v
npm -v
```

---

## References

- <https://nodejs.org>
- <https://www.npmjs.com>
- <https://pm2.keymetrics.io>
