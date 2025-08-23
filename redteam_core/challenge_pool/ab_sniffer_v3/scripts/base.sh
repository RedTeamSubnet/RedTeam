#!/bin/bash
set -euo pipefail


# Date format
_DATE_FORMAT="+%Y-%m-%d %H:%M:%S %z"
_BLUE=""
_GREEN=""
_YELLOW=""
_RED=""
_NC=""

if [[ "${TERM:-}" == *"xterm"* ]]; then
	_BLUE="[34m"
	_GREEN="[32m"
	_YELLOW="[33m"
	_RED="[31m"
	_NC="[0m"
fi

echoError()
{
	_date=$(date "${_DATE_FORMAT}")
	echo -e "[${_date} | ${_RED}ERR${_NC} ]: ${*}"
}
echoWarn()
{
	_date=$(date "${_DATE_FORMAT}")
	echo -e "[${_date} | ${_YELLOW}WARN${_NC}]: ${*}"
}
echoInfo()
{
	_date=$(date "${_DATE_FORMAT}")
	echo -e "[${_date} | ${_BLUE}INFO${_NC}]: ${*}"
}
echoOk()
{
	_date=$(date "${_DATE_FORMAT}")
	echo -e "[${_date} | ${_GREEN}OK${_NC}  ]: ${*}\n"
}


exitIfNotExists()
{
	_file_path=${1}
	if [ -z "${_file_path:-}" ]; then
		echoError "_file_path is required!"
		exit 2
	fi

	if [ ! -f "${_file_path}" ]; then
		echoError "Not found ${_file_path} file."
		exit 1
	fi
}


exitIfNoGit()
{
	if [ -z "$(which git)" ]; then
		echoError "'git' not found or not installed."
		exit 1
	fi
}


exitIfNoDocker()
{
	if [ -z "$(which docker)" ]; then
		echoError "'docker' not found or not installed."
		exit 1
	fi

	if ! docker info > /dev/null 2>&1; then
		echoError "Unable to communicate with the docker daemon. Check docker is running or check your account added to docker group."
		exit 1
	fi

	if ! docker compose > /dev/null 2>&1; then
		echoError "'docker compose' not found or not installed."
		exit 1
	fi
}
