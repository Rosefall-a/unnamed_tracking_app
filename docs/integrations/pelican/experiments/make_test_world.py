"""Generates an identifiable test world with the stand-in server (outside Pelican).

usage: make_test_world.py <out_dir> <level_name> <seed> <marker_block> <x> <y> <z> [weather]
Produces <out_dir>/world/ and <out_dir>/<slug>.zip + .tar.gz with a known seed, level name,
marker structure and a saved player position for "UTPlayer".
"""
import hashlib
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

out, level, seed, block, x, y, z = sys.argv[1:8]
weather = sys.argv[8] if len(sys.argv) > 8 else "clear"
out = Path(out)
shutil.rmtree(out, ignore_errors=True)
out.mkdir(parents=True)
shutil.copy("/srv/pelican/standin/standin-server.jar", out / "server.jar")
(out / "server.properties").write_text("server-port=25565\nlevel-name=world\nmax-players=20\n")
name = f"utworld-{seed}"
subprocess.run(["docker", "rm", "-f", name], capture_output=True)
proc = subprocess.Popen(
    ["docker", "run", "--rm", "-i", "--name", name, "-p", "25598:25565", "-v", f"{out}:/data", "-w", "/data",
     "-e", f"UT_STANDIN_SEED={seed}", "-e", f"UT_STANDIN_LEVEL_NAME={level}",
     "mirror.gcr.io/library/eclipse-temurin:25-jdk-noble", "java", "-jar", "server.jar"],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
lines: list[str] = []
threading.Thread(target=lambda: [lines.append(l.rstrip()) for l in proc.stdout], daemon=True).start()


def wait_line(fragment: str, timeout: float = 60) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if any(fragment in l for l in lines):
            return
        time.sleep(0.2)
    raise TimeoutError(fragment)


def cmd(c: str) -> None:
    proc.stdin.write(c + "\n")
    proc.stdin.flush()


wait_line(")! For help, type ")
cmd(f"ut-marker {block}")
wait_line("built at pillar")
cmd(f"weather {weather}")
bot = subprocess.Popen(["node", "bot.js", "127.0.0.1", "25598", "UTPlayer", "5000"], cwd="/srv/pelican/standin/bot",
                       stdout=subprocess.PIPE, text=True)
wait_line("UTPlayer joined the game")
time.sleep(2)
cmd(f"tp UTPlayer {x} {y} {z}")
wait_line("Teleported UTPlayer")
print("bot:", bot.communicate(timeout=60)[0].strip())
wait_line("UTPlayer left the game")
cmd("save-all")
wait_line("Saved the game")
cmd("stop")
proc.wait(timeout=60)
print("\n".join(l for l in lines if "Marker" in l or "Level" in l or "Teleported" in l))
slug = level.lower().replace(" ", "-")
shutil.make_archive(str(out / slug), "zip", out, "world")
shutil.make_archive(str(out / slug), "gztar", out, "world")
for f in sorted(out.glob(f"{slug}.*")):
    print(f.name, f.stat().st_size, hashlib.sha256(f.read_bytes()).hexdigest())
print("files:", sorted(str(p.relative_to(out)) for p in (out / "world").rglob("*") if p.is_file()))
