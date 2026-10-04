# Local stand-in for ghcr.io/parkervcp/games:minetest (ghcr.io blobs are blocked in the test env).
# Real Luanti (Minetest) 5.6.1 server + Minetest Game from the Ubuntu archive.
FROM ubuntu:24.04
RUN apt-get update -y && apt-get install -y --no-install-recommends minetest-server minetest-data iproute2 tini ca-certificates curl && rm -rf /var/lib/apt/lists/*
RUN useradd -m -d /home/container -s /bin/bash container
USER container
ENV USER=container HOME=/home/container
WORKDIR /home/container
STOPSIGNAL SIGINT
COPY --chown=container:container ./entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/usr/bin/tini", "-g", "--"]
CMD ["/entrypoint.sh"]
