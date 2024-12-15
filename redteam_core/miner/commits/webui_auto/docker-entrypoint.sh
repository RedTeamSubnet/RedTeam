#!/bin/bash
set -e

# Activate conda environment
# shellcheck disable=SC1091
. /opt/conda/etc/profile.d/conda.sh
conda activate base

# Run the command passed to the container
exec "$@"