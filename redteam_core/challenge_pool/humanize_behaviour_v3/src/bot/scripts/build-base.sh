#!/bin/bash
set -euo pipefail


# Getting path of this script file:
_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
_PROJECT_DIR="$(cd "${_SCRIPT_DIR}/.." >/dev/null 2>&1 && pwd)"
cd "${_PROJECT_DIR}" || exit 2

# Loading .env file (if exists):
if [ -f ".env" ]; then
	# shellcheck disable=SC1091
	source .env
fi


docker build \
	--progress plain \
	--platform linux/amd64 \
	-t redteamsn61/hbc-bot-base:latest \
	-f Dockerfile.base \
	.
