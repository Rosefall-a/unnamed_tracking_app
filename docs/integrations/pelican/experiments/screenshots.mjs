// Captures Pelican UI evidence for the discovery record. Reads passwords from the secrets dir at
// runtime; never visits API-key or token pages. usage: node screenshots.mjs <out_dir> <mc_server> <luanti_server>
import { chromium } from 'playwright';
import { readFileSync, mkdirSync } from 'node:fs';

const [outDir, mc, luanti] = process.argv.slice(2);
const PANEL = process.env.PELICAN_URL || 'http://127.0.0.1:8000';
const secret = (n) => readFileSync(`/srv/pelican/secrets/${n}.password`, 'utf8').trim();
mkdirSync(outDir, { recursive: true });

const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });

async function session(user, password) {
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, colorScheme: 'dark' });
  const page = await ctx.newPage();
  await page.goto(`${PANEL}/login`);
  await page.locator('input[type="text"], input[type="email"]').first().fill(user);
  await page.locator('input[type="password"]').fill(password);
  await page.locator('button[type="submit"]').click();
  await page.waitForLoadState('networkidle');
  return { ctx, page };
}

async function shot(page, path, name, wait = 2500) {
  await page.goto(`${PANEL}${path}`);
  await page.waitForLoadState('networkidle').catch(() => {});
  await page.waitForTimeout(wait);
  await page.screenshot({ path: `${outDir}/${name}.png` });
  console.log('captured', name, path);
}

const player = await session('utplayer', secret('utplayer'));
await shot(player.page, '/', '01-player-dashboard-servers');
await shot(player.page, `/server/${mc}/console`, '02-minecraft-console-running-player-joined', 6000);
await shot(player.page, `/server/${mc}/files`, '03-minecraft-files-world-custody-marker');
await shot(player.page, `/server/${mc}/backups`, '04-minecraft-backups-captures');
await shot(player.page, `/server/${mc}/subusers`, '05-minecraft-subuser-bridge-identity');
await shot(player.page, `/server/${luanti}/console`, '06-luanti-console-running', 5000);
await player.ctx.close();

const admin = await session('utadmin', secret('admin'));
await shot(admin.page, '/admin/servers', '07-admin-servers-external-ids');
await admin.ctx.close();
await browser.close();
