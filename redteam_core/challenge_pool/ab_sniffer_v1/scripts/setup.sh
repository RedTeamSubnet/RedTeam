#!/bin/bash
set -euo pipefail

echo "INFO: Setting up challenge environment..."
echo "INFO: Copying compose override file..."
cp ./templates/compose/compose.override.dev.yml ./compose.override.yml || exit 2

echo "INFO: Configuring Docker compose override..."
printf '    command: ["/bin/bash", "-c", "uvicorn main:app --host=0.0.0.0 --port=${ABSC_API_PORT:-10001} --no-access-log --no-server-header --proxy-headers --forwarded-allow-ips='\''*'\'' --reload --reload-include='\''*.yml'\'' --reload-include='\''.env'\''"]\n' >> ./compose.override.yml || exit 2

echo "INFO: Starting challenge server..."
./compose.sh start -d || exit 2

echo "INFO: Waiting for containers to start..."
sleep 10

echo "INFO: Executing commands in container..."
./compose.sh exec "sudo service docker start" || exit 2

echo "INFO: Starting Python server with persistent logs..."
./compose.sh logs

echo "OK: Setup complete!"
