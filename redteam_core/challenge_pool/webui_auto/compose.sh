#!/bin/bash
set -euo pipefail


## --- Base --- ##
# Getting path of this script file:
_PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
cd "${_PROJECT_DIR}" || exit 2

# Loading base script:
# shellcheck disable=SC1091
source ./scripts/base.sh

exitIfNoDocker

# Loading .env file (if exists):
if [ -f ".env" ]; then
	# shellcheck disable=SC1091
	source .env
fi
## --- Base --- ##


## --- Variables --- ##
_DEFAULT_SERVICE="api"
## --- Variables --- ##


## --- Functions --- ##
_doBuild()
{
	./scripts/build.sh || exit 2
	# docker compose build || exit 2
}

_doValidate()
{
	docker compose config || exit 2
}

_doStart()
{
	if [ "${1:-}" == "-l" ]; then
		shift
		# shellcheck disable=SC2068
		docker compose up -d --remove-orphans --force-recreate ${@:-} || exit 2
		_doLogs "${@:-}"
	else
		# shellcheck disable=SC2068
		docker compose up -d --remove-orphans --force-recreate ${@:-} || exit 2
	fi
}

_doStop()
{
	if [ -z "${1:-}" ]; then
		docker compose down --remove-orphans || exit 2
	else
		# shellcheck disable=SC2068
		docker compose rm -sfv ${@:-} || exit 2
	fi
}

_doRestart()
{
	if [ "${1:-}" == "-l" ]; then
		shift
		_doStop "${@:-}" || exit 2
		_doStart -l "${@:-}" || exit 2
	else
		_doStop "${@:-}" || exit 2
		_doStart "${@:-}" || exit 2
	fi
	# docker compose restart ${@:-} || exit 2
}

_doLogs()
{
	if [ -n "${1:-}" ]; then
		# docker compose logs -f --tail 100 ${@} || exit 2
		# shellcheck disable=SC2068
		docker compose ps -q ${@} | xargs -n 1 docker logs -f -n 100 || exit 2
	else
		docker compose logs -f --tail 100 || exit 2
	fi
}

_doList()
{
	docker compose ps || exit 2
}

_doPs()
{
	# shellcheck disable=SC2068
	docker compose top ${@:-} || exit 2
}

_doStats()
{
	# shellcheck disable=SC2046
	docker stats $(docker compose ps -q) || exit 2
}

_doExec()
{
	if [ -z "${1:-}" ]; then
		echoError "Not found any input."
		exit 1
	fi

	# shellcheck disable=SC2068
	docker compose exec "${_DEFAULT_SERVICE}" ${@} || exit 2
}

_doEnter()
{
	_service="${_DEFAULT_SERVICE}"
	if [ -n "${1:-}" ]; then
		_service=${1}
	fi

	echoInfo "Entering '${_service}' container..."
	docker compose exec "${_service}" /bin/bash || exit 2
}

_doImages()
{
	# shellcheck disable=SC2068
	docker compose images ${@:-} || exit 2
}

_doClean()
{
	# shellcheck disable=SC2068
	docker compose down -v --remove-orphans ${@:-} || exit 2
}

_doUpdate()
{
	if docker compose ps | grep 'Up' > /dev/null 2>&1; then
		_doStop "${@:-}" || exit 2
	fi

	# shellcheck disable=SC2068
	docker compose pull ${@:-} || exit 2
	# shellcheck disable=SC2046
	docker rmi -f $(docker images --filter "dangling=true" -q --no-trunc) > /dev/null 2>&1 || true

	# _doStart "${@:-}" || exit 2
}
## --- Functions --- ##


## --- Menu arguments --- ##
_exitOnWrongParams()
{
	echoInfo "USAGE: ${0}  build | validate | start | stop | restart | logs | list | ps | stats | exec | enter | images | clean | update"
	exit 1
}

main()
{
	if [ -z "${1:-}" ]; then
		echoError "Not found any input."
		_exitOnWrongParams
	fi

	case ${1} in
		build)
			shift
			_doBuild;;
		validate | valid | config)
			shift
			_doValidate;;
		start | run | up)
			shift
			_doStart "${@:-}";;
		stop | down | remove | rm | delete | del)
			shift
			_doStop "${@:-}";;
		restart)
			shift
			_doRestart "${@:-}";;
		logs)
			shift
			_doLogs "${@:-}";;
		list)
			_doList;;
		ps)
			shift
			_doPs "${@:-}";;
		stats | resource | limit)
			shift
			_doStats;;
		exec)
			shift
			_doExec "${@:-}";;
		enter)
			shift
			_doEnter "${@:-}";;
		images)
			shift
			_doImages "${@:-}";;
		clean | clear)
			shift
			_doClean "${@:-}";;
		update)
			shift
			_doUpdate "${@:-}";;
		*)
			echoError "Failed to parsing input: ${*}"
			_exitOnWrongParams;;
	esac

	exit
}

main "${@:-}"
## --- Menu arguments --- ##
