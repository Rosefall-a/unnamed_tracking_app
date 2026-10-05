// Real built frontend against the acceptance backend; no mocked API responses.
import assert from "node:assert/strict";
import { createServer, request as httpRequest } from "node:http";
import { readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const [pluginsRoot, phase] = process.argv.slice(2);
const require = createRequire(path.join(pluginsRoot, "package.json"));
const { chromium } = require("playwright");
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../src/frontend/dist");
const mime = { ".js": "text/javascript", ".css": "text/css", ".svg": "image/svg+xml", ".html": "text/html" };
const server = createServer(async (incoming, outgoing) => {
  if (incoming.url.startsWith("/api/")) {
    const upstream = httpRequest(new URL(incoming.url, process.env.PLUGIN_GATEWAY_URL), {
      method: incoming.method, headers: incoming.headers,
    }, (response) => {
      outgoing.writeHead(response.statusCode, response.headers);
      response.pipe(outgoing);
    });
    upstream.on("error", (error) => { outgoing.writeHead(502); outgoing.end(String(error)); });
    incoming.pipe(upstream);
    return;
  }
  let relative = decodeURIComponent(new URL(incoming.url, "http://localhost").pathname).replace(/^\//, "");
  if (!relative.startsWith("assets/")) relative = "index.html";
  const file = path.resolve(root, relative);
  if (!file.startsWith(root + path.sep)) { outgoing.writeHead(403); outgoing.end(); return; }
  try {
    outgoing.setHeader("Content-Type", mime[path.extname(file)] ?? "application/octet-stream");
    outgoing.end(await readFile(file));
  } catch { outgoing.writeHead(404); outgoing.end(); }
});
await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
const origin = `http://127.0.0.1:${server.address().port}`;
const browser = await chromium.launch({ headless: true, args: ["--no-sandbox"] });
const context = await browser.newContext({ viewport: { width: 1440, height: 1050 } });
const page = await context.newPage();
const errors = [];
page.on("pageerror", (error) => errors.push(String(error)));

const installed = [];
const snapshots = [];
const api = async (method, route, data, status = 200, apiContext = context) => {
  const response = await apiContext.request.fetch(origin + route, { method, ...(data ? { data } : {}) });
  assert.equal(response.status(), status, route + ": " + (response.status() === status ? "" : await response.text()));
  return status === 204 ? undefined : response.json();
};
async function install(id, catalogue, entries) {
  const entry = entries.find(item => item.plugin_id === id);
  assert(entry, "Actual signed catalogue contains " + id);
  const source = { url: entry.url, source_type: "catalogue", catalogue_url: catalogue.url };
  const preview = await api("POST", "/api/plugins/install/preview-url", source);
  assert(preview.installable);
  assert.equal(preview.signature_verified, true);
  assert.equal(preview.trust_status, "trusted");
  const query = new URLSearchParams();
  for (const permission of preview.permissions) query.append("approved_permissions", permission.key);
  await api("POST", "/api/plugins/install/url?" + query, { ...source,
    expected_digest: preview.sha256, confirm_dangerous: true,
    admin_password: process.env.PRIMARY_USER_PASSWORD }, 201);
  installed.push(id);
  const active = (await api("GET", "/api/plugins")).find(item => item.plugin_id === id);
  assert.equal(active.enabled, true);
  assert.equal(active.status, "running");
  return preview;
}
const palette = "plugin:example.theme-palettes:blue-hour";
const widget = "plugin:example.home-widgets:library-glance";
async function checkSidebarArea(area) {
  const more = page.getByRole("button", { name: "More", exact: true });
  const openMenu = page.getByRole("button", { name: "Open menu", exact: true });
  const opened = await more.count() > 0 || await openMenu.count() > 0;
  if (await more.count()) await more.click();
  else if (await openMenu.count()) await openMenu.click();
  try {
    for (const [label, expected] of [["Administration", area === "administration"], ["Preferences", area === "preferences"]])
      assert.equal((await page.locator(`[aria-label="${label}"]`).getAttribute("class")).split(/\s+/).includes("active"), expected);
  } finally {
    if (opened) await page.getByRole("button", { name: "Close menu", exact: true }).click();
  }
}
try {
  await api("POST", "/api/auth/login", { username_or_email: process.env.PRIMARY_USER_USERNAME, password: process.env.PRIMARY_USER_PASSWORD });
  const before = await api("GET", "/api/preferences");
  await api("PATCH", "/api/preferences", { ui_welcome_completed: true });
  const catalogues = await api("GET", "/api/plugins/catalogues");
  const catalogue = catalogues.find(item => item.name === "Acceptance");
  assert(catalogue);
  const entries = await api("GET", "/api/plugins/catalog?source=" + encodeURIComponent(catalogue.url));
  const themePreview = await install("example.theme-palettes", catalogue, entries);
  assert.deepEqual(themePreview.permissions.map(item => item.capability), ["frontend.themes", "frontend.native"]);
  assert.deepEqual(themePreview.permissions.map(item => item.risk), ["low", "critical"]);
  await install("example.home-widgets", catalogue, entries);
  await install("example.scoped-document-viewer", catalogue, entries);
  const theme = await api("GET", "/api/plugins/example.theme-palettes/ui");
  assert.deepEqual(theme.themes.map(item => item.id), ["blue-hour", "purple-blocks"]);
  assert.equal(theme.native_frontend.entry, "native/app.js");
  const nativeDocs = await api("GET", "/api/plugins/example.scoped-document-viewer/ui");
  assert(nativeDocs.native_frontend && nativeDocs.frontend, "Native configuration and opaque content renderer coexist");
  const game = await api("POST", "/api/game/create", { title: "The Manual of Suspiciously Specific Quests",
    folder_location: "appearance-documents-" + Date.now() }, 201);
  const uploaded = await context.request.post(origin + `/api/game/${game.id}/files/doc`, { multipart: {
    file: { name: "Quest handbook.txt", mimeType: "text/plain", buffer: Buffer.from("Welcome, adventurer.\n\n1. Read the handbook.\n2. Save your progress.\n3. Pet the suspiciously helpful dragon.\n\nThis document was uploaded through the native game attachment API.") },
  } });
  assert.equal(uploaded.status(), 200);
  assert.equal((await uploaded.json()).results[0].status, "saved");
  for (const width of [320, 390, 760, 1024, 1440, 1920]) {
    for (const mode of ["light", "dark"]) {
      await page.setViewportSize({ width, height: 1000 });
      await api("PATCH", "/api/preferences", { ui_theme: mode, ui_palette: "orange" });
      await page.goto(origin + "/settings?section=appearance");
      await page.locator("#ui-palette option[value='" + palette + "']").waitFor({ state: "attached" });
      await page.locator("#ui-palette").selectOption(palette);
      const paletteSaved = page.waitForResponse(response => response.url().endsWith("/api/preferences") && response.request().method() === "PATCH");
      await page.getByRole("button", { name: "Apply palette", exact: true }).click();
      assert.equal((await paletteSaved).status(), 200);
      await page.waitForFunction(({ mode, expected }) => document.documentElement.dataset.theme === mode &&
        getComputedStyle(document.documentElement).getPropertyValue("--ui-bg").trim() === expected,
        { mode, expected: theme.themes[0].colors[mode].background });
      const saved = await api("GET", "/api/preferences");
      assert.equal(saved.ui_palette, "custom");
      assert.deepEqual(saved.ui_custom_palette, theme.themes[0].colors);
      await page.reload();
      await page.waitForFunction(value => document.querySelector("#ui-palette")?.value === value, palette);
      assert.equal(await page.getByRole("button", { name: mode === "dark" ? "Dark preview" : "Light preview", exact: true }).getAttribute("aria-pressed"), "true");
      await page.goto(origin + "/settings?section=jellyfin-sync");
      await page.getByText("Jellyfin server URL", { exact: true }).waitFor();
      await page.locator("#jf-server_url").waitFor();
      await page.getByRole("navigation", { name: "Settings areas" }).getByRole("button", { name: "Account", exact: true }).getAttribute("class").then(value => assert(value.includes("active")));
      await checkSidebarArea("account");
      assert.equal(await page.locator("#jf-token").inputValue(), "", "Credential fields are empty in evidence");
      assert(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1));
      if ((width === 390 && mode === "dark") || (width === 1440 && mode === "light")) {
        const filename = `jellyfin-native-settings-${width}-${mode}.png`;
        await page.screenshot({ path: path.join(process.env.INTEGRATION_WORK_ROOT, filename), fullPage: true });
        snapshots.push(filename);
      }
      await page.goto(origin + "/settings?section=reader-settings");
      const native = page.locator("[data-native-document-settings]");
      await native.waitFor();
      await checkSidebarArea("administration");
      const save = native.getByRole("button", { name: "Save viewer settings", exact: true });
      await save.waitFor();
      await page.waitForFunction(() => !document.querySelector("[data-native-document-settings] input").disabled);
      const input = native.getByLabel("Maximum preview size (MiB)");
      await input.fill("12");
      await save.click();
      await native.getByText("Viewer settings saved.", { exact: true }).waitFor();
      const config = await api("POST", "/api/plugins/example.scoped-document-viewer/actions/load-settings", { values: {} });
      assert.equal(config.value, 12);
      const dimensions = await native.boundingBox();
      assert(dimensions && dimensions.x + dimensions.width <= width + 1);
      assert(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1));
      const saveBox = await save.boundingBox();
      assert(saveBox.height >= 44, JSON.stringify({ width, mode, saveBox,
        styles: await save.evaluate(button => ({ minHeight: getComputedStyle(button).minHeight,
          height: getComputedStyle(button).height, transform: getComputedStyle(button).transform,
          stylesheets: [...document.querySelectorAll('link[rel="stylesheet"]')].map(link => link.href) })) }));
      if ((width === 390 && mode === "dark") || (width === 1440 && mode === "light")) {
        const filename = `document-native-settings-${width}-${mode}.png`;
        await page.screenshot({ path: path.join(process.env.INTEGRATION_WORK_ROOT, filename), fullPage: true });
        snapshots.push(filename);
      }
      await page.goto(origin + "/plugins/example.scoped-document-viewer/documents");
      const iframe = page.locator(".frontend-shell iframe");
      await iframe.waitFor();
      assert.equal(await iframe.getAttribute("sandbox"), "allow-scripts");
      const frame = page.frameLocator(".frontend-shell iframe");
      await frame.getByRole("heading", { name: "Document reader", exact: true }).waitFor();
      await page.waitForFunction(expected => getComputedStyle(document.documentElement).getPropertyValue("--ui-bg").trim() === expected, theme.themes[0].colors[mode].background);
      const documentFrame = await iframe.elementHandle();
      const inner = await documentFrame.contentFrame();
      await inner.waitForFunction(({ mode, expected }) => document.documentElement.dataset.theme === mode &&
        getComputedStyle(document.documentElement).getPropertyValue("--ui-bg").trim() === expected,
        { mode, expected: theme.themes[0].colors[mode].background });
      await frame.locator("#documents button").filter({ hasText: "Suspiciously Specific Quests" }).click();
      await frame.locator("#viewer").getByText(/Pet the suspiciously helpful dragon/).waitFor();
      await page.waitForFunction(() => Number.parseFloat(document.querySelector(".frontend-shell iframe").style.height) > 600);
      assert.equal(await inner.evaluate(() => getComputedStyle(document.querySelector(".document-panel")).backgroundColor),
        await inner.evaluate(() => { const probe = document.createElement("span"); probe.style.color = "var(--ui-surface)";
          document.body.append(probe); const color = getComputedStyle(probe).color; probe.remove(); return color; }));
      if ((width === 390 && mode === "dark") || (width === 1440 && mode === "light")) {
        const filename = `document-browser-${width}-${mode}.png`;
        await page.screenshot({ path: path.join(process.env.INTEGRATION_WORK_ROOT, filename), fullPage: true });
        snapshots.push(filename);
      }
    }
  }
  await api("PATCH", "/api/preferences", { home_widgets: [widget], home_widget_config: { [widget]: { limit: 2 } } });
  for (const width of [390, 1440]) {
    await page.setViewportSize({ width, height: 1000 });
    await page.goto(origin + "/");
    const content = page.locator(`[data-widget-id="${widget}"]`);
    await content.locator(`[data-widget-layout="${width <= 760 ? "phone" : "desktop"}"]`).waitFor();
    assert.equal(await page.locator('iframe[src*="youtube"]').count(), 0, "Embedded media is never selected for capture");
    await content.getByRole("button", { name: "Customize Library glance", exact: true }).click();
    const options = page.getByRole("dialog", { name: "Customize Library glance", exact: true });
    await options.getByLabel("Number of games").fill("3");
    await options.getByRole("button", { name: "Save options", exact: true }).click();
    await options.waitFor({ state: "hidden" });
    assert.equal((await api("GET", "/api/preferences")).home_widget_config[widget].limit, 3);
  }
  const username = "widget-member-" + Date.now();
  const password = "Widget-account-review1!";
  await api("POST", "/api/auth/users", { username, email: username + "@example.invalid", password }, 201);
  const second = await browser.newContext();
  await api("POST", "/api/auth/login", { username_or_email: username, password }, 200, second);
  const memberBefore = await api("GET", "/api/preferences", undefined, 200, second);
  assert(!memberBefore.home_widgets.includes(widget));
  await api("PATCH", "/api/preferences", { home_widgets: [widget], home_widget_config: { [widget]: { limit: 1 } } }, 200, second);
  assert.equal((await api("GET", "/api/preferences")).home_widget_config[widget].limit, 3);
  assert.equal((await api("GET", "/api/preferences", undefined, 200, second)).home_widget_config[widget].limit, 1);
  await second.close();
  const selected = await api("GET", "/api/preferences");
  await api("POST", "/api/plugins/example.theme-palettes/permissions/revoke");
  await page.goto(origin + "/settings?section=appearance");
  await page.locator("#ui-palette").waitFor();
  assert.equal(await page.locator("#ui-palette option[value='" + palette + "']").count(), 0);
  assert.deepEqual((await api("GET", "/api/preferences")).ui_custom_palette, selected.ui_custom_palette);
  await api("POST", "/api/plugins/example.home-widgets/disable");
  await page.goto(origin + "/");
  const retained = page.locator(`[data-widget-id="${widget}"]`);
  await retained.locator(".widget-unavailable").waitFor();
  assert.equal(await retained.locator(".home-demo").count(), 0);
  assert.equal((await api("GET", "/api/preferences")).home_widget_config[widget].limit, 3);
  await api("POST", "/api/plugins/example.home-widgets/enable");
  await page.reload();
  await page.locator(`[data-widget-id="${widget}"] .home-demo`).waitFor();
  await api("PATCH", "/api/preferences", { ui_theme: before.ui_theme, ui_palette: before.ui_palette,
    ui_custom_palette: before.ui_custom_palette, home_widgets: before.home_widgets, home_widget_config: before.home_widget_config });
  // Actual keyboard focus is inside an installed opaque frontend, not the host.
  for (const [width, mode] of [[390, "dark"], [1440, "light"]]) {
    await page.setViewportSize({ width, height: 1050 });
    await api("PATCH", "/api/preferences", { ui_theme: mode });
    for (const [key, destination] of [["g", "/games"], ["u", "/upload"], ["o", "/notifications"]]) {
      await page.goto(origin + "/plugins/example.scoped-document-viewer/documents");
      const iframe = page.locator(".frontend-shell iframe"); await iframe.waitFor();
      const inner = await (await iframe.elementHandle()).contentFrame();
      await inner.getByRole("heading", { name: "Document reader", exact: true }).waitFor();
      await inner.locator("body").evaluate(body => { body.tabIndex = -1; body.focus(); });
      await page.keyboard.press("Alt+" + key); await page.waitForURL(origin + destination);
      await page.locator("h1").first().waitFor();
    }
    for (const [keys, name] of [["Control+k", "Search library"], ["?", "Keyboard shortcuts"]]) {
      await page.goto(origin + "/plugins/example.scoped-document-viewer/documents");
      const iframe = page.locator(".frontend-shell iframe"); await iframe.waitFor();
      const inner = await (await iframe.elementHandle()).contentFrame();
      await inner.getByRole("heading", { name: "Document reader", exact: true }).waitFor();
      await inner.locator("body").evaluate(body => { body.tabIndex = -1; body.focus(); });
      await page.keyboard.press(keys);
      const globalDialog = page.getByRole("dialog", { name, exact: true }); await globalDialog.waitFor();
      await page.keyboard.press("Escape"); await globalDialog.waitFor({ state: "hidden" });
      assert.equal(new URL(page.url()).pathname, "/plugins/example.scoped-document-viewer/documents");
    }
  }
  await page.goto(origin + "/plugins/example.scoped-document-viewer/documents");
  const guardIframe = page.locator(".frontend-shell iframe"); await guardIframe.waitFor();
  const shortcutFrame = await (await guardIframe.elementHandle()).contentFrame();
  await shortcutFrame.getByRole("heading", { name: "Document reader", exact: true }).waitFor();
  const postShortcut = key => shortcutFrame.evaluate(key => new Promise(resolve => {
    const requestId = "shortcut-guard-" + Math.random();
    const listener = event => { if (event.source === window.parent && event.data?.requestId === requestId) {
      window.removeEventListener("message", listener); resolve(event.data); } };
    window.addEventListener("message", listener);
    window.parent.postMessage({ type: "plugin-api-request", method: "plugin.shortcut", requestId, payload: { key } }, "*");
  }), key);
  assert.match((await postShortcut("../../settings?section=admin")).error, /Unknown host navigation shortcut/);
  await page.locator("#main-content").focus(); await page.keyboard.press("?");
  const shortcutHelp = page.getByRole("dialog", { name: "Keyboard shortcuts", exact: true }); await shortcutHelp.waitFor();
  await postShortcut("g"); assert.equal(new URL(page.url()).pathname, "/plugins/example.scoped-document-viewer/documents");
  assert.equal(await shortcutHelp.count(), 1); await page.keyboard.press("Escape");
  assert.deepEqual(errors, [], "Installed native and iframe UI have no runtime errors");
  await writeFile(path.join(process.env.INTEGRATION_WORK_ROOT, "plugin-appearance-conformance.json"), JSON.stringify({
    status: "passed", native_document_settings: true, opaque_document_reader: true, width_mode_cases: 12,
    opaque_frame_navigation_cases: 6, arbitrary_path_denied: true, host_dialog_guard: true,
    opaque_frame_global_dialog_cases: 4,
    independent_low_risk_theme_permission: true, personal_palette_copy_retained_on_revocation: true,
    personal_widget_options_two_accounts: true, widget_disable_restore: true, snapshots,
  }, null, 2) + "\n");
  console.log("Signed plugin palette/native document settings/opaque reader: 12 width-mode cases; account widgets and withdrawal passed");
} catch (error) {
  console.error("Appearance acceptance failed:", error);
  for (const frame of page.frames()) {
    console.error("Frame diagnostics:", await frame.locator("body").innerText().then(value => value.slice(0, 1800)).catch(() => "unavailable"));
  }
  console.error("Browser errors:", errors);
  throw error;
} finally {
  try {
    for (const id of installed.reverse()) {
      await api("DELETE", `/api/plugins/${id}`, undefined, 204);
    }
  } finally {
    await browser.close();
    await new Promise(resolve => server.close(resolve));
  }
}
