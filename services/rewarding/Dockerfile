# syntax=docker/dockerfile:1
# check=skip=SecretsUsedInArgOrEnv,UndefinedVar

ARG PYTHON_VERSION=3.10
ARG BASE_IMAGE=python:${PYTHON_VERSION}-slim-bookworm

ARG DEBIAN_FRONTEND=noninteractive
ARG RT_REWARD_APP_SLUG="server.reward-app"


## Here is the builder image:
FROM ${BASE_IMAGE} AS builder

ARG DEBIAN_FRONTEND
ARG RT_REWARD_APP_SLUG

ENV CARGO_HOME=/usr/local/rust/cargo \
	RUSTUP_HOME=/usr/local/rust/rustup
ENV PATH="${CARGO_HOME}/bin:${PATH}"

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

WORKDIR "/usr/src/${RT_REWARD_APP_SLUG}"

RUN --mount=type=cache,target=/root/.cache,sharing=locked \
	_BUILD_TARGET_ARCH=$(uname -m) && \
	echo "BUILDING TARGET ARCHITECTURE: ${_BUILD_TARGET_ARCH}" && \
	rm -rfv /var/lib/apt/lists/* /var/cache/apt/archives/* /tmp/* && \
	apt-get clean -y && \
	# echo "Acquire::http::Pipeline-Depth 0;" >> /etc/apt/apt.conf.d/99fixbadproxy && \
	# echo "Acquire::http::No-Cache true;" >> /etc/apt/apt.conf.d/99fixbadproxy && \
	# echo "Acquire::BrokenProxy true;" >> /etc/apt/apt.conf.d/99fixbadproxy && \
	apt-get update --fix-missing -o Acquire::CompressionTypes::Order::=gz && \
	apt-get install -y --no-install-recommends \
		curl \
		pkg-config \
		libssl-dev \
		build-essential && \
	curl https://sh.rustup.rs -sSf | sh -s -- -y  && \
	python3 -m pip install --timeout 60 -U pip uv

# COPY ./requirements* ./
RUN	--mount=type=cache,target=/root/.cache,sharing=locked \
	--mount=type=bind,source=./requirements.txt,target=requirements.txt \
	--mount=type=bind,source=./services/rewarding/requirements.txt,target=./requirements.extra.txt \
	python3 -m uv pip install --prefix=/install -r ./requirements.txt && \
	python3 -m uv pip install --prefix=/install -r ./requirements.extra.txt


## Here is the base image:
FROM ${BASE_IMAGE} AS base

ARG DEBIAN_FRONTEND
ARG RT_REWARD_APP_SLUG

ARG RT_HOME_DIR="/app"
ARG RT_REWARD_APP_DIR="${RT_HOME_DIR}/${RT_REWARD_APP_SLUG}"
ARG RT_REWARD_APP_DATA_DIR="/var/lib/${RT_REWARD_APP_SLUG}"
ARG RT_REWARD_APP_LOGS_DIR="/var/log/${RT_REWARD_APP_SLUG}"
ARG RT_REWARD_APP_TMP_DIR="/tmp/${RT_REWARD_APP_SLUG}"
## IMPORTANT!: Get hashed password from build-arg!
## echo "RT_REWARD_APP_PASSWORD123" | openssl passwd -5 -stdin
ARG HASH_PASSWORD="\$5\$92XQZEJ59Vs3llsd\$hca8huh.9PoEkMoWFYqGnxAK2maRdavuuDZktskVFc9"
ARG UID=1000
ARG GID=11000
ARG USER=rt-user
ARG GROUP=rt-group

ENV RT_REWARD_APP_SLUG="${RT_REWARD_APP_SLUG}" \
	RT_HOME_DIR="${RT_HOME_DIR}" \
	RT_REWARD_APP_DIR="${RT_REWARD_APP_DIR}" \
	RT_REWARD_APP_DATA_DIR="${RT_REWARD_APP_DATA_DIR}" \
	RT_REWARD_APP_LOGS_DIR="${RT_REWARD_APP_LOGS_DIR}" \
	RT_REWARD_APP_TMP_DIR="${RT_REWARD_APP_TMP_DIR}" \
	UID=${UID} \
	GID=${GID} \
	USER=${USER} \
	GROUP=${GROUP} \
	PYTHONIOENCODING=utf-8 \
	PYTHONUNBUFFERED=1 \
	PYTHONPATH="${RT_REWARD_APP_DIR}:${PYTHONPATH}"

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

RUN rm -rfv /var/lib/apt/lists/* /var/cache/apt/archives/* /tmp/* /root/.cache/* && \
	apt-get clean -y && \
	# echo "Acquire::http::Pipeline-Depth 0;" >> /etc/apt/apt.conf.d/99fixbadproxy && \
	# echo "Acquire::http::No-Cache true;" >> /etc/apt/apt.conf.d/99fixbadproxy && \
	# echo "Acquire::BrokenProxy true;" >> /etc/apt/apt.conf.d/99fixbadproxy && \
	apt-get update --fix-missing -o Acquire::CompressionTypes::Order::=gz && \
	apt-get install -y --no-install-recommends \
		sudo \
		locales \
		tzdata \
		procps \
		iputils-ping \
		iproute2 \
		curl \
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
	usermod -aG docker ${USER} && \
	echo "${USER} ALL=(ALL) NOPASSWD: ALL" > "/etc/sudoers.d/${USER}" && \
	chmod 0440 "/etc/sudoers.d/${USER}" && \
	echo -e "${USER}:${HASH_PASSWORD}" | chpasswd -e && \
	echo -e "\nalias ls='ls -aF --group-directories-first --color=auto'" >> /root/.bashrc && \
	echo -e "alias ll='ls -alhF --group-directories-first --color=auto'\n" >> /root/.bashrc && \
	echo -e "\numask 0002" >> "/home/${USER}/.bashrc" && \
	echo "alias ls='ls -aF --group-directories-first --color=auto'" >> "/home/${USER}/.bashrc" && \
	echo -e "alias ll='ls -alhF --group-directories-first --color=auto'\n" >> "/home/${USER}/.bashrc" && \
	rm -rfv /var/lib/apt/lists/* /var/cache/apt/archives/* /tmp/* /root/.cache/* "/home/${USER}/.cache/*" && \
	mkdir -pv "${RT_REWARD_APP_DIR}" "${RT_REWARD_APP_DATA_DIR}" "${RT_REWARD_APP_LOGS_DIR}" "${RT_REWARD_APP_TMP_DIR}" && \
	chown -Rc "${USER}:${GROUP}" "${RT_HOME_DIR}" "${RT_REWARD_APP_DATA_DIR}" "${RT_REWARD_APP_LOGS_DIR}" "${RT_REWARD_APP_TMP_DIR}" && \
	find "${RT_REWARD_APP_DIR}" "${RT_REWARD_APP_DATA_DIR}" -type d -exec chmod -c 770 {} + && \
	find "${RT_REWARD_APP_DIR}" "${RT_REWARD_APP_DATA_DIR}" -type d -exec chmod -c ug+s {} + && \
	find "${RT_REWARD_APP_LOGS_DIR}" "${RT_REWARD_APP_TMP_DIR}" -type d -exec chmod -c 775 {} + && \
	find "${RT_REWARD_APP_LOGS_DIR}" "${RT_REWARD_APP_TMP_DIR}" -type d -exec chmod -c +s {} +

ENV LANG=en_US.UTF-8 \
	LANGUAGE=en_US.UTF-8 \
	LC_ALL=en_US.UTF-8

COPY --from=builder /install /usr/local


## Here is the final image:
FROM base AS app

WORKDIR "${RT_REWARD_APP_DIR}"
COPY --chown=${UID}:${GID} ./redteam_core ${RT_REWARD_APP_DIR}/redteam_core
COPY --chown=${UID}:${GID} ./neurons/validator ${RT_REWARD_APP_DIR}/neurons/validator
COPY --chown=${UID}:${GID} ./services/rewarding ${RT_REWARD_APP_DIR}/services/rewarding
COPY --chown=${UID}:${GID} --chmod=770 ./services/rewarding/scripts/docker/*.sh /usr/local/bin/

# VOLUME ["${RT_REWARD_APP_DATA_DIR}"]

USER ${UID}:${GID}

ENTRYPOINT ["docker-entrypoint.sh"]
