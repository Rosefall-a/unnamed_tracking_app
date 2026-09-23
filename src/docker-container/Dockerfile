# syntax=docker/dockerfile:1.7

FROM node:22-slim AS frontend-build
WORKDIR /frontend
COPY src/frontend/package.json src/frontend/package-lock.json ./
RUN npm ci
COPY src/frontend/ ./
RUN npm run build

FROM python:3.12-slim AS runtime
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PATH="/opt/java/bin:${PATH}"
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx curl gcc postgresql-client unzip ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fL -o /tmp/jre.tar.gz \
    https://github.com/adoptium/temurin25-binaries/releases/download/jdk-25.0.4.1%2B1/OpenJDK25U-jre_x64_linux_hotspot_25.0.4.1_1.tar.gz \
    && mkdir -p /opt/java \
    && tar -xzf /tmp/jre.tar.gz -C /opt/java --strip-components=1 \
    && rm /tmp/jre.tar.gz

RUN curl -fL -o /opt/bluemap-cli.jar \
    https://github.com/BlueMap-Minecraft/BlueMap/releases/download/v5.23/bluemap-5.23-cli.jar

COPY src/backend/requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY src/backend/src /app/src
COPY src/backend/tests /app/tests
COPY src/backend/pyproject.toml /app/pyproject.toml
COPY src/backend/alembic.ini /app/alembic.ini

COPY --from=frontend-build /frontend/dist /srv/frontend
COPY src/docker-container/nginx/nginx.conf /etc/nginx/nginx.conf
COPY src/docker-container/nginx/startup.conf /etc/nginx/startup.conf
COPY src/docker-container/nginx/ready.conf /etc/nginx/ready.conf
COPY src/docker-container/startup /srv/startup
#COPY src/docker-container/entrypoint.sh ./entrypoint.sh
COPY src/docker-container/loggingpoint.sh ./entrypoint.sh

RUN mkdir -p /run/unnamed-tracking /var/log/nginx \
    && chmod +x ./entrypoint.sh

EXPOSE 80
#ENTRYPOINT ["ls ./"]
ENTRYPOINT ["./entrypoint.sh"]
