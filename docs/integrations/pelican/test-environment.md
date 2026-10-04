# Test environment

A disposable Pelican Panel + Wings, rebuilt from release artifacts inside the Claude Code cloud container that ran this investigation. Rebuild it with [`experiments/setup_env.sh`](experiments/setup_env.sh) on any throwaway Linux host or VM with Docker. **Never** point the scripts at a real Panel.

## Versions

| Component | Version | Install method |
| --- | --- | --- |
| Pelican Panel | `v1.0.0-beta38` (`e84a4afd`), Laravel 13.25 | GitHub release `panel.tar.gz` + `composer install --no-dev` |
| Pelican Wings | `v1.0.0-beta29` | GitHub release `wings_linux_amd64` |
| PHP | 8.3.6 (+ `php8.3-bcmath`) | Ubuntu 24.04 archive |
| Database / cache / queue | SQLite / file / database queue (`queue:work`) + `schedule:work` | — |
| Docker | 29.6.2, cgroup v1, `overlayfs` | preinstalled; `dockerd` started manually |
| Minecraft server | **stand-in**: Minestom `2026.07.01-26.1.2` (protocol 26.1.2, `DataVersion` 4790) on Temurin 25 | built from [`experiments/standin-server/`](experiments/standin-server/) |
| Luanti server | `minetest-server` 5.6.1 + Minetest Game 1.9 | Ubuntu archive in a local yolk |
| Protocol client | `mineflayer` 4.39.0 (26.1 support) | npm |
| Renderers | BlueMap CLI 5.23 (blocked at asset download), mcmap 3.0.4 (built), `minetestmapper` 20220221 | GitHub / apt |

## Topology

```text
127.0.0.1:8000  Panel (php artisan serve, PHP_CLI_SERVER_WORKERS=8)
0.0.0.0:8080    Wings API     0.0.0.0:2022  Wings SFTP
pelican_nw      172.18.0.0/16 (Wings-created; IPv6 disabled because the kernel has none)
0.0.0.0:8099    artifact host for the stand-in egg's install script (reached as 172.18.0.1:8099)
Allocations     0.0.0.0:25580-25590 with alias 127.0.0.1 (25581 = Minecraft world host, 25584 = Luanti)
```

## Pelican objects

| Object | Value |
| --- | --- |
| Node | `ut-node-1` (FQDN 127.0.0.1, http, 8 GiB / 40 GiB / 400% CPU, upload 1024 MB) |
| Eggs | `UT Stand-in Minecraft (26.1.2)` ([yaml](experiments/egg/egg-ut-standin-minecraft.yaml)), `UT Luanti (Minetest 5.6)` ([yaml](experiments/egg/egg-ut-luanti.yaml)) |
| Images | `~utpelican/yolk-java25:local`, `~utpelican/yolk-luanti:local`, `utpelican/installer:local` ([`yolks/`](experiments/yolks/)). The `~` prefix tells Wings never to pull. |
| Users | `utadmin` (admin), `utplayer` (owner of the world hosts), `utfriend` (other tenant), `utbridge` (dedicated bridge identity, subuser) |
| Keys (identifiers only; secrets never leave `/srv/pelican/secrets`) | `app_full` (application, all resources RW), `app_min` (application, server RW + node/allocation/user/egg R), `client_player`, `client_friend`, `client_admin`, `client_bridge` |
| Servers | `UT host for ut-world:demo-a` (`external_id ut-world:demo-a`), `UT host for ut-world:luanti-a` (`external_id ut-world:luanti-a`); disposable ones created and deleted by E06 and E08d |
| Test worlds | Minecraft A (`UT Test World A`, seed 424242, gold markers), Minecraft B (`UT Test World B`, seed 1337, diamond markers, rain); Luanti A (seed 111111, gold pillar) and B (seed 222222, diamond pillar) |

## Environment-specific adjustments (and why)

| Adjustment | Reason |
| --- | --- |
| Local yolks instead of `ghcr.io/pelican-eggs/yolks` | ghcr.io blob downloads are denied by the egress policy |
| Installer image on Ubuntu, not Debian | `deb.debian.org` is denied; Ubuntu's archive is allowed |
| Minecraft stand-in instead of vanilla or Paper | Mojang and PaperMC download hosts are denied |
| `docker.network.IPv6: false` | No IPv6 in the kernel; Wings fails to create `pelican0` otherwise |
| 8 PHP CLI server workers | A single worker deadlocks on Panel → Wings → Panel calls during server creation |
| Panel and allocations on loopback, aliases set | Only loopback and private ranges bypass the sandbox's HTTPS proxy |
| Base images pulled from `mirror.gcr.io` and tagged with their Docker Hub names | Docker Hub's anonymous pull limit (HTTP 429) broke a from-scratch rebuild |
| Maven (in Docker) gets the sandbox proxy from `HTTPS_PROXY` | Maven ignores proxy environment variables, and the proxy's port changes between sessions, so a hardcoded port broke a rebuild |

## Reproducing

```bash
sudo ./docs/integrations/pelican/experiments/setup_env.sh   # fresh Panel + Wings + images
sudo ./docs/integrations/pelican/experiments/run_all.sh     # test worlds, then every experiment in run 1's order
```

`run_all.sh` passes every script its arguments, sets up the preconditions each one expects (the world to start from, the E04 backup for E04c, the 1 MB upload limit around E12), and stops at the first failure. E04d runs last, as in run 1, because it captures as the bridge identity that E06 makes a subuser. `/srv/pelican/evidence/run_all.log` holds the combined output. Behind an egress proxy, use `sudo -E` (or run as root) so `setup_env.sh` still sees `HTTPS_PROXY`. E06 prints `CHECK` because of a known finding: a client key can mint sibling keys. That isn't a failure of the run.

Every script appends to `/srv/pelican/evidence/api-calls.jsonl`. Any field whose name contains `token`, `secret` or `password` is redacted, as are `socket` and `url`. Full API keys, JWTs and signed-URL parameters are also masked inside other strings.

The first version of the harness redacted only a fixed list of field names (`token`, `token_id`, `daemon_token`, `password`, `socket`, `url`). That let one secret into the committed log: the `secret_token` Pelican returned for the key E06's minting probe created. Run 1 had already deleted that key within 33 seconds of minting it (the run's own cleanup; the test Panel's database holds no such key), and it was only ever valid against the loopback test Panel. The reproduction run found the leak, and the committed log has been re-redacted with the current rules. A value-based scan against every credential the test Panel issued, rather than a pattern-based one, has not been run.
