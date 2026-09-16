# Central image: reuse the existing frontend and backend runtime choices.
FROM node:22-slim AS node-runtime
FROM python:3.12-slim

WORKDIR /app

# Keep these dependencies aligned with src/backend/dockerfile.
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    postgresql-client \
    curl \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Reuse Node 22 from the same official image as the standalone frontend.
COPY --from=node-runtime /usr/local/bin/node /usr/local/bin/node
COPY --from=node-runtime /usr/local/lib/node_modules/npm /usr/local/lib/node_modules/npm
RUN ln -s /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
    && ln -s /usr/local/lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx

# Keep the same Java/BlueMap runtime used by the backend image.
RUN curl -fL -o /tmp/jre.tar.gz \
    https://github.com/adoptium/temurin25-binaries/releases/download/jdk-25.0.4.1%2B1/OpenJDK25U-jre_x64_linux_hotspot_25.0.4.1_1.tar.gz \
    && mkdir -p /opt/java \
    && tar -xzf /tmp/jre.tar.gz -C /opt/java --strip-components=1 \
    && rm /tmp/jre.tar.gz
ENV JAVA_HOME=/opt/java
ENV PATH="${JAVA_HOME}/bin:${PATH}"

RUN curl -fL -o /opt/bluemap-cli.jar \
    https://github.com/BlueMap-Minecraft/BlueMap/releases/download/v5.23/bluemap-5.23-cli.jar

# Reuse the existing backend dependency manifest; do not duplicate it.
COPY src/backend/requirements.txt /app/backend-requirements.txt
RUN pip install --no-cache-dir -r /app/backend-requirements.txt

# Preserve the backend's existing /app layout.
COPY src/backend/src /app/src
COPY src/backend/alembic.ini /app/alembic.ini

# Reuse the frontend's existing package manifest and source.
COPY src/frontend/package*.json /app/frontend/
WORKDIR /app/frontend
RUN npm install
COPY src/frontend/. /app/frontend/

WORKDIR /app

# The combined image defaults to both processes. Override APP_MODE at runtime
# for the same image when it is used as a standalone frontend or backend.
ENV APP_MODE=both
EXPOSE 80 8000

COPY src/central/entrypoint.sh /usr/local/bin/central-entrypoint.sh
RUN chmod +x /usr/local/bin/central-entrypoint.sh

ENTRYPOINT ["/usr/local/bin/central-entrypoint.sh"]
