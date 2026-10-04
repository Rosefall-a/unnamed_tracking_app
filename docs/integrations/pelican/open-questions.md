# Open questions

## Answered during discovery

| # | Question | Decision |
| --- | --- | --- |
| D1 | Where do byte transfer and live connections live? | Narrow, Pelican-scoped **host bridge** capabilities; the plugin orchestrates |
| D2 | Create servers or attach to existing ones first? | **Attach first**; creation is a later, admin-opt-in milestone |
| D3 | Where is the durable copy of a world? | **UT archives are the record**; Pelican backups are a short-lived safety net |
| D4 | How does M1 avoid overwriting progress? | **Custody plus capture-back in M1** |
| D5 | How does hosted playtime relate to `Game.playtime_seconds`? | **Separate hosted sessions**; never write that column |
| D6 | First map source for Pelican worlds | **Reuse core BlueMap on snapshots**, adapter fallback |

## Still open (decisions)

| # | Question | Options | Recommendation |
| --- | --- | --- | --- |
| Q1 | How does a UT user come to own a Pelican server in UT? The shared `ut-bridge` account sees every server it was added to, across Pelican users. | (a) UT admin assigns servers to UT users; (b) **claim code**: UT shows a code, the owner puts it in the server's Pelican description, and the bridge reads it (`GET /servers/{id}`, no extra permission) to prove control; (c) one bridge account per UT user | (a) for M1, (b) as self-service later. Avoid (c): each account is another credential. |
| Q2 | How is the bridge deployed? It holds long-lived websockets, and the backend runs a single worker with in-memory state (BlueMap status). | asyncio tasks in the backend process; a separate bridge worker process (same image, DB and data volume); a separate container | A separate worker process in the backend image: it survives request load, and restarts are reconciled (E08b, Wings reattach). |
| Q3 | Should contracts be Pelican-named (`pelican.*`) or provider-neutral (`hosting.*`, with Pelican as the first provider)? | | Neutral **contracts** (`hosting.*`), Pelican-only **implementation**, and the connection record carries `provider`. This keeps D1's narrow surface while not hard-coding a vendor into plugin APIs. Needs your call. |
| Q4 | Stop & Save default: cold (stop, then capture; consistent) or hot (`save-off/all` → backup; no downtime)? | | Cold for explicit Stop & Save; hot only for periodic snapshots (M2). |
| Q5 | What happens when stop times out? | ask the user; kill automatically after N s; never kill | Ask the user (M1). `kill` can lose unsaved progress. |
| Q6 | Privacy: sessions and positions of **other players** who aren't UT users | store names; store hashed IDs; store only the owner's own player | Store names (needed for "who played"), positions opt-in per world, retention-limited, and visible only to the world owner. Needs product sign-off. |
| Q7 | Retention defaults | UT versions (last N + daily/weekly); `.ut-prev/` asides (keep newest 1–2); Pelican safety backups (delete after a verified swap) | As listed; configurable per world |
| Q8 | Is BlueMap's Mojang asset download (from the UT backend) acceptable as a hard requirement for M3? | | Yes, with the adapter fallback when egress is denied. This is already true of today's core world-map feature. |
| Q9 | Luanti `worldmods/` are Lua the game server executes. Deploy worlds that contain them? | allow with a label; strip; refuse | Allow with a visible label (they run inside the game container, not UT). |
| Q10 | Does the plugin need a long-lived worker at all? Workers have a cumulative 60 CPU-second limit, and I found no restart in `runtime.py`. | long-lived loop (Jellyfin pattern); short action-driven calls plus `events.poll` ticks | If the bridge owns the websocket, the plugin can be action- and tick-driven, which avoids the CPU-limit risk. Confirm the runtime restart behaviour either way. |

## Still unverified (experiments that remain)

| Item | Why not done here | What would close it |
| --- | --- | --- |
| Vanilla and Paper behaviour (log formats, 26.1 world layout, `level.dat` fields, `data get entity`, newer-world refusal) | Mojang and PaperMC hosts are denied by this environment's network policy | Allow `piston-meta.mojang.com`, `piston-data.mojang.com`, `libraries.minecraft.net`, `api.papermc.io`, `fill.papermc.io`, `fill-data.papermc.io` and re-run E02–E11 with the upstream Vanilla and Paper eggs |
| BlueMap render of a captured world | Same (Mojang client jar) | Same allow-list, then the core render route on a captured version |
| UT core thumbnail on real 26.1 worlds | Layout evidence comes from Minestom 26.1, not vanilla | A vanilla 26.1 world |
| Luanti player join/leave and `players.sqlite` | No headless Luanti client | A desktop client, or a Go/Rust protocol client |
| Terraria/TShock | The installer needs the GitHub Releases API, which this sandbox doesn't serve | Run the upstream TShock egg on a normal network |
| Real client IPs | Docker userland-proxy NAT shows the gateway (E07) | A test with `userland-proxy: false` / host networking |
| Plugin-runtime worker restart after the CPU limit | Not exercised | A runtime test with a CPU-burning worker |
| Mod and plugin detection | Not attempted | List `mods/` and `plugins/` on Fabric and Paper servers |
| Live web maps (BlueMap/squaremap plugins) | Paper blocked; out of scope by D6 | Later |
