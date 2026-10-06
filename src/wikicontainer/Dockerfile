FROM python:3.12-alpine

RUN pip install --no-cache-dir "mkdocs-material==9.7.7"

WORKDIR /wiki
COPY wiki/ /wiki/

EXPOSE 8000

CMD ["mkdocs", "serve", "--dev-addr=0.0.0.0:8000", "--config-file=/wiki/mkdocs.yml"]
