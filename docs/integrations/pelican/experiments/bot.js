// Headless test client (mineflayer, protocol 26.1) used to observe/verify worlds.
// usage: node bot.js <host> <port> <username> [stayMs]
// Prints one JSON line describing what the player sees: position, dimension, time, weather,
// and the marker blocks at the pillar (0,*,0) and pad (16,*,16) columns.
const mineflayer = require('mineflayer');
const [host, port, username, stayMs] = [process.argv[2], +process.argv[3], process.argv[4] || 'UTPlayer', +(process.argv[5] || 4000)];
const bot = mineflayer.createBot({ host, port, username, auth: 'offline', version: '26.1' });
const fail = setTimeout(() => { console.log(JSON.stringify({ ok: false, error: 'timeout' })); process.exit(2); }, 60000);
function column(x, z) {
  for (let y = 140; y > 40; y--) {
    const b = bot.blockAt(bot.entity.position.offset(0, 0, 0).set(x, y, z));
    if (b && b.name !== 'air' && b.name !== 'water') return { y, name: b.name };
  }
  return null;
}
bot.once('spawn', async () => {
  await bot.waitForChunksToLoad().catch(() => {});
  await new Promise((r) => setTimeout(r, 1500));
  const p = bot.entity.position;
  const report = {
    ok: true, username, uuid: bot.player && bot.player.uuid, version: bot.version,
    position: { x: +p.x.toFixed(2), y: +p.y.toFixed(2), z: +p.z.toFixed(2) },
    dimension: bot.game.dimension, timeOfDay: bot.time.timeOfDay, raining: bot.isRaining,
    pillarTop: column(0, 0), padTop: column(16, 16),
    onlinePlayers: Object.keys(bot.players),
  };
  console.log(JSON.stringify(report));
  // Optional: wait for the server to teleport us next to the markers, then scan again.
  if (process.argv[6] === 'rescan') {
    await new Promise((r) => { bot.once('forcedMove', r); setTimeout(r, 15000); });
    await new Promise((r) => setTimeout(r, 2500));
    const q = bot.entity.position;
    console.log(JSON.stringify({ ok: true, rescan: true, position: { x: +q.x.toFixed(2), y: +q.y.toFixed(2), z: +q.z.toFixed(2) },
      pillarTop: column(0, 0), padTop: column(16, 16) }));
  }
  setTimeout(() => { clearTimeout(fail); bot.quit(); setTimeout(() => process.exit(0), 500); }, stayMs);
});
bot.on('kicked', (r) => { console.log(JSON.stringify({ ok: false, kicked: r })); process.exit(3); });
bot.on('error', (e) => { console.log(JSON.stringify({ ok: false, error: e.message })); process.exit(1); });
