#!/usr/bin/env bash
# Rebuilds the disposable Pelican Panel + Wings test environment used by the discovery experiments.
# Run as root on a throwaway Linux host or VM with Docker. Never point this at a real Panel.
#
# Produces:
#   /srv/pelican/panel        Panel v1.0.0-beta38 (release tarball, SQLite, artisan serve with 8 workers)
#   /srv/pelican/wings/wings  Wings v1.0.0-beta29 (release binary), config at /etc/pelican/config.yml
#   /srv/pelican/secrets/     Generated passwords and API keys (never commit this directory)
#   utpelican/yolk-java25:local, utpelican/installer:local   Locally built yolks (ghcr.io is blocked)
#   /srv/pelican/artifacts/server.jar served on :8099 for the stand-in egg's install script
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
PANEL_TAG=v1.0.0-beta38
WINGS_TAG=v1.0.0-beta29
mkdir -p /srv/pelican/{panel,wings,secrets,evidence,worlds,standin/bot,artifacts,logs,m2} /etc/pelican /var/lib/pelican/volumes
chmod 700 /srv/pelican/secrets

# --- Docker daemon (the container image ships the CLI and daemon, not a running service) ----------
docker info >/dev/null 2>&1 || { nohup dockerd >/srv/pelican/logs/dockerd.log 2>&1 & sleep 5; }

# --- Panel -------------------------------------------------------------------------------------
apt-get install -y -q php8.3-bcmath >/dev/null   # the only missing extension on the base image
curl -fsSL -o /srv/pelican/panel.tar.gz "https://github.com/pelican-dev/panel/releases/download/${PANEL_TAG}/panel.tar.gz"
tar xzf /srv/pelican/panel.tar.gz -C /srv/pelican/panel
cd /srv/pelican/panel
COMPOSER_ALLOW_SUPERUSER=1 composer install --no-dev --optimize-autoloader --no-interaction
cat > .env <<'EOF'
APP_ENV=production
APP_DEBUG=false
APP_KEY=
APP_URL=http://127.0.0.1:8000
APP_INSTALLED=true
APP_LOCALE=en
APP_TIMEZONE=UTC
DB_CONNECTION=sqlite
DB_DATABASE=/srv/pelican/panel/database/database.sqlite
CACHE_STORE=file
SESSION_DRIVER=file
QUEUE_CONNECTION=database
MAIL_MAILER=log
APP_BACKUP_DRIVER=wings
EOF
touch database/database.sqlite
php artisan key:generate --force
php artisan migrate --seed --force
# A single-worker PHP server deadlocks on Panel -> Wings -> Panel calls (server create), so use 8.
PHP_CLI_SERVER_WORKERS=8 nohup php artisan serve --host=127.0.0.1 --port=8000 --no-reload >/srv/pelican/logs/panel.log 2>&1 &
nohup php artisan queue:work --sleep=1 --tries=3 >/srv/pelican/logs/queue.log 2>&1 &
nohup php artisan schedule:work >/srv/pelican/logs/schedule.log 2>&1 &
sleep 3

umask 077
for u in admin utplayer utfriend utbridge; do openssl rand -base64 18 | tr -d '/+=' > "/srv/pelican/secrets/$u.password"; done
php artisan p:user:make --email=admin@ut-pelican.test --username=utadmin --password="$(cat /srv/pelican/secrets/admin.password)" --admin=1
php artisan p:user:make --email=player@ut-pelican.test --username=utplayer --password="$(cat /srv/pelican/secrets/utplayer.password)" --admin=0
php artisan p:user:make --email=friend@ut-pelican.test --username=utfriend --password="$(cat /srv/pelican/secrets/utfriend.password)" --admin=0
# Dedicated least-privilege bridge identity; server owners add it as a subuser (see e06_least_privilege.py).
php artisan p:user:make --email=bridge@ut-pelican.test --username=utbridge --password="$(cat /srv/pelican/secrets/utbridge.password)" --admin=0
php artisan p:node:make --name=ut-node-1 --description="UT discovery node" --fqdn=127.0.0.1 --public=1 --scheme=http \
  --proxy=0 --maintenance=0 --maxMemory=8192 --overallocateMemory=0 --maxDisk=40960 --overallocateDisk=0 --maxCpu=400 \
  --overallocateCpu=0 --uploadSize=1024 --daemonListeningPort=8080 --daemonConnectingPort=8080 --daemonSFTPPort=2022 \
  --daemonSFTPAlias="" --daemonBase=/var/lib/pelican/volumes

# API keys through Pelican's own KeyCreationService (same path as the UI).
ALL='{"server":3,"node":3,"allocation":3,"user":3,"egg":3,"database_host":3,"database":3,"mount":3,"role":3,"plugin":3}'
MIN='{"server":3,"node":1,"allocation":1,"user":1,"egg":1}'
mk() { KEY_USER=$1 KEY_TYPE=$2 KEY_PERMS="$3" KEY_NAME=$4 php artisan tinker --execute "require '$HERE/mkkey.php';"; }
mk utadmin 2 "$ALL" app_full
mk utadmin 2 "$MIN" app_min
mk utplayer 1 '{}' client_player
mk utfriend 1 '{}' client_friend
mk utadmin 1 '{}' client_admin
mk utbridge 1 '{}' client_bridge
umask 022

# --- Wings -------------------------------------------------------------------------------------
curl -fsSL -o /srv/pelican/wings/wings "https://github.com/pelican-dev/wings/releases/download/${WINGS_TAG}/wings_linux_amd64"
chmod +x /srv/pelican/wings/wings
php artisan p:node:configuration 1 --format=yaml > /etc/pelican/config.yml
chmod 600 /etc/pelican/config.yml
# The test kernel has no IPv6; Wings defaults docker.network.IPv6 to true and fails to create pelican0.
python3 - <<'EOF'
import yaml
p = '/etc/pelican/config.yml'
c = yaml.safe_load(open(p))
c.setdefault('docker', {}).setdefault('network', {})['IPv6'] = False
open(p, 'w').write(yaml.safe_dump(c))
EOF
(cd /srv/pelican/wings && NO_PROXY="127.0.0.1,localhost,172.18.0.0/16" nohup ./wings --config /etc/pelican/config.yml >/srv/pelican/logs/wings.log 2>&1 &)
sleep 8

# --- Yolks, stand-in server, artifact host -------------------------------------------------------
docker build -q --network host -t utpelican/yolk-java25:local "$HERE/yolks/java25"
docker build -q --network host -t utpelican/installer:local "$HERE/yolks/installer"
docker build -q --network host -t utpelican/yolk-luanti:local "$HERE/yolks/luanti"   # second game (E10)
docker pull -q maven:3-eclipse-temurin-25
docker pull -q eclipse-temurin:25-jdk-noble
docker tag eclipse-temurin:25-jdk-noble mirror.gcr.io/library/eclipse-temurin:25-jdk-noble
cp -r "$HERE/standin-server" /srv/pelican/standin/src
# Maven inside Docker needs the egress proxy + its CA in this sandbox; drop these two lines elsewhere.
printf '<settings><proxies><proxy><id>p</id><active>true</active><protocol>https</protocol><host>127.0.0.1</host><port>38809</port></proxy></proxies></settings>' > /srv/pelican/m2/settings.xml
docker run --rm --network host -v /srv/pelican/standin/src:/src -v /srv/pelican/m2:/root/.m2 \
  -v /root/.ccr/ca-bundle.crt:/ca.crt:ro -w /src maven:3-eclipse-temurin-25 bash -c \
  'keytool -importcert -noprompt -alias ccr -file /ca.crt -cacerts -storepass changeit >/dev/null 2>&1; mvn -q -B package -s /root/.m2/settings.xml'
cp /srv/pelican/standin/src/target/standin-server.jar /srv/pelican/artifacts/server.jar
cp /srv/pelican/standin/src/target/standin-server.jar /srv/pelican/standin/standin-server.jar
(cd /srv/pelican/artifacts && nohup python3 -m http.server 8099 --bind 0.0.0.0 >/srv/pelican/logs/artifacts.log 2>&1 &)

# --- Egg + allocations ---------------------------------------------------------------------------
APP=$(cat /srv/pelican/secrets/app_full.key)
H=(-H "Authorization: Bearer $APP" -H "Accept: application/json")
curl -fsS "${H[@]}" -H 'Content-Type: application/yaml' --data-binary @"$HERE/egg/egg-ut-standin-minecraft.yaml" \
  http://127.0.0.1:8000/api/application/eggs/import >/dev/null
curl -fsS "${H[@]}" -H 'Content-Type: application/yaml' --data-binary @"$HERE/egg/egg-ut-luanti.yaml" \
  http://127.0.0.1:8000/api/application/eggs/import >/dev/null
# Bind 0.0.0.0 and publish an alias. A 127.0.0.1 allocation is silently re-bound by Wings to the
# pelican0 gateway (172.18.0.1), so the address the Panel reports would not be joinable.
# Note: the Application API field is "alias"; "ip_alias" is silently ignored.
curl -fsS "${H[@]}" -H 'Content-Type: application/json' \
  -d '{"ip":"0.0.0.0","alias":"127.0.0.1","ports":["25581-25590","2456-2460","7777-7780"]}' \
  http://127.0.0.1:8000/api/application/nodes/1/allocations

# --- Python + Node test clients ------------------------------------------------------------------
pip install -q requests websocket-client nbtlib pillow
apt-get install -y -q minetestmapper >/dev/null   # asset-free Luanti renderer (E10)
cp "$HERE/bot.js" /srv/pelican/standin/bot/
(cd /srv/pelican/standin/bot && npm init -y >/dev/null && npm install --silent mineflayer)
# Screenshots: node screenshots.mjs <out> <mc_server> <luanti_server> from a dir whose node_modules
# links to a Playwright install (Chromium is preinstalled under /opt/pw-browsers here).
echo "Pelican test environment ready: Panel http://127.0.0.1:8000, Wings :8080"
