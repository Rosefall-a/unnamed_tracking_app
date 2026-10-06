FROM python:3.12-alpine

RUN pip install --no-cache-dir "mkdocs-material==9.7.7"

WORKDIR /wiki
COPY wiki/ /wiki/

ENV WIKI_CONTAINER_BIND_PORT=999

EXPOSE 999

CMD ["sh", "-c", "exec mkdocs serve --dev-addr=0.0.0.0:${WIKI_CONTAINER_BIND_PORT} --config-file=/wiki/mkdocs.yml"]
