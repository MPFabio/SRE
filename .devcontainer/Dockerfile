FROM mcr.microsoft.com/devcontainers/python:3.11-bookworm

RUN apt-get update && apt-get install --yes --no-install-recommends \
        make \
        jq \
        curl \
        postgresql-client \
        redis-tools \
    && rm --recursive --force /var/lib/apt/lists/*
