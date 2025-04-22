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


## --- Variables --- ##
# Load from envrionment variables:
IMG_REGISTRY=${IMG_REGISTRY:-redteamsubnet61}
IMG_REPO=${PROJECT_SLUG:-hbc-bot-base}

# Flags:
_IS_CROSS_COMPILE=false


_buildImage()
{
	DOCKER_BUILDKIT=1 docker build \
		--progress plain \
		-t "${IMG_REGISTRY}/${IMG_REPO}:latest" \
		-f Dockerfile.base \
		. || exit 2
}


_crossBuildPush()
{
	if ! docker buildx ls | grep new_builder > /dev/null 2>&1; then
		echo "INFO: Creating new builder..."
		docker buildx create --driver docker-container --bootstrap --use --name new_builder || exit 2
		echo -e "OK: Done.\n"
	fi

	echo "INFO: Cross building images (linux/amd64, linux/arm64): ${IMG_REGISTRY}/${IMG_REPO}:latest"
	docker buildx build \
		--progress plain \
		--platform linux/amd64,linux/arm64 \
		--cache-from=type="registry,ref=${IMG_REGISTRY}/${IMG_REPO}:cache-latest" \
		--cache-to=type="registry,ref=${IMG_REGISTRY}/${IMG_REPO}:cache-latest,mode=max" \
		-t "${IMG_REGISTRY}/${IMG_REPO}:latest" \
		-f ./Dockerfile.base \
		--push \
		. || exit 2
	echo -e "OK: Done.\n"

	echo "INFO: Removing new builder..."
	docker buildx rm new_builder || exit 2
	echo -e "OK: Done.\n"
}


main()
{
	## --- Menu arguments --- ##
	if [ -n "${1:-}" ]; then
		for _input in "${@:-}"; do
			case ${_input} in
				-x | --cross-compile)
					_IS_CROSS_COMPILE=true
					shift;;
				*)
					echoError "Failed to parsing input -> ${_input}"
					echoInfo "USAGE: ${0}  -x, --cross-compile"
					exit 1;;
			esac
		done
	fi

	if [ ${_IS_CROSS_COMPILE} == false ]; then
		_buildImage
	else
		_crossBuildPush
	fi
}


main "$@"
