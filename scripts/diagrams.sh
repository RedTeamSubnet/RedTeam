#!/usr/bin/env bash
set -euo pipefail


## --- Base --- ##
_SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]:-"$0"}")" >/dev/null 2>&1 && pwd -P)"
_PROJECT_DIR="$(cd "${_SCRIPT_DIR}/.." >/dev/null 2>&1 && pwd)"
cd "${_PROJECT_DIR}" || exit 2


# shellcheck disable=SC1091
[ -f .env ] && . .env


if ! command -v dot >/dev/null 2>&1; then
	echo "[ERROR]: Not found 'dot' command, please install 'graphviz' first!" >&2
	exit 1
fi

if ! command -v python >/dev/null 2>&1; then
	echo "[ERROR]: Not found 'python' command, please install it first!" >&2
	exit 1
fi

if ! command -v pyreverse >/dev/null 2>&1; then
	echo "[ERROR]: Not found 'pyreverse' command, please install 'pylint' first!" >&2
	exit 1
fi
## --- Base --- ##


## --- Variables --- ##
# Load from envrionment variables:
MODULE_NAME="${MODULE_NAME:-redteam_core}"
MODULE_DIR="${MODULE_DIR:-./src/${MODULE_NAME}}"
OUTPUT_DIR="${OUTPUT_DIR:-./docs/diagrams}"


_MODULE_NAME=""
_MODULE_DIR=""
_OUTPUT_DIR=""
## --- Variables --- ##


## --- Menu arguments --- ##
_usage_help() {
	cat <<EOF
USAGE: ${0} [options]

OPTIONS:
    -m, --module-name [NAME]    Module name. Default: 'redteam_core'
    -d, --module-dir [DIR]      Module directory. Default: './src/redteam_core'
    -o, --output-dir [DIR]      Output directory. Default: './docs/diagrams'
    -h, --help                  Show this help message.

EXAMPLES:
    ${0} --module-name my_module01
    ${0} -m=my_module01 -o=./docs/diagrams
EOF
}

while [ $# -gt 0 ]; do
	case "${1}" in
		-m | --module-name)
			[ $# -ge 2 ] || { echo "[ERROR]: ${1} requires a value!" >&2; exit 1; }
			_MODULE_NAME="${2}"
			shift 2;;
		-m=* | --module-name=*)
			_MODULE_NAME="${1#*=}"
			shift;;
		-d | --module-dir)
			[ $# -ge 2 ] || { echo "[ERROR]: ${1} requires a value!" >&2; exit 1; }
			_MODULE_DIR="${2}"
			shift 2;;
		-d=* | --module-dir=*)
			_MODULE_DIR="${1#*=}"
			shift;;
		-o | --output-dir)
			[ $# -ge 2 ] || { echo "[ERROR]: ${1} requires a value!" >&2; exit 1; }
			_OUTPUT_DIR="${2}"
			shift 2;;
		-o=* | --output-dir=*)
			_OUTPUT_DIR="${1#*=}"
			shift;;
		-h | --help)
			_usage_help
			exit 0;;
		*)
			echo "[ERROR]: Failed to parse argument -> ${1}!" >&2
			_usage_help
			exit 1;;
	esac
done
## --- Menu arguments --- ##


## --- Main --- ##
main()
{
	if [ -z "${_MODULE_NAME:-}" ]; then
		_MODULE_NAME="${MODULE_NAME}"
	else
		MODULE_DIR="./src/${_MODULE_NAME}"
	fi

	if [ -z "${_MODULE_DIR:-}" ]; then
		_MODULE_DIR="${MODULE_DIR}"
	fi

	if [ -z "${_OUTPUT_DIR:-}" ]; then
		_OUTPUT_DIR="${OUTPUT_DIR}"
	fi

	local _classes_dir="${_OUTPUT_DIR}/classes"
	local _packages_dir="${_OUTPUT_DIR}/packages"

	if [ ! -d "${_classes_dir}" ]; then
		mkdir -vp "${_classes_dir}"
	fi

	if [ ! -d "${_packages_dir}" ]; then
		mkdir -vp "${_packages_dir}"
	fi


	echo "[INFO]: Generating UML diagrams..."
	local _cp_formats=("html" "pdf" "png" "svg")
	local _cp_format
	for _cp_format in "${_cp_formats[@]}"; do
		local _tmp_class_path="${_OUTPUT_DIR}/classes_${_MODULE_NAME}.${_cp_format}"
		local _tmp_package_path="${_OUTPUT_DIR}/packages_${_MODULE_NAME}.${_cp_format}"

		echo "[INFO]: Generating ['${_tmp_class_path}', '${_tmp_package_path}'] files..."
		pyreverse -d "${_OUTPUT_DIR}" -o "${_cp_format}" -p "${_MODULE_NAME}" "${_MODULE_DIR}" || exit 2
		mv -vf "${_tmp_class_path}" "${_classes_dir}/" || exit 2
		mv -vf "${_tmp_package_path}" "${_packages_dir}/" || exit 2
		echo "[OK]: Done."
	done
	echo "[OK]: Done."
}

main
## --- Main --- ##
