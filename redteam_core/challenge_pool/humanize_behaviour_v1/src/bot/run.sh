#!/bin/bash
set -euo pipefail


docker run --rm -it --name bot_container -e HBC_ACTION_LIST="" bot:latest
