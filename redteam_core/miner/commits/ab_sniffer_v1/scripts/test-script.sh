#!/bin/bash

set -euo pipefail

curl -X 'GET' \
  'http://127.0.0.1:10002/test-script' \
  -H 'accept: application/json' | jq
