# syntax=docker/dockerfile:1

FROM python:3.10.16-slim-bullseye

ARG DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Install python dependencies
COPY requirements.txt .
RUN python3 -m pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY ./src .

EXPOSE 10002

CMD ["/bin/bash", "-c", "uvicorn app:app --host 0.0.0.0 --port 10002"]
