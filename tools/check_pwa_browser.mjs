// Full browser + real Plugin Manager acceptance. No plugin API is mocked.
import assert from "node:assert/strict";
import { createServer, request as httpRequest } from "node:http";
import { readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { createRequire } from "node:module";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const [pluginsRoot] = process.argv.slice(2);
const require = createRequire(path.join(pluginsRoot, "package.json"));
const { chromium } = require("playwright");
const frontend = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../src/frontend/dist");
const server = createServer(async (incoming, outgoing) => {
  if (/^\/(?:api\/|pwa\/|service-worker\.js|manifest\.webmanifest)/.test(incoming.url)) {
    const upstream = httpRequest(new URL(incoming.url, process.env.PLUGIN_GATEWAY_URL), {
      method: incoming.method, headers: incoming.headers,
    }, response => { outgoing.writeHead(response.statusCode, response.headers); response.pipe(outgoing); });
    upstream.on("error", () => { outgoing.writeHead(503); outgoing.end(); });
    incoming.pipe(upstream);
    return;
  }
  const relative = decodeURIComponent(new URL(incoming.url, "http://localhost").pathname).slice(1);
  const file = path.resolve(frontend, relative.startsWith("assets/") ? relative : "index.html");
  if (!file.startsWith(frontend + path.sep)) { outgoing.writeHead(403); outgoing.end(); return; }
  try {
    outgoing.setHeader("Content-Type", ({ ".js": "text/javascript", ".css": "text/css", ".html": "text/html" })[path.extname(file)] || "application/octet-stream");
    outgoing.end(await readFile(file));
  } catch { outgoing.writeHead(404); outgoing.end(); }
});
await new Promise(resolve => server.listen(0, "127.0.0.1", resolve));
const origin = `http://127.0.0.1:${server.address().port}`;
const browser = await chromium.launch({ headless: true, args: ["--no-sandbox"] });
const context = await browser.newContext({ viewport: { width: 1280, height: 900 } });
// The disposable HTTPS catalogue points at a fixture branch which is never
// published. Map its public icon acquisition to the same real source bytes;
// host/plugin routes and browser service-worker infrastructure remain real.
await context.route("https://raw.githubusercontent.com/Rosefall-a/unnamed_tracking_app_plugins/integration-fixture/official/pwa/pwa/pwa-icon.svg", async route => {
  await route.fulfill({ contentType: "image/svg+xml", body: await readFile(path.join(process.env.PWA_ACCEPTANCE_ROOT, "official/pwa/pwa/pwa-icon.svg")) });
});
const page = await context.newPage();
const checkpoints = [];
async function checkpoint(name) {
  checkpoints.push(name);
  await writeFile(path.join(process.env.PWA_ACCEPTANCE_WORK, "pwa-conformance.json"), JSON.stringify({
    status: "running", package_version: "0.0.1", passed: checkpoints,
    limitation: "OS install surfaces and physical Android/iOS/Windows device testing require human devices.",
  }, null, 2));
  console.log(name);
}
async function api(method, route, expected = 200, options = {}) {
  const response = await context.request.fetch(origin + route, { method, ...options });
  assert.equal(response.status(), expected, `${route}: ${await response.text()}`);
  return response.status() === 204 ? null : await response.json();
}
const source = version => ({ url: `https://raw.githubusercontent.com/Rosefall-a/unnamed_tracking_app_plugins/integration-fixture/dist/official.pwa-${version}.utp`, source_type: "catalogue",
  catalogue_url: "https://raw.githubusercontent.com/Rosefall-a/unnamed_tracking_app_plugins/integration-fixture/list.json" });
const pluginPath = "/api/plugins/official.pwa";
const current = async () => (await api("GET", "/api/plugins")).find(item => item.plugin_id === "official.pwa");
const upload = async name => ({ file: { name: name + ".utp", mimeType: "application/octet-stream",
  buffer: await readFile(path.join(process.env.PWA_ACCEPTANCE_WORK, name + ".utp")) } });
const cacheKeys = () => page.evaluate(() => caches.keys());
async function reloadControlled() {
  const expected = await api("GET", "/pwa/status");
  assert.equal(expected.enabled, true);
  await page.goto(origin + "/");
  // A retired controller can remain attached while a replacement installs.
  // Require the live registration and its current neutral cache before offline launch.
  await page.waitForFunction(async generation => {
    const registration = await navigator.serviceWorker.getRegistration("/");
    if (!registration?.active || registration.installing || registration.waiting ||
        navigator.serviceWorker.controller !== registration.active) return false;
    const cached = await caches.match("/pwa/offline.html", { cacheName: "unnamed-tracking:pwa:" + generation });
    return !!cached?.ok;
  }, expected.generation, { timeout: 30000 });
}
try {
  await api("POST", "/api/auth/login", 200, { data: { username_or_email: process.env.PRIMARY_USER_USERNAME, password: process.env.PRIMARY_USER_PASSWORD } });
  await api("PATCH", "/api/preferences", 200, { data: { ui_welcome_completed: true } });
  const unsigned = await api("POST", "/api/plugins/install/preview", 200, { multipart: await upload("unsigned") });
  assert.equal(unsigned.publisher_channel, "unverified");
  assert.equal(unsigned.trust_status, "unsigned");
  await api("POST", "/api/plugins/install", 409, { multipart: await upload("unsigned") });
  await api("POST", "/api/plugins/install", 201, {
    params: { allow_untrusted: "true", confirm_dangerous: "true", approved_permissions: unsigned.permissions[0].key },
    multipart: { ...await upload("unsigned"), admin_password: process.env.PRIMARY_USER_PASSWORD },
  });
  assert.equal((await current()).trust.publisher_channel, "unverified");
  assert.equal((await api("GET", "/pwa/status")).enabled, true);
  await api("DELETE", pluginPath, 204);
  const invalid = await api("POST", "/api/plugins/install/preview", 200, { multipart: await upload("invalid") });
  assert.equal(invalid.installable, false);
  await api("POST", "/api/plugins/install", 400, { params: { allow_untrusted: "true" }, multipart: await upload("invalid") });
  await api("POST", "/api/plugins/install/preview", 400, { multipart: { file: { name: "malformed.utp", mimeType: "application/octet-stream", buffer: Buffer.from("invalid archive") } } });
  assert.equal((await api("GET", "/pwa/status")).enabled, false);
  await checkpoint("unsigned requires consent; bad signature cannot be overridden; malformed PWA package rejected before execution");
  await api("PATCH", "/api/plugins/catalogues/official", 200, { data: { enabled: false } });
  await api("POST", "/api/plugins/catalogues", 201, { data: { name: "PWA acceptance", url: source("0.0.1").catalogue_url } });
  const catalogue = await api("GET", "/api/plugins/catalog?source=" + encodeURIComponent(source("0.0.1").catalogue_url));
  assert.equal(catalogue[0].plugin_id, "official.pwa");
  const preview = await api("POST", "/api/plugins/install/preview-url", 200, { data: source("0.0.1") });
  assert.equal(preview.publisher_channel, "official");
  assert.equal(preview.signing_version, 2);
  assert.equal(preview.signature_verified, true);
  assert.equal(preview.permissions[0].capability, "frontend.pwa");
  await api("POST", "/api/plugins/install/url", 201, { data: source("0.0.1") });
  assert.equal((await api("GET", "/pwa/status")).enabled, false);
  await api("POST", pluginPath + "/permissions/grant", 200, { data: { approved_permissions: [preview.permissions[0].key], expected_digest: preview.package_digest } });
  assert.equal((await current()).status, "running");
  assert.equal((await current()).trust.publisher_channel, "official");
  await api("POST", pluginPath + "/permissions/revoke");
  assert.equal((await api("GET", "/pwa/status")).enabled, false);
  assert.equal((await context.request.get(origin + "/manifest.webmanifest")).status(), 404);
  await api("POST", pluginPath + "/permissions/grant", 200, { data: { approved_permissions: [preview.permissions[0].key], expected_digest: preview.package_digest } });
  assert.equal((await api("GET", "/pwa/status")).enabled, true);
  await checkpoint("discover → signed inspection → real installation → explicit site-wide permission → healthy worker");

  await reloadControlled();
  await page.goto(origin + "/settings?section=plugins");
  await page.getByText("Official · verified", { exact: true }).waitFor();
  await page.waitForFunction(() => [...document.querySelectorAll(".plugin img")].every(icon => icon.complete && icon.naturalWidth > 0));
  await page.screenshot({ path: path.join(process.env.PWA_ACCEPTANCE_WORK, "pwa-plugin-installed.png"), fullPage: true });
  const status1 = await api("GET", "/pwa/status");
  const manifest = await api("GET", "/manifest.webmanifest");
  assert.equal(manifest.scope, "/");
  assert.equal(manifest.start_url, "/?pwa=1");
  assert.equal(manifest.id, "/");
  for (const icon of manifest.icons) assert.equal((await context.request.get(origin + icon.src)).status(), 200);
  const cdp = await context.newCDPSession(page);
  const parsed = await cdp.send("Page.getAppManifest");
  assert.equal(parsed.url, origin + "/manifest.webmanifest");
  assert.ok(parsed.data.includes("Unnamed Tracking"));
  await page.evaluate(async () => { await caches.open("another-app-cache"); });
  const keys1 = await cacheKeys();
  assert.ok(keys1.includes("unnamed-tracking:pwa:" + status1.generation));
  await page.evaluate(async () => {
    const keys = await caches.keys();
    for (const key of keys.filter(key => key.startsWith("unnamed-tracking:pwa:"))) {
      const entries = await (await caches.open(key)).keys();
      if (entries.length !== 1 || !entries[0].url.endsWith("/pwa/offline.html")) throw new Error("Private or unexpected cache entry");
    }
  });
  await checkpoint("real frontend reload → official UI badge → browser parses root PWA manifest/icons → cache contains only neutral offline HTML");

  await api("PUT", "/api/branding", 200, { data: { app_name: "Weekend Archive" } });
  const logo = Buffer.from(await page.evaluate(() => {
    const canvas = document.createElement("canvas"); canvas.width = 64; canvas.height = 64;
    const context = canvas.getContext("2d"); context.fillStyle = "#a4520d"; context.fillRect(0, 0, 64, 64);
    return canvas.toDataURL("image/png").split(",")[1];
  }), "base64");
  await api("POST", "/api/branding/assets/logo", 200, { multipart: { file: { name: "review-logo.png", mimeType: "image/png", buffer: logo } } });
  const brandedStatus = await api("GET", "/pwa/status");
  assert.notEqual(brandedStatus.generation, status1.generation);
  const brandedManifest = await api("GET", "/manifest.webmanifest");
  assert.equal(brandedManifest.name, "Weekend Archive");
  assert.equal(brandedManifest.short_name, "Weekend Archive");
  for (const icon of brandedManifest.icons) {
    const response = await context.request.get(origin + icon.src);
    assert.equal(response.status(), 200);
    const bytes = await response.body();
    const size = Number(icon.sizes.split("x")[0]);
    assert.equal(bytes.readUInt32BE(16), size);
    assert.equal(bytes.readUInt32BE(20), size);
  }
  assert.equal((await context.request.get(origin + manifest.icons[0].src)).status(), 404);
  await api("POST", pluginPath + "/permissions/revoke");
  assert.equal((await context.request.get(origin + brandedManifest.icons[0].src)).status(), 404);
  assert.equal((await context.request.get(origin + "/manifest.webmanifest")).status(), 404);
  await api("POST", pluginPath + "/permissions/grant", 200, { data: { approved_permissions: [preview.permissions[0].key], expected_digest: preview.package_digest } });
  await api("DELETE", "/api/branding/assets/logo");
  await api("PUT", "/api/branding", 200, { data: { app_name: "Archive" } });
  assert.equal((await api("GET", "/pwa/status")).generation, status1.generation);
  await checkpoint("server branding changes real manifest and maskable icons; cache identity changes; revoked PWA grant still withdraws branded assets; restoring default restores package identity");
  await reloadControlled();

  // Hold the real status response to reproduce a browser prompt arriving
  // before asynchronous provider validation finishes.
  let releaseInstallStatus;
  const installStatusGate = new Promise(resolve => { releaseInstallStatus = resolve; });
  await page.route("**/pwa/status", async route => { await installStatusGate; await route.continue(); });
  await page.goto(origin + "/settings?section=app-installation");
  await page.getByRole("heading", { name: "Install on this device", exact: true }).waitFor();
  assert.equal(await page.locator('.pwa-status button').filter({ hasText: "Install" }).count(), 0, "No persistent install button covers the top bar");
  // Headless Chromium has no OS install surface. Exercise only the browser-prompt
  // event boundary; manifest, worker, permissions and installation state are real.
  await page.evaluate(() => {
    window.__pwaPromptCalled = false;
    const event = new Event("beforeinstallprompt", { cancelable: true });
    Object.assign(event, { prompt: async () => { window.__pwaPromptCalled = true; }, userChoice: Promise.resolve({ outcome: "accepted" }) });
    window.dispatchEvent(event);
  });
  const installButton = page.getByRole("button", { name: "Install Archive", exact: true });
  assert.equal(await installButton.count(), 0, "Installation stays hidden before provider validation");
  releaseInstallStatus();
  await page.unrouteAll({ behavior: "wait" });
  for (const width of [390, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    await page.waitForFunction(width => {
      const main = document.querySelector("#main-content");
      if (!main) return false;
      const margin = parseFloat(getComputedStyle(main).marginLeft);
      return width <= 760 ? main.classList.contains("phone-content") && margin < 1 : margin >= 256;
    }, width);
    const bounds = await page.locator(".installation-section").boundingBox();
    assert(bounds && bounds.x >= 0 && bounds.x + bounds.width <= width + 1, "Installation settings fit after responsive navigation settles");
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1), "Installation settings have no horizontal overflow");
    await page.screenshot({ path: path.join(process.env.PWA_ACCEPTANCE_WORK, `pwa-settings-install-${width}.png`), fullPage: true });
  }
  await installButton.click();
  assert(await page.evaluate(() => window.__pwaPromptCalled));
  assert(await installButton.isDisabled(), "Consumed prompt is not offered again");
  await checkpoint("Settings-based installation invokes the available browser prompt; no persistent top-bar install control");

  const appearanceBefore = await api("GET", "/api/preferences");
  try {
    const custom = {
      light: { background: "#f4f1f8", surface: "#ffffff", surface_alt: "#ece6f1", text: "#302437", muted: "#66576e", accent: "#70468a", success: "#216e3e", warning: "#855000", error: "#b42318", info: "#265a8b", purple: "#6951a2" },
      dark: { background: "#201827", surface: "#2a2132", surface_alt: "#35283e", text: "#f3edf8", muted: "#c0afcc", accent: "#ddb0fa", success: "#96d5a9", warning: "#f2c87a", error: "#ffa6a0", info: "#a2c8ef", purple: "#c6b5f1" },
    };
    for (const width of [320, 390, 1440]) {
      await page.setViewportSize({ width, height: 900 });
      for (const palette of ["orange", "green", "custom"]) {
        for (const mode of ["light", "dark"]) {
          await context.setOffline(false);
          await api("PATCH", "/api/preferences", 200, { data: { ui_theme: mode, ui_palette: palette, ui_custom_palette: custom } });
          await reloadControlled();
          await page.waitForFunction(({ mode, palette }) => {
            const value = JSON.parse(localStorage.getItem("ui-appearance") || "null");
            return value?.theme === mode && value?.palette === palette;
          }, { mode, palette });
          const online = await page.evaluate(() => ({ background: getComputedStyle(document.body).backgroundColor,
            color: getComputedStyle(document.documentElement).getPropertyValue("--ui-bg").trim() }));
          assert.equal(await page.locator('meta[name="theme-color"]').getAttribute("content"), online.color);
          await context.setOffline(true);
          await page.goto(origin + "/?pwa=palette");
          await page.getByRole("heading", { name: "Waiting for internet", exact: true }).waitFor();
          const offline = await page.evaluate(() => ({ background: getComputedStyle(document.body).backgroundColor,
            width: window.innerWidth, content: document.documentElement.scrollWidth,
            button: document.querySelector("#retry").getBoundingClientRect().height }));
          assert.equal(offline.background, online.background);
          assert(offline.content <= offline.width + 1);
          assert(offline.button >= 44);
          assert.equal(await page.locator('meta[name="theme-color"]').getAttribute("content"), online.color);
          if (width === 390 && palette === "custom") await page.screenshot({ path: path.join(process.env.PWA_ACCEPTANCE_WORK, `pwa-custom-offline-${mode}.png`) });
        }
      }
    }
    await context.setOffline(false);
    await api("PATCH", "/api/preferences", 200, { data: { ui_theme: "system", ui_palette: "green" } });
    await reloadControlled();
    await page.waitForFunction(() => JSON.parse(localStorage.getItem("ui-appearance") || "null")?.theme === "system");
    await context.setOffline(true);
    await page.goto(origin + "/?pwa=system");
    await page.getByRole("heading", { name: "Waiting for internet", exact: true }).waitFor();
    for (const colorScheme of ["light", "dark"]) {
      await page.emulateMedia({ colorScheme });
      await page.waitForFunction(mode => document.documentElement.dataset.theme === mode, colorScheme);
      assert.equal(await page.locator('meta[name="theme-color"]').getAttribute("content"), colorScheme === "light" ? "#f1f5f1" : "#141c18");
    }
    await page.evaluate(() => localStorage.setItem("ui-appearance", '{"version":1,"colors":{"dark":{"background":"url(https://invalid.test)"}}}'));
    await page.reload();
    await page.getByRole("heading", { name: "Waiting for internet", exact: true }).waitFor();
    assert.equal(await page.locator('meta[name="theme-color"]').getAttribute("content"), "#17191c");
  } finally {
    await context.setOffline(false);
    await page.emulateMedia({ colorScheme: "light" });
    await page.setViewportSize({ width: 1280, height: 900 });
    await api("PATCH", "/api/preferences", 200, { data: { ui_theme: appearanceBefore.ui_theme, ui_palette: appearanceBefore.ui_palette, ui_custom_palette: appearanceBefore.ui_custom_palette } });
    await reloadControlled();
  }
  await checkpoint("18 real online/offline width-palette-mode cases, custom browser bars, live System switching and invalid-cache fallback preserve the neutral PWA page");

  await context.setOffline(true);
  await page.goto(origin + "/?pwa=1");
  await page.getByRole("heading", { name: "Waiting for internet", exact: true }).waitFor();
  await page.screenshot({ path: path.join(process.env.PWA_ACCEPTANCE_WORK, "pwa-offline.png") });
  assert.equal(await page.evaluate(async () => { try { await fetch("/api/auth/me"); return "unexpected"; } catch { return "network failure"; } }), "network failure");
  await page.evaluate(async () => {
    for (const key of (await caches.keys()).filter(key => key.startsWith("unnamed-tracking:pwa:"))) {
      await (await caches.open(key)).delete("/pwa/offline.html");
    }
  });
  const missingCache = await page.goto(origin + "/?pwa=1");
  assert.equal(missingCache.status(), 503);
  await page.getByText("Waiting for internet. Reconnect and reload Unnamed Tracking.", { exact: true }).waitFor();
  await context.setOffline(false);
  await reloadControlled();
  await checkpoint("offline app launch → neutral reconnect page → private API fails offline → missing cache falls back safely → online full application returns");

  await writeFile(path.join(process.env.PWA_ACCEPTANCE_ROOT, "list.json"),
    await readFile(path.join(process.env.PWA_ACCEPTANCE_WORK, "catalogue-0.0.2.json")));
  await api("POST", pluginPath + "/update/preview-url", 200, { data: source("0.0.2") });
  await api("PUT", pluginPath + "/auto-update", 200, { data: { mode: "enabled" } });
  const automatic = execFileSync(process.env.PWA_ACCEPTANCE_PYTHON, [path.join(path.dirname(fileURLToPath(import.meta.url)), "check_plugin_repository_lifecycle.py"), "--mode", "automatic"], { env: process.env, encoding: "utf8" });
  assert.equal(JSON.parse(automatic.trim().split("\n").at(-1)).installed, 1);
  assert.equal((await current()).version, "0.0.2");
  await reloadControlled();
  const status2 = await api("GET", "/pwa/status");
  assert.notEqual(status2.generation, status1.generation);
  await page.waitForFunction(async generation => {
    const keys = await caches.keys();
    return keys.includes("unnamed-tracking:pwa:" + generation) && keys.filter(key => key.startsWith("unnamed-tracking:pwa:")).length === 1;
  }, status2.generation);
  assert.ok((await cacheKeys()).includes("another-app-cache"));
  assert.equal((await context.request.get(origin + manifest.icons[0].src)).status(), 404);
  await checkpoint("real automatic signed update → automatic worker replacement → owned cache migration → stale icon withdrawn → unrelated cache retained");

  const package3 = await readFile(path.join(process.env.PWA_ACCEPTANCE_ROOT, "dist/official.pwa-0.0.3.utp"));
  const failed = await context.request.put(origin + pluginPath + "/update", { multipart: { file: { name: "broken.utp", mimeType: "application/octet-stream", buffer: package3 } } });
  assert.equal(failed.status(), 200, await failed.text());
  assert.equal((await failed.json()).status, "rolled_back");
  assert.equal((await current()).version, "0.0.2");
  assert.equal((await api("GET", "/pwa/status")).generation, status2.generation);
  await api("PUT", pluginPath + "/update", 409, { multipart: { file: {
    name: "old.utp", mimeType: "application/octet-stream",
    buffer: await readFile(path.join(process.env.PWA_ACCEPTANCE_ROOT, "dist/official.pwa-0.0.1.utp")),
  } } });
  await checkpoint("failed real-worker update rolls back PWA provider/assets/grants; old version update rejected");

  await api("POST", pluginPath + "/disable");
  assert.equal((await api("GET", "/pwa/status")).enabled, false);
  assert.equal((await context.request.get(origin + "/manifest.webmanifest")).status(), 404);
  await page.goto(origin + "/?pwa=1");
  // Unregistration and CacheStorage deletion are independent asynchronous
  // browser operations. Observe both completed conditions before asserting
  // retirement, without deleting data or bypassing actual lifecycle behavior.
  await page.waitForFunction(async () =>
    !(await navigator.serviceWorker.getRegistrations()).length &&
    !(await caches.keys()).some(key => key.startsWith("unnamed-tracking:pwa:")),
  );
  assert.ok(!(await cacheKeys()).some(key => key.startsWith("unnamed-tracking:pwa:")));
  assert.ok((await cacheKeys()).includes("another-app-cache"));
  await page.getByText("PWA plugin is not enabled.", { exact: false }).waitFor();
  await page.screenshot({ path: path.join(process.env.PWA_ACCEPTANCE_WORK, "pwa-plugin-disabled.png") });
  await api("DELETE", pluginPath, 204);
  await writeFile(path.join(process.env.PWA_ACCEPTANCE_ROOT, "list.json"),
    await readFile(path.join(process.env.PWA_ACCEPTANCE_WORK, "catalogue-0.0.1.json")));
  await api("POST", "/api/plugins/install/url", 201, { params: { approved_permissions: preview.permissions[0].key }, data: source("0.0.1") });
  await reloadControlled();
  const reinstalled = await api("GET", "/pwa/status");
  assert.notEqual(reinstalled.generation, status1.generation);
  await checkpoint("disabled while browser PWA is installed → installability/cache/worker withdrawn → uninstall → reinstall receives fresh identity");

  execFileSync(process.env.PWA_ACCEPTANCE_PYTHON, [path.join(path.dirname(fileURLToPath(import.meta.url)), "check_pwa_lifecycle.py"), "--expire-session"], { env: process.env });
  await page.goto(origin + "/");
  await page.waitForURL(url => url.pathname === "/login");
  assert.ok([null, "/"].includes(new URL(page.url()).searchParams.get("return_to")),
    "Expired sessions return to sign-in with a safe local return target");
  assert.equal(new URL(page.url()).searchParams.get("return_to"), "/");
  const cacheEntries = await page.evaluate(async () => {
    const keys = await caches.keys();
    return (await Promise.all(keys.filter(key => key.startsWith("unnamed-tracking:pwa:")).map(async key => (await (await caches.open(key)).keys()).map(r => r.url)))).flat();
  });
  assert.ok(cacheEntries.every(url => url.endsWith("/pwa/offline.html")));
  await checkpoint("real API session expires → default login; credentials and private responses absent from caches");
  await api("POST", "/api/auth/login", 200, { data: { username_or_email: process.env.PRIMARY_USER_USERNAME, password: process.env.PRIMARY_USER_PASSWORD } });
  await api("DELETE", pluginPath, 204);
  const brokenInstall = await context.request.post(origin + "/api/plugins/install", { multipart: { file: { name: "broken.utp", mimeType: "application/octet-stream", buffer: package3 } } });
  assert.equal(brokenInstall.status(), 201, await brokenInstall.text());
  const brokenResult = await brokenInstall.json();
  assert.equal(brokenResult.healthy, false);
  assert.equal(brokenResult.status, "unhealthy");
  assert.notEqual((await current()).status, "running");
  assert.equal((await api("GET", "/pwa/status")).enabled, false);
  assert.equal((await context.request.get(origin + "/manifest.webmanifest")).status(), 404);
  await api("DELETE", pluginPath, 204);
  assert.equal(await current(), undefined);
  await checkpoint("failed initial worker startup is visibly unhealthy, exposes no PWA assets/provider, and uninstalls cleanly");
  await page.goto(origin + "/");
  await page.waitForFunction(async () => !(await navigator.serviceWorker.getRegistrations()).length);
  await writeFile(path.join(process.env.PWA_ACCEPTANCE_WORK, "pwa-conformance.json"), JSON.stringify({ status: "passed", package_version: "0.0.1", passed: checkpoints, limitation: "Native browser OS installation UI and physical device coverage remain manual." }, null, 2));
} finally {
  await browser.close();
  await new Promise(resolve => server.close(resolve));
}
