#!/bin/bash
set -euo pipefail


echo "INFO: Running 'rest.rt-hb-challenger' docker-entrypoint.sh..."

_doStart()
{
	sudo service docker start || exit 2
	sleep 2
	# sudo docker pull redteamsn61/hbc-bot-base:latest || exit 2
	# sudo docker load -i /app/redteamsn61_hbc-bot-base.tar || exit 2
	# sudo docker tag sha256:2a10d9beec491035db67bbc818fc3356cdc0bddfa3fc4bd3136c5924ed21bd14 redteamsn61/hbc-bot-base:latest || exit 2
	exec sg docker "exec python -u ./main.py" || exit 2
	# exec python -u ./main.py || exit 2
	# exec uvicorn main:app --host=0.0.0.0 --port=${HBC_API_PORT:-10001} --no-access-log --no-server-header --proxy-headers --forwarded-allow-ips='*' || exit 2
	exit 0
}


main()
{
	umask 0002 || exit 2
	find "${HBC_HOME_DIR}" "${HBC_API_DATA_DIR}" "${HBC_API_LOGS_DIR}" "${HBC_API_TMP_DIR}" -path "*/modules" -prune -o -name ".env" -o -print0 | sudo xargs -0 chown -c "${USER}:${GROUP}" || exit 2
	find "${HBC_API_DIR}" "${HBC_API_DATA_DIR}" -type d -not -path "*/modules/*" -not -path "*/scripts/*" -exec sudo chmod 770 {} + || exit 2
	find "${HBC_API_DIR}" "${HBC_API_DATA_DIR}" -type f -not -path "*/modules/*" -not -path "*/scripts/*" -exec sudo chmod 660 {} + || exit 2
	find "${HBC_API_DIR}" "${HBC_API_DATA_DIR}" -type d -not -path "*/modules/*" -not -path "*/scripts/*" -exec sudo chmod ug+s {} + || exit 2
	find "${HBC_API_LOGS_DIR}" "${HBC_API_TMP_DIR}" -type d -exec sudo chmod 775 {} + || exit 2
	find "${HBC_API_LOGS_DIR}" "${HBC_API_TMP_DIR}" -type f -exec sudo chmod 664 {} + || exit 2
	find "${HBC_API_LOGS_DIR}" "${HBC_API_TMP_DIR}" -type d -exec sudo chmod +s {} + || exit 2
	chmod ug+x "${HBC_API_DIR}/main.py" || exit 2
	# echo "${USER} ALL=(ALL) ALL" | sudo tee -a "/etc/sudoers.d/${USER}" > /dev/null || exit 2
	echo ""

	## Parsing input:
	case ${1:-} in
		"" | -s | --start | start | --run | run)
			_doStart;;
			# shift;;
		-b | --bash | bash | /bin/bash)
			shift
			if [ -z "${*:-}" ]; then
				echo "INFO: Starting bash..."
				/bin/bash
			else
				echo "INFO: Executing command -> ${*}"
				exec /bin/bash -c "${@}" || exit 2
			fi
			exit 0;;
		*)
			echo "ERROR: Failed to parsing input -> ${*}"
			echo "USAGE: ${0}  -s, --start, start | -b, --bash, bash, /bin/bash"
			exit 1;;
	esac
}

main "${@:-}"
