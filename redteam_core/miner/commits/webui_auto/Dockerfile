ARG BASE_IMAGE=ubuntu:22.04
ARG UBUNTU_FRONTEND=noninteractive

ARG WUM_API_SLUG="webui-auto-miner"

ARG PYTHON_VERSION=3.10

FROM ${BASE_IMAGE} AS builder

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

LABEL maintainer="Bot Runtime Maintainer"
LABEL description="Bot Runtime Environment for Script Execution"

WORKDIR "/usr/src/${WUM_API_SLUG}"

# Install dependencies and Miniconda
RUN _BUILD_TARGET_ARCH=$(uname -m) && \
    echo "BUILDING TARGET ARCHITECTURE: ${_BUILD_TARGET_ARCH}" && \
    rm -rfv /var/lib/apt/lists/* /var/cache/apt/archives/* /tmp/* /root/.cache/* && \
    apt-get clean -y && \
    apt-get update --fix-missing -o Acquire::CompressionTypes::Order::=gz && \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        build-essential \
        wget && \
    if [ "${_BUILD_TARGET_ARCH}" == "x86_64" ]; then \
        export _MINICONDA_URL=https://repo.anaconda.com/miniconda/Miniconda3-py310_24.9.2-0-Linux-x86_64.sh; \
    elif [ "${_BUILD_TARGET_ARCH}" == "aarch64" ]; then \
        export _MINICONDA_URL=https://repo.anaconda.com/miniconda/Miniconda3-py310_24.9.2-0-Linux-aarch64.sh; \
    else \
        echo "Unsupported platform: ${_BUILD_TARGET_ARCH}" && \
        exit 1; \
    fi && \
    wget -nv --show-progress --progress=bar:force:noscroll "${_MINICONDA_URL}" -O /root/miniconda.sh && \
    /bin/bash /root/miniconda.sh -b -u -p /opt/conda && \
    /opt/conda/condabin/conda clean -y -av && \
    /opt/conda/condabin/conda update -y conda && \
    /opt/conda/condabin/conda install -y python=${PYTHON_VERSION} pip && \
    /opt/conda/bin/pip install --timeout 60 --no-cache-dir -U pip && \
    /opt/conda/bin/pip cache purge && \
    /opt/conda/condabin/conda clean -y -av

# COPY ./requirements* ./
RUN	--mount=type=cache,target=/root/.cache,sharing=locked \
	--mount=type=bind,source=requirements.txt,target=requirements.txt \
	# _BUILD_TARGET_ARCH=$(uname -m) && \
	# if [ "${_BUILD_TARGET_ARCH}" == "x86_64" ] && [ "${USE_GPU}" == "false" ]; then \
	# 	export _REQUIRE_FILE_PATH=./requirements/requirements.amd64.txt; \
	# elif [ "${_BUILD_TARGET_ARCH}" == "x86_64" ] && [ "${USE_GPU}" == "true" ]; then \
	# 	export _REQUIRE_FILE_PATH=./requirements/requirements.gpu.txt; \
	# elif [ "${_BUILD_TARGET_ARCH}" == "aarch64" ]; then \
	# 	export _REQUIRE_FILE_PATH=./requirements/requirements.arm64.txt; \
	# fi && \
	# /opt/conda/bin/pip install --timeout 60 -r "${_REQUIRE_FILE_PATH}" && \
	/opt/conda/bin/pip install --timeout 60 -r ./requirements.txt

FROM ${BASE_IMAGE} AS base

ARG DEBIAN_FRONTEND
ARG WUM_API_SLUG

ARG WUM_HOME_DIR="/app"
ARG WUM_API_DIR="${WUM_HOME_DIR}/${WUM_API_SLUG}"
ARG WUM_API_DATA_DIR="/var/lib/${WUM_API_SLUG}"
ARG WUM_API_LOGS_DIR="/var/log/${WUM_API_SLUG}"
ARG WUM_API_TMP_DIR="/tmp/${WUM_API_SLUG}"
ARG WUM_API_PORT=10001
## IMPORTANT!: Get hashed password from build-arg!
## echo "WUM_USER_PASSWORD123" | openssl passwd -5 -stdin
ARG HASH_PASSWORD="\$5\$7rxSgAlU1ynFUQJF\$Kdi1D2IrsBWDTwn1GKpItnLWAMgGsyaBJw2qXcUCAC/"
ARG UID=1000
ARG GID=11000
ARG USER=wuc-user
ARG GROUP=wuc-group

ENV WUM_HOME_DIR="${WUM_HOME_DIR}" \
	WUM_API_DIR="${WUM_API_DIR}" \
	WUM_API_DATA_DIR="${WUM_API_DATA_DIR}" \
	WUM_API_LOGS_DIR="${WUM_API_LOGS_DIR}" \
	WUM_API_TMP_DIR="${WUM_API_TMP_DIR}" \
	WUM_API_PORT=${WUM_API_PORT} \
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
    # First, configure architecture and repositories
    dpkg --add-architecture amd64 && \
    apt-get update --fix-missing -o Acquire::CompressionTypes::Order::=gz && \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        wget \
        gnupg \
        apt-transport-https && \
    # Add Chrome repository properly
    wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - && \
    echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list && \
    # Update package lists with new repository
    apt-get update && \
    # Install Chrome and other required packages
    apt-get install -y --no-install-recommends \
        google-chrome-stable \
        sudo \
        locales \
        tzdata \
        procps \
        iputils-ping \
        net-tools \
        curl \
        nano && \
    # Clean up
    apt-get clean -y && \
    rm -rf /var/lib/apt/lists/* && \
    # Continue with locale configuration
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
	mkdir -pv "${WUM_API_DIR}" "${WUM_API_DATA_DIR}" "${WUM_API_LOGS_DIR}" "${WUM_API_TMP_DIR}" && \
	chown -Rc "${USER}:${GROUP}" "${WUM_HOME_DIR}" "${WUM_API_DATA_DIR}" "${WUM_API_LOGS_DIR}" "${WUM_API_TMP_DIR}" && \
	find "${WUM_API_DIR}" "${WUM_API_DATA_DIR}" -type d -exec chmod -c 770 {} + && \
	find "${WUM_API_DIR}" "${WUM_API_DATA_DIR}" -type d -exec chmod -c ug+s {} + && \
	find "${WUM_API_LOGS_DIR}" "${WUM_API_TMP_DIR}" -type d -exec chmod -c 775 {} + && \
	find "${WUM_API_LOGS_DIR}" "${WUM_API_TMP_DIR}" -type d -exec chmod -c +s {} +

ENV LANG=en_US.UTF-8 \
	LANGUAGE=en_US.UTF-8 \
	LC_ALL=en_US.UTF-8

COPY --from=builder --chown=${UID}:${GID} /opt/conda /opt/conda

## Here is the final image:
FROM base AS app

WORKDIR "${WUM_API_DIR}"
COPY --chown=${UID}:${GID} . ${WUM_API_DIR}
COPY --chown=${UID}:${GID} --chmod=770 ./*.sh /usr/local/bin/

# VOLUME ["${WUM_API_DATA_DIR}"]
# EXPOSE ${WUM_API_PORT}

USER ${UID}:${GID}
# HEALTHCHECK --start-period=30s --start-interval=1s --interval=5m --timeout=5s --retries=3 \
# 	CMD curl -f http://localhost:${WUM_API_PORT}/health || exit 1

ENTRYPOINT ["docker-entrypoint.sh"]

# CMD ["-b", "uvicorn app:app --host=0.0.0.0 --port=${WUM_API_PORT:-10001} --no-access-log --no-server-header --proxy-headers --forwarded-allow-ips='*'"]