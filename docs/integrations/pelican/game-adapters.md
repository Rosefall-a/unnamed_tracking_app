# Game adapter proposal

The integration must not assume every game works like Minecraft. Two games were run through the **same** Pelican sequence: Minecraft (26.1.2-protocol stand-in) and **Luanti 5.6.1** (real server, E10). A third, Terraria via TShock, is analysed from its upstream `pelican-eggs` egg only, because its installer needs the GitHub Releases API, which this sandbox doesn't serve.

## Comparison

| Concern | Minecraft Java | Luanti (Minetest) | Terraria (TShock) |
| --- | --- | --- | --- |
| Evidence level | Run (stand-in) | **Run (real)** | Egg only |
| World on disk | Directory `world/` (name from `server.properties` `level-name`) | Directory `worlds/<WORLD_NAME>/` (CLI `--world`) | **Single file** `<WORLD_NAME>.wld` (+ `.bak`) |
| Main files | `level.dat` (gzip NBT), region `.mca` per 32×32 chunks, player `.dat` per UUID; 26.1 layout `dimensions/minecraft/overworld/region`, `players/data` (stand-in) | `world.mt`, `map_meta.txt`, `env_meta.txt`, **`map.sqlite` (one potentially huge file)**, `players.sqlite` (created on first join), `worldmods/` | one binary `.wld` |
| Identity | `level.dat`: seed, `LevelName`, `DataVersion` ✅ | `map_meta.txt` `seed` ✅, `world.mt` `gameid` ✅ | `.wld` header (name, ID, version), from format knowledge only |
| Missing world → | **new world, silently** ✅ | **new world, silently** ✅ | `-autocreate` in the egg, so a new world silently (inferred from the egg) |
| Newer world version → | refuse, crash loop ✅ (stand-in) | not tested | not tested |
| Readiness (egg `done`) | `)! For help, type ` ✅ | `Server for gameid` ✅, **but only without `--terminal`** (E10) | `Type 'help' for a list of commands` (egg) |
| Stop | `stop` | `^C` without a terminal (`/shutdown` needs `--terminal`) ✅ | `exit` (egg) |
| Console commands | yes ✅ | **no** without `--terminal` ✅ | yes (egg) |
| Flush for hot capture | `save-off`, `save-all` → `Saved the game` ✅ | none on the console; capture **cold** | `save` (TShock); not tested |
| Join/leave lines | `X joined the game` / `X left the game`, `X[/ip:port] logged in … at (x,y,z)` ✅ | `X [ip] joins game` / `X leaves game` (from docs; **no client available**) | TShock `X has joined.` / `X has left.` (from docs) |
| Live position | console `data get entity X Pos` ✅ | Lua API or mod only | TShock REST (extra port and token) |
| Saved player state | per-player NBT: Pos, Dimension, Rotation ✅ | `players.sqlite` (pos ×10) (from docs) | **client-side characters** unless SSC |
| Asset-free map | top-block render from region data ✅ (E09) | `minetestmapper` + open `colors.txt` ✅ (E10) | no standard CLI found |
| High-fidelity map | BlueMap (needs Mojang client jar) | `minetestmapper` already is | — |
| Terrain exists without players | yes (spawn chunks) | **no**: only generated around players or an emerge (E10) | whole world generated up front |
| Upload-limit fit | many mid-size files, so splittable ✅ (E12) | **one large `map.sqlite`**, so the node upload limit must exceed it | one file, small to mid size |

✅ = observed in this investigation.

## Universal (belongs in the bridge, game-agnostic)

* Power, websocket supervision, `status`, the `[pelican Daemon]` crash block, server runtime accounting.
* Archive safety: entry types, paths, sizes, uncompressed total vs disk and upload limits.
* The staged deploy with upload parts → staging → rename swap → custody marker → start → readiness timeout (E03, E12, E11).
* Capture via backup with an `ignored` list → stream → archive version (E04, E09b).
* Join address from the allocation (E03).

## Game-specific (belongs in the adapter)

* Where the world lives, relative to the server root, possibly derived from an egg variable or a config file.
* What a valid archive must contain, and how to read identity from it.
* The compatibility rule (game version or data version vs the server).
* Console line patterns for join, leave, login position and save-complete, and whether the console accepts commands at all.
* Hot-capture commands, or "cold only".
* Player-state source, and the map renderer to use.
* Join instructions (client version, mod list, "add server" hints).

## Minimum useful abstraction

A **declarative descriptor** shipped inside the UT plugin, plus a few small functions that run in the sandbox on **bounded bytes** the bridge hands them. The bridge interprets only the declarative parts (paths, regexes, command allow-list), so the host stays game-agnostic and the plugin never touches I/O.

```yaml
id: minecraft-java
match: { egg_features: [eula], egg_name_contains: [minecraft, paper, vanilla] }
game_version_from: { egg_variable: [MINECRAFT_VERSION, VANILLA_VERSION] }   # else first console line
world:
  root: { from_file: server.properties, key: level-name, default: world }
  kind: directory
  required: [level.dat]
  identity_files: [level.dat]            # ≤ 1 MiB each, handed to identify()
capture:
  ignored: ["*", "!{root}", "!{root}/**"]   # world only; negation verified in E04d
  hot: { before: [save-off, save-all], wait_for: "Saved the game", after: [save-on] }
console:
  join:  '^\[[^]]+\] \[Server thread/INFO\]: (?P<name>\w+) joined the game'
  leave: '^\[[^]]+\] \[Server thread/INFO\]: (?P<name>\w+) left the game'
  position_command: 'data get entity {name} Pos'
  position: '(?P<name>\w+) has the following entity data: \[(?P<x>[-\d.]+)d, (?P<y>[-\d.]+)d, (?P<z>[-\d.]+)d\]'
  list_command: list
  allowed_commands: [save-off, save-all, save-on, list, 'data get entity * Pos', seed]
timeouts: { ready_s: 180, stop_s: 60 }
map: { renderer: bluemap, fallback: topdown }
```

```text
identify(files: {path: bytes}) -> Identity        # e.g. parse NBT level.dat → seed, name, data_version
compatible(identity, server: {game_version, egg}) -> ok | reason
verify_running(identity, probe) -> ok | reason     # e.g. compare `seed` output, or re-read map_meta.txt
join_instructions(runtime, identity) -> text
```

The Luanti descriptor differs only in data: `root: worlds/{WORLD_NAME}`, `required: [world.mt, map_meta.txt]`, `capture.hot: none` (cold only), `console` with join/leave and no commands, `map: minetestmapper`. That is the test that the abstraction is the right size.

What is **not** in the abstraction (deliberately): mod or plugin installation, server config editing, version upgrades, and cross-game conversion ([roadmap: out of scope](roadmap.md#out-of-scope-for-the-first-implementation)).

## Shipping order

1. `minecraft-java` (vanilla, Paper and Fabric eggs share the world format; mods are out of scope).
2. `luanti`, proving the abstraction against a second real game, with cold capture only.
3. Others on demand. Single-file games (Terraria, Valheim) need the upload limit check, and their player state may be client-side, so Track would rely on console lines only.
