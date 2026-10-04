"""E09: Visualise — what a Minecraft adapter can extract from a captured save with no game assets.

usage: e09_visualise.py <world_dir> <out.png> [<positions.json from E07 evidence>]
Reads level.dat (identity, time, weather, spawn), every saved player file (position, dimension,
rotation), the region headers (explored chunks) and the chunk sections (top block per column),
then renders a top-down map with the spawn, saved player positions and optional live samples.
Supports both the pre-26.1 layout (world/region, world/playerdata) and the layout produced by
the 26.1 stand-in (world/dimensions/minecraft/overworld/region, world/players/data).
"""
import hashlib
import io
import json
import struct
import sys
import zlib
from pathlib import Path

import nbtlib
from PIL import Image, ImageDraw

world = Path(sys.argv[1])
out = Path(sys.argv[2])
live = json.load(open(sys.argv[3])) if len(sys.argv) > 3 else []

PALETTE = {
    "grass_block": (95, 159, 53), "dirt": (134, 96, 67), "stone": (125, 125, 125), "water": (64, 64, 255),
    "sand": (219, 207, 163), "bedrock": (60, 60, 60), "gold_block": (249, 212, 61),
    "diamond_block": (98, 237, 228), "oak_log": (109, 85, 50), "oak_leaves": (60, 120, 40),
    "snow_block": (240, 250, 250), "gravel": (136, 126, 126), "deepslate": (80, 80, 82),
}


def color(name: str) -> tuple[int, int, int]:
    short = name.split(":")[-1]
    if short in PALETTE:
        return PALETTE[short]
    h = hashlib.md5(short.encode()).digest()
    return (80 + h[0] % 120, 80 + h[1] % 120, 80 + h[2] % 120)


def root_of(nbt):
    return nbt[""] if "" in nbt and len(nbt) == 1 else nbt


def first(*paths: Path) -> Path | None:
    return next((p for p in paths if p.exists()), None)


# --- world state from level.dat ---
level = root_of(nbtlib.load(world / "level.dat"))["Data"]
state = {
    "level_name": str(level.get("LevelName")),
    "seed": int(level["WorldGenSettings"]["seed"]) if "WorldGenSettings" in level else None,
    "data_version": int(level.get("DataVersion", 0)),
    "version_name": str(level["Version"]["Name"]) if "Version" in level else None,
    "day_time": int(level.get("DayTime", 0)), "day": int(level.get("DayTime", 0)) // 24000,
    "raining": bool(level.get("raining", 0)), "spawn": [int(level.get(k, 0)) for k in ("SpawnX", "SpawnY", "SpawnZ")],
}

# --- player state from saved player files ---
players = []
pdir = first(world / "players" / "data", world / "playerdata")
for f in sorted(pdir.glob("*.dat")) if pdir else []:
    p = root_of(nbtlib.load(f))
    players.append({"uuid": f.stem, "pos": [round(float(v), 1) for v in p["Pos"]],
                    "dimension": str(p.get("Dimension", "minecraft:overworld")),
                    "rotation": [round(float(v), 1) for v in p.get("Rotation", [])]})

# --- explored chunks + top block per column ---
region_dir = first(world / "dimensions" / "minecraft" / "overworld" / "region", world / "region")
tops: dict[tuple[int, int], str] = {}
explored = set()
for rf in sorted(region_dir.glob("r.*.*.mca")):
    _, rx, rz, _ = rf.name.split(".")
    rx, rz = int(rx), int(rz)
    data = rf.read_bytes()
    for i in range(1024):
        off = int.from_bytes(data[i * 4:i * 4 + 3], "big")
        if not off:
            continue
        cx, cz = rx * 32 + i % 32, rz * 32 + i // 32
        explored.add((cx, cz))
        start = off * 4096
        length, comp = struct.unpack(">I", data[start:start + 4])[0], data[start + 4]
        raw = data[start + 5:start + 4 + length]
        chunk = root_of(nbtlib.File.parse(io.BytesIO(zlib.decompress(raw) if comp == 2 else raw)))
        for sec in sorted(chunk.get("sections", []), key=lambda s: -int(s["Y"])):
            pal = [str(b["Name"]) for b in sec["block_states"]["palette"]]
            if pal == ["minecraft:air"]:
                continue
            bits = max(4, (len(pal) - 1).bit_length())
            per_long = 64 // bits
            longs = [int(v) & 0xFFFFFFFFFFFFFFFF for v in sec["block_states"].get("data", [])]
            for x in range(16):
                for z in range(16):
                    if (cx * 16 + x, cz * 16 + z) in tops:
                        continue
                    for y in range(15, -1, -1):
                        idx = y * 256 + z * 16 + x
                        b = 0 if not longs else (longs[idx // per_long] >> ((idx % per_long) * bits)) & ((1 << bits) - 1)
                        if pal[b] not in ("minecraft:air", "minecraft:cave_air", "minecraft:void_air"):
                            tops[(cx * 16 + x, cz * 16 + z)] = pal[b]
                            break

# --- render ---
xs = [x for x, _ in explored]
zs = [z for _, z in explored]
min_x, min_z = min(xs) * 16, min(zs) * 16
w, h = (max(xs) - min(xs) + 1) * 16, (max(zs) - min(zs) + 1) * 16
scale = max(1, 768 // max(w, h))
img = Image.new("RGB", (w * scale, h * scale), (20, 24, 30))
d = ImageDraw.Draw(img)
for (x, z), name in tops.items():
    px, pz = (x - min_x) * scale, (z - min_z) * scale
    d.rectangle([px, pz, px + scale - 1, pz + scale - 1], fill=color(name))


def mark(x, z, fill, r=5, label=None):
    px, pz = (x - min_x) * scale, (z - min_z) * scale
    d.ellipse([px - r, pz - r, px + r, pz + r], fill=fill, outline=(0, 0, 0))
    if label:
        d.text((px + r + 2, pz - r - 2), label, fill=(255, 255, 255))


mark(state["spawn"][0], state["spawn"][2], (255, 255, 255), 4, "spawn")
for s in live:
    mark(s["pos"][0], s["pos"][2], (255, 140, 0), 3)
for p in players:
    mark(p["pos"][0], p["pos"][2], (230, 30, 30), 6, f"player {p['uuid'][:8]} (saved)")
img.save(out)
summary = {"world": state, "players": players, "explored_chunks": len(explored), "columns_rendered": len(tops),
           "distinct_top_blocks": sorted({n.split(':')[-1] for n in tops.values()}), "image": str(out), "image_px": img.size}
print(json.dumps(summary, indent=1))
