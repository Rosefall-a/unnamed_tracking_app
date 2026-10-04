# Local rebuild of ghcr.io/pelican-eggs/installers:debian (Ubuntu base: deb.debian.org is blocked here)
FROM ubuntu:24.04
RUN apt-get update -y && apt-get install -y ca-certificates curl git unzip zip tar jq wget file xz-utils && rm -rf /var/lib/apt/lists/*
