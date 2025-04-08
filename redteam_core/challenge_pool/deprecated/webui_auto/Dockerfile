# syntax=docker/dockerfile:1

ARG BASE_IMAGE=ubuntu:22.04

ARG DEBIAN_FRONTEND=noninteractive
ARG WUC_API_SLUG="rest.rt-wu-challenger"


## Here is the builder image:
FROM ${BASE_IMAGE} AS builder

ARG DEBIAN_FRONTEND
ARG WUC_API_SLUG

# ARG USE_GPU=false
ARG PYTHON_VERSION=3.10

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

WORKDIR "/usr/src/${WUC_API_SLUG}"

RUN _BUILD_TARGET_ARCH=$(uname -m) && \
    echo "BUILDING TARGET ARCHITECTURE: $_BUILD_TARGET_ARCH" && \
	rm -rfv /var/lib/apt/lists/* /var/cache/apt/archives/* /tmp/* && \
	apt-get clean -y && \
	apt-get update --fix-missing -o Acquire::CompressionTypes::Order::=gz && \
	apt-get install -y --no-install-recommends \
		ca-certificates \
		build-essential \
		git \
		wget && \
	if [ "${_BUILD_TARGET_ARCH}" == "x86_64" ]; then \
		export _MINICONDA_FILENAME=Miniconda3-py310_24.9.2-0-Linux-x86_64.sh; \
		export _MINICONDA_URL=https://repo.anaconda.com/miniconda/${_MINICONDA_FILENAME}; \
	elif [ "${_BUILD_TARGET_ARCH}" == "aarch64" ]; then \
		export _MINICONDA_FILENAME=Miniconda3-py310_24.9.2-0-Linux-aarch64.sh; \
		export _MINICONDA_URL=https://repo.anaconda.com/miniconda/${_MINICONDA_FILENAME}; \
		# export _MINICONDA_FILENAME=Miniforge3-24.9.2-0-Linux-aarch64.sh; \
		# export _MINICONDA_URL=https://github.com/conda-forge/miniforge/releases/download/24.9.2-0/${_MINICONDA_FILENAME}; \
	else \
		echo "Unsupported platform: ${_BUILD_TARGET_ARCH}" && \
		exit 1; \
	fi && \
	if [ ! -f "/root/${_MINICONDA_FILENAME}" ]; then \
		wget -nv --show-progress --progress=bar:force:noscroll "${_MINICONDA_URL}" -O "/root/${_MINICONDA_FILENAME}"; \
	fi && \
	/bin/bash "/root/${_MINICONDA_FILENAME}" -b -u -p /opt/conda && \
	/opt/conda/condabin/conda update -y conda && \
	/opt/conda/condabin/conda install -y python=${PYTHON_VERSION} pip && \
	/opt/conda/bin/pip install --timeout 60 -U pip

# COPY ./requirements* ./
COPY requirements.txt ./requirements.txt
RUN /opt/conda/bin/pip install --timeout 60 -r ./requirements.txt
# RUN	--mount=type=cache,target=/root/.cache,sharing=locked \
# 	--mount=type=bind,source=requirements.txt,target=requirements.txt \
# 	# _BUILD_TARGET_ARCH=$(uname -m) && \
# 	# if [ "${_BUILD_TARGET_ARCH}" == "x86_64" ] && [ "${USE_GPU}" == "false" ]; then \
# 	# 	export _REQUIRE_FILE_PATH=./requirements/requirements.amd64.txt; \
# 	# elif [ "${_BUILD_TARGET_ARCH}" == "x86_64" ] && [ "${USE_GPU}" == "true" ]; then \
# 	# 	export _REQUIRE_FILE_PATH=./requirements/requirements.gpu.txt; \
# 	# elif [ "${_BUILD_TARGET_ARCH}" == "aarch64" ]; then \
# 	# 	export _REQUIRE_FILE_PATH=./requirements/requirements.arm64.txt; \
# 	# fi && \
# 	# /opt/conda/bin/pip install --timeout 60 -r "${_REQUIRE_FILE_PATH}" && \
# 	/opt/conda/bin/pip install --timeout 60 -r ./requirements.txt


## Here is the base image:
FROM ${BASE_IMAGE} AS base

ARG DEBIAN_FRONTEND
ARG WUC_API_SLUG

ARG WUC_HOME_DIR="/app"
ARG WUC_API_DIR="${WUC_HOME_DIR}/${WUC_API_SLUG}"
ARG WUC_API_DATA_DIR="/var/lib/${WUC_API_SLUG}"
ARG WUC_API_LOGS_DIR="/var/log/${WUC_API_SLUG}"
ARG WUC_API_TMP_DIR="/tmp/${WUC_API_SLUG}"
ARG WUC_API_PORT=10001
## IMPORTANT!: Get hashed password from build-arg!
## echo "WUC_USER_PASSWORD123" | openssl passwd -5 -stdin
ARG HASH_PASSWORD="\$5\$7rxSgAlU1ynFUQJF\$Kdi1D2IrsBWDTwn1GKpItnLWAMgGsyaBJw2qXcUCAC/"
ARG UID=1000
ARG GID=11000
ARG USER=wuc-user
ARG GROUP=wuc-group

ENV WUC_HOME_DIR="${WUC_HOME_DIR}" \
	WUC_API_DIR="${WUC_API_DIR}" \
	WUC_API_DATA_DIR="${WUC_API_DATA_DIR}" \
	WUC_API_LOGS_DIR="${WUC_API_LOGS_DIR}" \
	WUC_API_TMP_DIR="${WUC_API_TMP_DIR}" \
	WUC_API_PORT=${WUC_API_PORT} \
	UID=${UID} \
	GID=${GID} \
	USER=${USER} \
	GROUP=${GROUP} \
	PYTHONIOENCODING=utf-8 \
	PYTHONUNBUFFERED=1 \
	PATH="/opt/conda/bin:${PATH}"

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

RUN rm -rfv /var/lib/apt/lists/* /var/cache/apt/archives/* /tmp/* /root/.cache/* && \
	apt-get clean -y && \
	apt-get update --fix-missing -o Acquire::CompressionTypes::Order::=gz && \
	apt-get install -y --no-install-recommends \
		sudo \
		locales \
		tzdata \
		procps \
		iputils-ping \
		net-tools \
		curl \
		nano && \
	apt-get clean -y && \
	sed -i -e 's/# en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen && \
	sed -i -e 's/# en_AU.UTF-8 UTF-8/en_AU.UTF-8 UTF-8/' /etc/locale.gen && \
	dpkg-reconfigure --frontend=noninteractive locales && \
	update-locale LANG=en_US.UTF-8 && \
	echo "LANGUAGE=en_US.UTF-8" >> /etc/default/locale && \
	echo "LC_ALL=en_US.UTF-8" >> /etc/default/locale && \
	addgroup --gid ${GID} ${GROUP} && \
	useradd -lmN -d "/home/${USER}" -s /bin/bash -g ${GROUP} -G sudo -u ${UID} ${USER} && \
	echo "${USER} ALL=(ALL) NOPASSWD: ALL" > "/etc/sudoers.d/${USER}" && \
	chmod 0440 "/etc/sudoers.d/${USER}" && \
	echo -e "${USER}:${HASH_PASSWORD}" | chpasswd -e && \
	echo -e "\nalias ls='ls -aF --group-directories-first --color=auto'" >> /root/.bashrc && \
	echo -e "alias ll='ls -alhF --group-directories-first --color=auto'\n" >> /root/.bashrc && \
	echo -e "\numask 0002" >> "/home/${USER}/.bashrc" && \
	echo "alias ls='ls -aF --group-directories-first --color=auto'" >> "/home/${USER}/.bashrc" && \
	echo -e "alias ll='ls -alhF --group-directories-first --color=auto'\n" >> "/home/${USER}/.bashrc" && \
	echo ". /opt/conda/etc/profile.d/conda.sh" >> "/home/${USER}/.bashrc" && \
	echo "conda activate base" >> "/home/${USER}/.bashrc" && \
	rm -rfv /var/lib/apt/lists/* /var/cache/apt/archives/* /tmp/* /root/.cache/* "/home/${USER}/.cache/*" && \
	mkdir -pv "${WUC_API_DIR}" "${WUC_API_DATA_DIR}" "${WUC_API_LOGS_DIR}" "${WUC_API_TMP_DIR}" && \
	chown -Rc "${USER}:${GROUP}" "${WUC_HOME_DIR}" "${WUC_API_DATA_DIR}" "${WUC_API_LOGS_DIR}" "${WUC_API_TMP_DIR}" && \
	find "${WUC_API_DIR}" "${WUC_API_DATA_DIR}" -type d -exec chmod -c 770 {} + && \
	find "${WUC_API_DIR}" "${WUC_API_DATA_DIR}" -type d -exec chmod -c ug+s {} + && \
	find "${WUC_API_LOGS_DIR}" "${WUC_API_TMP_DIR}" -type d -exec chmod -c 775 {} + && \
	find "${WUC_API_LOGS_DIR}" "${WUC_API_TMP_DIR}" -type d -exec chmod -c +s {} +

ENV LANG=en_US.UTF-8 \
	LANGUAGE=en_US.UTF-8 \
	LC_ALL=en_US.UTF-8

COPY --from=builder --chown=${UID}:${GID} /opt/conda /opt/conda


## Here is the final image:
FROM base AS app

WORKDIR "${WUC_API_DIR}"
COPY --chown=${UID}:${GID} ./src ${WUC_API_DIR}
COPY --chown=${UID}:${GID} ./scripts/docker/*.sh /usr/local/bin/

# VOLUME ["${WUC_API_DATA_DIR}"]
EXPOSE ${WUC_API_PORT}

USER ${UID}:${GID}
# HEALTHCHECK --start-period=30s --start-interval=1s --interval=5m --timeout=5s --retries=3 \
# 	CMD curl -f http://localhost:${WUC_API_PORT}/health || exit 1

ENTRYPOINT ["docker-entrypoint.sh"]
# CMD ["-b", "uvicorn main:app --host=0.0.0.0 --port=${WUC_API_PORT:-10001} --no-access-log --no-server-header --proxy-headers --forwarded-allow-ips='*'"]
