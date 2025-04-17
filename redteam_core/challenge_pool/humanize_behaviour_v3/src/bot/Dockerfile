# syntax=docker/dockerfile:1

FROM redteamsn61/hbc-bot-base:latest

ARG DEBIAN_FRONTEND=noninteractive
ARG APT_PACKAGES=""

# Install python3 and pip
RUN if [ -n "${APT_PACKAGES:-}" ]; then \
		sudo apt-get update && \
		sudo apt-get install -y --no-install-recommends \
			${APT_PACKAGES}; \
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
