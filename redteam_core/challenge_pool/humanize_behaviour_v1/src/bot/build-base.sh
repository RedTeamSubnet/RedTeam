#!/bin/bash
set -euo pipefail


docker build -t redteamsn61/hbc-bot-base:latest -f Dockerfile.base .
