#!/usr/bin/env bash
# Reruns every Pelican discovery experiment, in order, on an environment built by setup_env.sh.
# usage (as root): docs/integrations/pelican/experiments/run_all.sh
# Output: /srv/pelican/evidence/run_all.log; every API call: /srv/pelican/evidence/api-calls.jsonl.
# Stops at the first experiment that exits non-zero.
set -euo pipefail
cd "$(dirname "$0")"
EV=/srv/pelican/evidence
W=/srv/pelican/worlds
S=$EV/server-demo-a.json
LOG=$EV/run_all.log
mkdir -p "$EV"

step() { printf '\n=== %s (%s)\n' "$*" "$(date -u +%H:%M:%S)" | tee -a "$LOG"; }
run() { python3 "$@" 2>&1 | tee -a "$LOG"; }
set_upload_limit() {
  python3 -c "import yaml; p='/etc/pelican/config.yml'; c=yaml.safe_load(open(p)); c['api']['upload_limit']=$1; open(p,'w').write(yaml.safe_dump(c))"
}
restart_wings() {
  kill "$(pgrep -x wings)"
  sleep 3
  # Background only wings itself, so the subshell exits at once and nothing reports its later kill.
  (cd /srv/pelican/wings || exit 1; NO_PROXY="127.0.0.1,localhost,172.18.0.0/16" nohup ./wings --config /etc/pelican/config.yml >>/srv/pelican/logs/wings.log 2>&1 &)
  python3 -c "import requests; from ptlab import wait_for; wait_for(lambda: requests.get('http://127.0.0.1:8080/api/system', timeout=2).status_code == 401, 60, 1, 'wings')"
}
backup_uuid() {
  python3 -c "import json, sys; from ptlab import Api; s=json.load(open('$S'))['identifier']; print([b['attributes']['uuid'] for b in Api('client', 'client_player', 'run-all').get(f'servers/{s}/backups').json()['data'] if b['attributes']['name'] == sys.argv[1]][0])" "$1"
}

step "versions"
(cd /srv/pelican/panel && php artisan tinker --execute 'echo "Panel ", config("app.version"), PHP_EOL;' 2>/dev/null) | tee -a "$LOG"
/srv/pelican/wings/wings version 2>/dev/null | head -1 | tee -a "$LOG"

step "test worlds A and B"
run make_test_world.py "$W/a" "UT Test World A" 424242 minecraft:gold_block 4 100 4 clear
run make_test_world.py "$W/b" "UT Test World B" 1337 minecraft:diamond_block -6 100 9 rain

step "E01 create a server for world A"
ALLOC=$(python3 -c "from ptlab import Api; print([a['attributes']['id'] for a in Api('application', 'app_full', 'run-all').get('nodes/1/allocations', params={'per_page': 100}).json()['data'] if a['attributes']['port'] == 25581][0])")
run e01_create_server.py ut-world:demo-a "$ALLOC"
step "E02 lifecycle and readiness";        run e02_lifecycle.py "$S"
step "E03 deploy world B";                 run e03_deploy_world.py "$S" "$W/b/ut-test-world-b.tar.gz" minecraft:diamond_block
step "E03 deploy world A";                 run e03_deploy_world.py "$S" "$W/a/ut-test-world-a.tar.gz" minecraft:gold_block
step "E03 deploy world B (E04 start)";     run e03_deploy_world.py "$S" "$W/b/ut-test-world-b.tar.gz" minecraft:diamond_block
step "E04 backups as capture/restore";     run e04_backups.py "$S"
step "E04b truncate-restore recovery";     run e04b_restore_recovery.py "$S" "$EV/backup-world-b.tar.gz"
step "E03 deploy world A (E04c start)";    run e03_deploy_world.py "$S" "$W/a/ut-test-world-a.tar.gz" minecraft:gold_block
step "E04c safe restore";                  run e04c_safe_restore.py "$S" "$(backup_uuid ut-capture-world-b)" "$EV/backup-world-b.tar.gz" 1337 minecraft:diamond_block
step "E05 files/pull reachability";        run e05_files_pull.py "$S" "$W/b/ut-test-world-b.tar.gz" /srv/pelican/artifacts
step "E06 least privilege";                run e06_least_privilege.py "$S"
step "E07 tracking";                       run e07_tracking.py "$S"
step "E08a archive safety";                run e08a_archive_safety.py "$S" "$W/a/ut-test-world-a.tar.gz"
step "E08b runtime failures";              run e08b_runtime_failures.py "$S" "$W/a/world"
step "E08c isolated crash";                run e08c_crash_isolated.py "$S"
step "E08d server deletion";               run e08d_server_deletion.py
step "E09 visualise world B";              run e09_visualise.py "$W/b/world" "$EV/e09-world-b-map.png"
step "E09b session -> snapshot -> map";    run e09b_session_snapshot_map.py "$S" "$EV/e09b"
step "E10 Luanti";                         run e10_luanti.py "$EV/server-luanti-a.json" /srv/pelican/luanti
step "E11 custody";                        run e11_custody.py "$S"
step "E12 large world as parts (upload limit 1 MB)"
set_upload_limit 1
restart_wings
run e12_large_world_parts.py "$S"
set_upload_limit 1024
restart_wings
# Last, as in run 1: E04d captures as the bridge identity, which E06 makes a subuser.
step "E04d world-only capture";            run e04d_world_only_capture.py "$S"
step "done"
