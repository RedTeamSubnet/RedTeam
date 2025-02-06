#!/bin/bash
set -euo pipefail


docker run --rm -it --name bot_container -e WUC_ACTION_LIST="" bot:latest
