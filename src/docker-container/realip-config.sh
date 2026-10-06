#!/bin/sh
set -eu
payload="$(curl -fsS http://127.0.0.1:8000/api/internal/real-ip)" || { printf '%s\n' "Unable to retrieve real-IP configuration from the backend." >&2; exit 1; }
REALIP_PAYLOAD="$payload" python - <<'PY'
import json, os, shlex
payload=json.loads(os.environ["REALIP_PAYLOAD"])
print("export NGINX_REALIP_HEADER="+shlex.quote(str(payload["header"])))
print("export NGINX_REALIP_TRUSTED_PROXIES="+shlex.quote(str(payload["trusted_proxies"])))
PY
