// Verify the built application against a disposable real backend, with no API mocks.
// Usage: UI_REVIEW_USERNAME=... UI_REVIEW_PASSWORD=... node tools/check_ui_redevelopment.mjs plugins-root evidence-root backend-url
import assert from "node:assert/strict";
import { createServer, request as httpRequest } from "node:http";
import { readFile, mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import { checkHomeWidgets } from "./check_home_widgets.mjs";
import { checkBrandingUi } from "./check_branding_ui.mjs";
import { checkDetailUi } from "./check_detail_ui.mjs";
import { checkPaletteUi } from "./check_palette_ui.mjs";
import { checkContentUi } from "./check_content_ui.mjs";
import { checkCompletionBadges } from "./check_completion_badges.mjs";
import { checkTopbarNavigation } from "./check_topbar_navigation.mjs";
import { checkSearchShortcuts } from "./check_search_shortcuts.mjs";
import { checkLibraryEditors } from "./check_library_editors.mjs";
import { checkAppearanceSettings } from "./check_appearance_settings.mjs";
import { checkStartupRecovery } from "./check_startup_recovery.mjs";
import { checkAppearanceWelcome } from "./check_appearance_welcome.mjs";
import { checkUploadUi } from "./check_upload_ui.mjs";
import { checkPluginDiscoveryUi } from "./check_plugin_discovery_ui.mjs";
import { checkPluginReviewUi } from "./check_plugin_review_ui.mjs";
import { checkLibraryWorkflows } from "./check_library_workflows.mjs";
import { checkMobileNavigation } from "./check_mobile_navigation.mjs";
import { checkQuickTour } from "./check_quick_tour.mjs";

const [pluginsRoot, evidenceRoot, backendUrl] = process.argv.slice(2);
const reviewStage = process.argv[5] ?? "shell";
assert(pluginsRoot && evidenceRoot && backendUrl && process.env.UI_REVIEW_USERNAME && process.env.UI_REVIEW_PASSWORD, "Supply a disposable backend and review credentials.");
const require = createRequire(path.resolve(pluginsRoot, "package.json"));
const { chromium, webkit } = require("playwright");
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../src/frontend/dist");
const mime = { ".js": "text/javascript", ".css": "text/css", ".svg": "image/svg+xml", ".html": "text/html" };
const server = createServer(async (incoming, outgoing) => {
  if (incoming.url.startsWith("/api/")) {
    const upstream = httpRequest(new URL(incoming.url, backendUrl), { method: incoming.method, headers: incoming.headers }, response => {
      outgoing.writeHead(response.statusCode, response.headers); response.pipe(outgoing);
    });
    upstream.on("error", error => { outgoing.writeHead(502); outgoing.end(String(error)); });
    incoming.pipe(upstream); return;
  }
  let relative = decodeURIComponent(new URL(incoming.url, "http://localhost").pathname).replace(/^\//, "");
  if (!relative.startsWith("assets/")) relative = "index.html";
  const file = path.resolve(root, relative);
  if (!file.startsWith(root + path.sep)) { outgoing.writeHead(403); outgoing.end(); return; }
  try { outgoing.setHeader("Content-Type", mime[path.extname(file)] ?? "application/octet-stream"); outgoing.end(await readFile(file)); }
  catch { outgoing.writeHead(404); outgoing.end(); }
});
await mkdir(evidenceRoot, { recursive: true });
await new Promise(resolve => server.listen(0, "127.0.0.1", resolve));
const origin = `http://127.0.0.1:${server.address().port}`;
const browserType = process.env.UI_REVIEW_BROWSER === "webkit" ? webkit : chromium;
const browser = await browserType.launch({ headless: true, ...(browserType === chromium ? { args: ["--no-sandbox"] } : {}) });
const errors = [];
const report = { backend: "real", passed: [], screens: [], widths: [320, 390, 430, 768, 1024, 1440, 1920, 2560] };
const admin = await browser.newContext();
const memberName = `ui-member-${Date.now()}`;
let memberId;
async function login(context, username, password) {
  const response = await context.request.post(origin + "/api/auth/login", { data: { username_or_email: username, password } });
  assert.equal(response.status(), 200, "Review login must succeed against the real server.");
  // General stages exercise a returning account. The welcome stage creates its own new accounts.
  assert.equal((await context.request.patch(origin + "/api/preferences", { data: { ui_welcome_completed: true } })).status(), 200);
}
async function checkOverflow(page, label) {
  const boundary = await page.evaluate(() => { const main = document.querySelector("#main-content") ?? document.querySelector("main"); return { width: window.innerWidth, document: document.documentElement.scrollWidth, main: main?.scrollWidth ?? 0, mainWidth: main?.clientWidth ?? 0 }; });
  assert(boundary.document <= boundary.width + 1, `${label}: document overflow ${JSON.stringify(boundary)}`);
  assert(boundary.main <= boundary.mainWidth + 1, `${label}: page overflow ${JSON.stringify(boundary)}`);
}
try {
  await login(admin, process.env.UI_REVIEW_USERNAME, process.env.UI_REVIEW_PASSWORD);
  const created = await admin.request.post(origin + "/api/auth/users", { data: { username: memberName, email: `${memberName}@example.invalid`, password: process.env.UI_REVIEW_PASSWORD, is_admin: false } });
  assert.equal(created.status(), 201);
  memberId = (await created.json()).id;
  // Evidence must never contain embedded media from installed plugins.
  const installed = await admin.request.get(origin + "/api/plugins");
  assert.equal(installed.status(), 200);
  assert.equal((await installed.json()).length, 0, "Run this stage against a clean plugin inventory to exclude embedded-media evidence.");
  if (reviewStage === "tour") {
    await checkQuickTour({ browser, admin, origin, evidenceRoot, report, checkOverflow });
    await writeFile(path.join(evidenceRoot, "guided-tour-conformance.json"), JSON.stringify(report, null, 2) + "\n");
    console.log(JSON.stringify({ cases: report.screens.length, passed: report.passed }, null, 2));
  } else if (reviewStage === "mobile-navigation") {
    await checkMobileNavigation({ admin, browser, origin, evidenceRoot, report, checkOverflow });
    await writeFile(path.join(evidenceRoot, "mobile-navigation-conformance.json"), JSON.stringify(report, null, 2) + "\n");
    console.log(JSON.stringify({ cases: report.screens.length, passed: report.passed }, null, 2));
  } else if (reviewStage === "library-workflows") {
    await checkLibraryWorkflows({ admin, origin, evidenceRoot, report, checkOverflow });
    await writeFile(path.join(evidenceRoot, "library-workflow-conformance.json"), JSON.stringify(report, null, 2) + "\n");
    console.log(JSON.stringify({ cases: report.screens.length, passed: report.passed }, null, 2));
  } else if (reviewStage === "plugin-discovery") {
    await checkPluginDiscoveryUi({ admin, origin, evidenceRoot, report, checkOverflow });
    await writeFile(path.join(evidenceRoot, "plugin-discovery-conformance.json"), JSON.stringify(report, null, 2) + "\n");
    console.log(JSON.stringify({ cases: report.screens.length, passed: report.passed }, null, 2));
  } else if (reviewStage === "plugin-review") {
    await checkPluginReviewUi({ admin, origin, evidenceRoot, report, checkOverflow });
    await writeFile(path.join(evidenceRoot, "plugin-review-conformance.json"), JSON.stringify(report, null, 2) + "\n");
    console.log(JSON.stringify({ cases: report.screens.length, passed: report.passed }, null, 2));
  } else if (reviewStage === "upload") {
    await checkUploadUi({ admin, origin, evidenceRoot, report, checkOverflow });
    await writeFile(path.join(evidenceRoot, "stage-upload-conformance.json"), JSON.stringify(report, null, 2) + "\n");
    console.log(JSON.stringify({ cases: report.screens.length, passed: report.passed }, null, 2));
  } else if (reviewStage === "welcome") {
    await checkAppearanceWelcome({ browser, admin, origin, evidenceRoot, report, checkOverflow });
    await writeFile(path.join(evidenceRoot, "stage-welcome-conformance.json"), JSON.stringify(report, null, 2) + "\n");
    console.log(JSON.stringify({ cases: report.screens.length, passed: report.passed }, null, 2));
  } else if (reviewStage === "palette" || reviewStage === "palette-editor") {
    const member = await browser.newContext(); await login(member, memberName, process.env.UI_REVIEW_PASSWORD);
    await checkPaletteUi({ admin, member, origin, evidenceRoot, report, pluginsRoot, editorOnly: reviewStage === "palette-editor" }); await member.close();
    await writeFile(path.join(evidenceRoot, "stage-palette-conformance.json"), JSON.stringify(report, null, 2) + "\n");
    console.log(JSON.stringify({ cases: report.screens.length, passed: report.passed }, null, 2));
  } else if (reviewStage === "startup") {
    await checkStartupRecovery({ browser, admin, origin, evidenceRoot, report, checkOverflow });
    await writeFile(path.join(evidenceRoot, "stage-startup-conformance.json"), JSON.stringify(report, null, 2) + "\n");
    console.log(JSON.stringify({ cases: report.screens.length, passed: report.passed }, null, 2));
  } else if (reviewStage === "appearance-settings") {
    await checkAppearanceSettings({ admin, origin, evidenceRoot, report, checkOverflow });
    await writeFile(path.join(evidenceRoot, "stage-settings-combined-conformance.json"), JSON.stringify(report, null, 2) + "\n");
    console.log(JSON.stringify({ cases: report.screens.length, passed: report.passed }, null, 2));
  } else if (reviewStage === "editors") {
    await checkLibraryEditors({ admin, origin, evidenceRoot, report, checkOverflow });
    await writeFile(path.join(evidenceRoot, "stage-editors-conformance.json"), JSON.stringify(report, null, 2) + "\n");
    console.log(JSON.stringify({ cases: report.screens.length, passed: report.passed }, null, 2));
  } else if (reviewStage === "search") {
    const member = await browser.newContext(); await login(member, memberName, process.env.UI_REVIEW_PASSWORD);
    await checkSearchShortcuts({ admin, member, origin, evidenceRoot, report, checkOverflow }); await member.close();
    await writeFile(path.join(evidenceRoot, "stage-search-conformance.json"), JSON.stringify(report, null, 2) + "\n");
    console.log(JSON.stringify({ cases: report.screens.length, passed: report.passed }, null, 2));
  } else if (reviewStage === "topbar") {
    await checkTopbarNavigation({ admin, origin, evidenceRoot, report, checkOverflow });
    await writeFile(path.join(evidenceRoot, "stage-topbar-conformance.json"), JSON.stringify(report, null, 2) + "\n");
    console.log(JSON.stringify({ cases: report.screens.length, passed: report.passed }, null, 2));
  } else if (reviewStage === "ribbon") {
    const member = await browser.newContext(); await login(member, memberName, process.env.UI_REVIEW_PASSWORD);
    await checkCompletionBadges({ admin, member, origin, evidenceRoot, report, checkOverflow }); await member.close();
    await writeFile(path.join(evidenceRoot, "stage-ribbon-conformance.json"), JSON.stringify(report, null, 2) + "\n");
    console.log(JSON.stringify({ cases: report.screens.length, passed: report.passed }, null, 2));
  } else if (reviewStage === "details") {
    const member = await browser.newContext(); await login(member, memberName, process.env.UI_REVIEW_PASSWORD);
    await checkDetailUi({ admin, member, origin, evidenceRoot, report, pluginsRoot }); await member.close();
    await writeFile(path.join(evidenceRoot, "stage-detail-conformance.json"), JSON.stringify(report, null, 2) + "\n");
    console.log(JSON.stringify({ cases: report.screens.length, passed: report.passed }, null, 2));
  } else if (reviewStage === "content") {
    const member = await browser.newContext();
    await login(member, memberName, process.env.UI_REVIEW_PASSWORD);
    await checkContentUi({ admin, member, origin, evidenceRoot, report, checkOverflow });
    await member.close();
    await writeFile(path.join(evidenceRoot, "stage-content-conformance.json"), JSON.stringify(report, null, 2) + "\n");
    console.log(JSON.stringify({ cases: report.screens.length, passed: report.passed }, null, 2));
  } else if (reviewStage === "branding") {
    const member = await browser.newContext();
    await login(member, memberName, process.env.UI_REVIEW_PASSWORD);
    await checkBrandingUi({ admin, member, browser, origin, evidenceRoot, report, checkOverflow });
    await member.close();
    await writeFile(path.join(evidenceRoot, "stage-branding-conformance.json"), JSON.stringify(report, null, 2) + "\n");
    console.log(JSON.stringify({ cases: report.screens.length, passed: report.passed }, null, 2));
  } else if (reviewStage === "home") {
    const member = await browser.newContext();
    await login(member, memberName, process.env.UI_REVIEW_PASSWORD);
    await checkHomeWidgets({ admin, member, origin, evidenceRoot, report, checkOverflow });
    await member.close();
    await writeFile(path.join(evidenceRoot, "stage-home-conformance.json"), JSON.stringify(report, null, 2) + "\n");
    console.log(JSON.stringify({ cases: report.screens.length, passed: report.passed }, null, 2));
  } else {
  for (const role of ["admin", "member"]) {
    const context = role === "admin" ? admin : await browser.newContext();
    if (role === "member") await login(context, memberName, process.env.UI_REVIEW_PASSWORD);
    const page = await context.newPage();
    page.on("pageerror", error => errors.push(String(error)));
    for (const theme of ["light", "dark"]) {
      const saved = await context.request.patch(origin + "/api/preferences", { data: { ui_theme: theme, ui_reduce_motion: false, ui_high_contrast: false, ui_density: "comfortable" } });
      assert.equal(saved.status(), 200);
      for (const width of report.widths) {
        await page.setViewportSize({ width, height: width <= 430 ? 880 : 1050 });
        let titleStyle;
        const screens = ["/settings", "/settings?area=account", "/settings?section=appearance", "/settings?section=profile", "/settings?section=interface", "/settings?section=admin"];
        for (const screen of screens) {
          await page.goto(origin + screen);
          await page.locator(".page-header h1").waitFor();
          await page.waitForFunction(expected => document.documentElement.dataset.theme === expected, theme);
          await page.waitForFunction(() => !document.querySelector('.navigation a[href="/"]')?.classList.contains("active"));
          if (screen.includes("appearance")) await page.getByLabel("Theme", { exact: true }).waitFor();
          const style = await page.locator(".page-header h1").evaluate(element => { const s = getComputedStyle(element); return [s.fontSize, s.fontWeight, s.lineHeight, s.letterSpacing]; });
          titleStyle ??= style;
          assert.deepEqual(style, titleStyle, `${role}/${theme}/${width}: Settings title styles must match.`);
          await checkOverflow(page, `${role}/${theme}/${width}/${screen}`);
          assert.equal(await page.getByRole("navigation", { name: "Settings areas", exact: true }).getByRole("button", { name: "Administration", exact: true }).count(), role === "admin" ? 1 : 0);
          if (role === "member") assert.equal(await page.getByText("Changes apply to the entire server.", { exact: false }).count(), 0);
          report.screens.push({ role, theme, width, screen });
        }
        if (width <= 430) {
          const more = page.getByRole("button", { name: "More", exact: true });
          await more.click();
          const menu = page.getByRole("dialog", { name: "Main navigation" });
          await menu.waitFor();
          assert.equal(await menu.getByRole("link", { name: "Administration", exact: true }).count(), role === "admin" ? 1 : 0);
          for (let i = 0; i < 24; i++) {
            await page.keyboard.press("Tab");
            assert(await menu.evaluate(element => element.contains(document.activeElement)), "Menu focus must stay inside the native modal.");
          }
          await checkOverflow(page, `phone menu/${width}`);
          if (role === "admin" && width === 390) await page.screenshot({ path: path.join(evidenceRoot, `stage-shell-mobile-navigation-${theme}.png`) });
          await page.keyboard.press("Escape");
          await menu.waitFor({ state: "hidden" });
          assert(await more.evaluate(element => element === document.activeElement), "Escape restores focus to More.");
          assert.equal(await page.locator(".app-content").evaluate(element => getComputedStyle(element).marginLeft), "0px");
        }
        if (role === "admin" && [390, 1024, 1440].includes(width)) {
          await page.goto(origin + "/settings?section=appearance");
          await page.getByLabel("Theme", { exact: true }).waitFor();
          await page.getByRole("button", { name: "Save", exact: true }).waitFor();
          await page.screenshot({ path: path.join(evidenceRoot, `stage-shell-appearance-${width}-${theme}.png`), fullPage: width > 430 });
        }
      }
    }
    if (role === "member") {
      assert.equal((await context.request.get(origin + "/api/auth/users")).status(), 403);
      await context.close();
    } else await page.close();
  }
  assert.equal((await admin.request.patch(origin + "/api/preferences", { data: { ui_theme: "dark", ui_reduce_motion: false } })).status(), 200);
  const page = await admin.newPage();
  await page.goto(origin + "/settings?section=appearance");
  await page.getByLabel("Theme", { exact: true }).selectOption("light");
  await page.getByText("Appearance saved", { exact: true }).waitFor();
  await page.reload();
  await page.waitForFunction(() => document.documentElement.dataset.theme === "light");
  assert.equal((await (await admin.request.get(origin + "/api/preferences")).json()).ui_theme, "light");
  await page.getByLabel("Reduce motion", { exact: true }).check();
  await page.getByText("Appearance saved", { exact: true }).waitFor();
  assert(await page.locator("html").evaluate(element => element.classList.contains("reduce-motion")));
  assert.deepEqual(errors, []);
  report.passed.push("192 real Settings screen/theme/width/role cases", "Uniform Settings titles", "Phone modal focus, Escape and focus restoration", "Zero phone sidebar offset", "Member administration UI hidden and API denied", "Persisted appearance and reduced motion", "No JavaScript errors or page overflow");
  await writeFile(path.join(evidenceRoot, "stage-shell-conformance.json"), JSON.stringify(report, null, 2) + "\n");
  console.log(JSON.stringify({ cases: report.screens.length, passed: report.passed }, null, 2));
  }
} finally {
  if (memberId) await admin.request.delete(origin + `/api/auth/users/${memberId}`);
  await browser.close();
  await new Promise(resolve => server.close(resolve));
}
