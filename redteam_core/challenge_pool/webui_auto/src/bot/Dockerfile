# syntax=docker/dockerfile:1

FROM selenium/standalone-chrome:4.28.1

ARG DEBIAN_FRONTEND=noninteractive
ARG APT_PACKAGES=""

# Install python3 and pip
RUN sudo apt-get update && \
	sudo apt-get install -y --no-install-recommends \
		python3 \
		python3-pip \
		python3-venv \
		${APT_PACKAGES} \
		iproute2 && \
	sudo apt-get clean -y && \
	sudo rm -rfv /var/lib/apt/lists/* /var/cache/apt/archives/* /tmp/* /root/.cache/*

WORKDIR /app

# Install python dependencies
COPY requirements.txt .
RUN python3 -m venv venv && \
	. venv/bin/activate && \
	python3 -m pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY ./src .

CMD ["/bin/bash", "-c", "source venv/bin/activate && python3 -u ./main.py && /bin/bash"]
