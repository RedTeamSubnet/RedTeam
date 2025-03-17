FROM selenium/standalone-chrome:131.0

# Install python3 and pip
RUN sudo apt-get update && sudo apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
	net-tools \
	curl \
	iputils-ping \
    && sudo apt-get clean \
    && sudo rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install python dependencies
COPY requirements.txt .
RUN python3 -m venv venv && \
    . venv/bin/activate && \
    python3 -m pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY ./src .

EXPOSE 10002

CMD ["/bin/bash", "-c", "source venv/bin/activate && uvicorn app:app --host 0.0.0.0 --port 10002"]
