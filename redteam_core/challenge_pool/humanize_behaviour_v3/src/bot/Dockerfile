# syntax=docker/dockerfile:1

FROM redteamsubnet61/hbc-bot-base:latest

ARG DEBIAN_FRONTEND=noninteractive
ARG APT_PACKAGES=""

# Install python3 and pip
RUN _BUILD_TARGET_ARCH=$(uname -m) && \
	echo "BUILDING TARGET ARCHITECTURE: $_BUILD_TARGET_ARCH" && \
	if [ -n "${APT_PACKAGES:-}" ]; then \
		sudo rm -rfv /var/lib/apt/lists/* /var/cache/apt/archives/* /tmp/* && \
		sudo apt-get clean -y && \
		sudo apt-get update --fix-missing -o Acquire::CompressionTypes::Order::=gz && \
		sudo apt-get install -y --no-install-recommends \
			${APT_PACKAGES} && \
		sudo rm -rfv /var/lib/apt/lists/* /var/cache/apt/archives/* /tmp/*; \
	fi

# Install python dependencies
COPY requirements.txt .
RUN sudo chown -R seluser:seluser /app && \
	python3 -m venv venv && \
	. venv/bin/activate && \
	python3 -m pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY --chown=seluser:seluser ./src .
# RUN sudo chown -R seluser:seluser /app

CMD ["/bin/bash", "-c", "source venv/bin/activate && python3 -u ./main.py"]
