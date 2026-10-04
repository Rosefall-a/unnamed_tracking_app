# Local rebuild of ghcr.io/pelican-eggs/yolks:java_25 (ghcr.io blobs are blocked in the test env)
FROM eclipse-temurin:25-jdk-noble
RUN apt-get update -y && apt-get install -y lsof curl ca-certificates openssl git tar sqlite3 fontconfig tzdata iproute2 libfreetype6 tini zip unzip jq && rm -rf /var/lib/apt/lists/*
RUN useradd -m -d /home/container -s /bin/bash container
USER container
ENV USER=container HOME=/home/container
WORKDIR /home/container
STOPSIGNAL SIGINT
COPY --chown=container:container ./entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/usr/bin/tini", "-g", "--"]
CMD ["/entrypoint.sh"]
