# syntax=docker/dockerfile:1
# check=skip=SecretsUsedInArgOrEnv

ARG BASE_IMAGE=ubuntu:22.04

ARG DEBIAN_FRONTEND=noninteractive
ARG HBC_API_SLUG="rest.rt-hb-challenger"


## Here is the builder image:
FROM ${BASE_IMAGE} AS builder

ARG DEBIAN_FRONTEND
ARG HBC_API_SLUG

# ARG USE_GPU=false
ARG PYTHON_VERSION=3.10

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

WORKDIR "/usr/src/${HBC_API_SLUG}"

RUN _BUILD_TARGET_ARCH=$(uname -m) && \
	echo "BUILDING TARGET ARCHITECTURE: $_BUILD_TARGET_ARCH" && \
	rm -rfv /var/lib/apt/lists/* /var/cache/apt/archives/* /tmp/* && \
	apt-get clean -y && \
	apt-get update --fix-missing -o Acquire::CompressionTypes::Order::=gz && \
	apt-get install -y --no-install-recommends \
		ca-certificates \
		build-essential \
		git \
		graphviz \
		graphviz-dev \
		wget && \
	_MINICONDA_VERSION=py310_25.1.1-2 && \
	if [ "${_BUILD_TARGET_ARCH}" == "x86_64" ]; then \
		_MINICONDA_FILENAME=Miniconda3-${_MINICONDA_VERSION}-Linux-x86_64.sh && \
		export _MINICONDA_URL=https://repo.anaconda.com/miniconda/${_MINICONDA_FILENAME}; \
	elif [ "${_BUILD_TARGET_ARCH}" == "aarch64" ]; then \
		_MINICONDA_FILENAME=Miniconda3-${_MINICONDA_VERSION}-Linux-aarch64.sh && \
		export _MINICONDA_URL=https://repo.anaconda.com/miniconda/${_MINICONDA_FILENAME}; \
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
	# /opt/conda/condabin/conda install -y python=${PYTHON_VERSION} graphviz pip && \
	# /opt/conda/condabin/conda install -y --channel conda-forge pygraphviz && \
	/opt/conda/bin/pip install --timeout 60 -U pip

COPY requirements ./requirements
COPY requirements.txt ./requirements.txt
RUN /opt/conda/bin/pip install --timeout 60 -r ./requirements.txt


## Here is the base image:
FROM ${BASE_IMAGE} AS base

ARG DEBIAN_FRONTEND
ARG HBC_API_SLUG

ARG HBC_HOME_DIR="/app"
ARG HBC_API_DIR="${HBC_HOME_DIR}/${HBC_API_SLUG}"
ARG HBC_API_DATA_DIR="/var/lib/${HBC_API_SLUG}"
ARG HBC_API_LOGS_DIR="/var/log/${HBC_API_SLUG}"
ARG HBC_API_TMP_DIR="/tmp/${HBC_API_SLUG}"
ARG HBC_API_PORT=10001
## IMPORTANT!: Get hashed password from build-arg!
## echo "HBC_USER_PASSWORD123" | openssl passwd -5 -stdin
ARG HASH_PASSWORD="\$5\$7rxSgAlU1ynFUQJF\$Kdi1D2IrsBWDTwn1GKpItnLWAMgGsyaBJw2qXcUCAC/"
ARG UID=1000
ARG GID=11000
ARG USER=hbc-user
ARG GROUP=hbc-group

ENV HBC_HOME_DIR="${HBC_HOME_DIR}" \
	HBC_API_DIR="${HBC_API_DIR}" \
	HBC_API_DATA_DIR="${HBC_API_DATA_DIR}" \
	HBC_API_LOGS_DIR="${HBC_API_LOGS_DIR}" \
	HBC_API_TMP_DIR="${HBC_API_TMP_DIR}" \
	HBC_API_PORT=${HBC_API_PORT} \
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
		ca-certificates \
		locales \
		tzdata \
		procps \
		iputils-ping \
		net-tools \
		curl \
		iproute2 \
		graphviz \
		graphviz-dev \
		# skopeo \
		nano && \
	curl -fsSL https://get.docker.com/ | sh && \
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
	usermod -aG docker ${USER} && \
	echo -e "${USER}:${HASH_PASSWORD}" | chpasswd -e && \
	echo -e "\nalias ls='ls -aF --group-directories-first --color=auto'" >> /root/.bashrc && \
	echo -e "alias ll='ls -alhF --group-directories-first --color=auto'\n" >> /root/.bashrc && \
	echo -e "\numask 0002" >> "/home/${USER}/.bashrc" && \
	echo "alias ls='ls -aF --group-directories-first --color=auto'" >> "/home/${USER}/.bashrc" && \
	echo -e "alias ll='ls -alhF --group-directories-first --color=auto'\n" >> "/home/${USER}/.bashrc" && \
	echo ". /opt/conda/etc/profile.d/conda.sh" >> "/home/${USER}/.bashrc" && \
	echo "conda activate base" >> "/home/${USER}/.bashrc" && \
	rm -rfv /var/lib/apt/lists/* /var/cache/apt/archives/* /tmp/* /root/.cache/* "/home/${USER}/.cache/*" && \
	mkdir -pv "${HBC_API_DIR}" "${HBC_API_DATA_DIR}" "${HBC_API_LOGS_DIR}" "${HBC_API_TMP_DIR}" && \
	# skopeo copy docker://redteamsn61/hbc-bot-base:latest docker-archive:/app/redteamsn61_hbc-bot-base.tar &&\
	chown -Rc "${USER}:${GROUP}" "${HBC_HOME_DIR}" "${HBC_API_DATA_DIR}" "${HBC_API_LOGS_DIR}" "${HBC_API_TMP_DIR}" && \
	find "${HBC_API_DIR}" "${HBC_API_DATA_DIR}" -type d -exec chmod -c 770 {} + && \
	find "${HBC_API_DIR}" "${HBC_API_DATA_DIR}" -type d -exec chmod -c ug+s {} + && \
	find "${HBC_API_LOGS_DIR}" "${HBC_API_TMP_DIR}" -type d -exec chmod -c 775 {} + && \
	find "${HBC_API_LOGS_DIR}" "${HBC_API_TMP_DIR}" -type d -exec chmod -c +s {} +


ENV LANG=en_US.UTF-8 \
	LANGUAGE=en_US.UTF-8 \
	LC_ALL=en_US.UTF-8

COPY --from=builder --chown=${UID}:${GID} /opt/conda /opt/conda


## Here is the final image:
FROM base AS app

WORKDIR "${HBC_API_DIR}"
COPY --chown=${UID}:${GID} ./src ${HBC_API_DIR}
COPY --chown=${UID}:${GID} ./scripts/docker/*.sh /usr/local/bin/

# VOLUME ["${HBC_API_DATA_DIR}"]
EXPOSE ${HBC_API_PORT}

USER ${UID}:${GID}
# HEALTHCHECK --start-period=30s --start-interval=1s --interval=5m --timeout=5s --retries=3 \
# 	CMD curl -f http://localhost:${HBC_API_PORT}/health || exit 1

ENTRYPOINT ["docker-entrypoint.sh"]
# CMD ["-b", "uvicorn main:app --host=0.0.0.0 --port=${HBC_API_PORT:-10001} --no-access-log --no-server-header --proxy-headers --forwarded-allow-ips='*'"]
