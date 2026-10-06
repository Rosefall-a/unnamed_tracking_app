// Use a disposable host with the reviewed CI PWA already installed.
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { createRequire } from "node:module";
import path from "node:path";

const [pluginsRoot, outputArgument, origin, cookiesFile, themesArgument] =
  process.argv.slice(2);
assert.ok(
  themesArgument,
  "Usage: check_production_pwa_ui.mjs <plugins> <output> <host-url> <admin-cookies> <theme-packages>",
);
assert.ok(
  process.env.PWA_ACCEPTANCE_ADMIN_PASSWORD,
  "Disposable administrator reauthentication is required for restoring the reviewed PWA grant",
);
const output = path.resolve(outputArgument),
  themes = path.resolve(themesArgument);
await mkdir(output, { recursive: true });
const require = createRequire(
  path.join(path.resolve(pluginsRoot), "package.json"),
);
const { chromium } = require("playwright");
const browser = await chromium.launch({
  headless: true,
  args: ["--no-sandbox"],
});
const context = await browser.newContext({
  viewport: { width: 1440, height: 1050 },
  colorScheme: "light",
});
await context.addCookies(
  JSON.parse(await readFile(cookiesFile, "utf8")).map(({ name, value }) => ({
    name,
    value,
    url: origin,
  })),
);
const page = await context.newPage(),
  errors = [],
  installedThemes = [],
  disabledDemos = [];
page.on("pageerror", (error) => errors.push(String(error)));
const plugin = "/api/plugins/official.pwa",
  prefix = "unnamed-tracking:pwa:",
  unrelated = "uta-review:unrelated-pwa-cache";
const expectedVersion = process.env.PWA_EXPECTED_VERSION ?? "0.0.4";
const report = {
  status: "running",
  host_source_head: process.env.PWA_HOST_HEAD ?? null,
  plugin_source_head: process.env.PWA_SOURCE_HEAD ?? null,
  plugin_package_sha256: process.env.PWA_PACKAGE_SHA256 ?? null,
  plugin_version: expectedVersion,
  theme_source_head: process.env.THEME_SOURCE_HEAD ?? null,
  limitation:
    "Headless browser validation exercises the install-event boundary; physical OS install surfaces remain manual.",
  passed: [],
  captures: [],
  themes: [],
};
async function request(method, route, data, expected = 200) {
  const response = await context.request.fetch(origin + route, {
    method,
    ...(data === undefined ? {} : { data }),
  });
  assert.equal(
    response.status(),
    expected,
    `${method} ${route}: HTTP ${response.status()}`,
  );
  return expected === 204 ? null : response.json();
}
function checkpoint(message) {
  report.passed.push(message);
  console.log(message);
}
async function save(name) {
  await page.waitForFunction(
    () => document.documentElement.scrollWidth <= innerWidth + 1,
    undefined,
    { timeout: 5000 },
  );
  await page.screenshot({ path: path.join(output, name) });
  report.captures.push(name);
}
async function waitBrowser(predicate, argument, timeout = 30000) {
  const deadline = performance.now() + timeout;
  do {
    try {
      if (await page.evaluate(predicate, argument)) return;
    } catch (error) {
      // A host upgrade can reload the controlled page between observations.
      if (!String(error).includes("Execution context was destroyed"))
        throw error;
    }
    await new Promise((resolve) => setTimeout(resolve, 200));
  } while (performance.now() < deadline);
  throw new Error(
    "Production browser state did not become ready before timeout",
  );
}
async function controlled() {
  const status = await request("GET", "/pwa/status");
  assert.equal(status.enabled, true);
  assert.equal(status.version, expectedVersion);
  await page.reload();
  await waitBrowser(async (generation) => {
    const registration = await navigator.serviceWorker.getRegistration("/");
    return (
      registration?.active?.state === "activated" &&
      !registration.installing &&
      !registration.waiting &&
      registration.active === navigator.serviceWorker.controller &&
      Boolean(
        await caches.match("/pwa/offline.html", {
          cacheName: "unnamed-tracking:pwa:" + generation,
        }),
      )
    );
  }, status.generation);
  return status;
}
async function retired() {
  await page.goto(
    origin + "/settings?area=preferences&section=app-installation",
  );
  await page.getByText("The PWA plugin is disabled", { exact: true }).waitFor();
  await waitBrowser(async (ownedPrefix) => {
    const registrations = await navigator.serviceWorker.getRegistrations();
    return (
      !registrations.some((item) =>
        [item.active, item.waiting, item.installing].some(
          (worker) =>
            worker &&
            new URL(worker.scriptURL).pathname === "/service-worker.js",
        ),
      ) && !(await caches.keys()).some((key) => key.startsWith(ownedPrefix))
    );
  }, prefix);
  assert.equal(
    await page.evaluate(
      async (name) =>
        Boolean(
          await caches.match("/pwa-unrelated-review", { cacheName: name }),
        ),
      unrelated,
    ),
    true,
  );
  assert.equal(
    (await context.request.get(origin + "/manifest.webmanifest")).status(),
    404,
  );
}
async function restoreGrant() {
  await request("POST", plugin + "/permissions/grant", {
    approved_permissions: ["frontend.pwa:v1"],
    allow_untrusted: true,
    confirm_dangerous: true,
    admin_password: process.env.PWA_ACCEPTANCE_ADMIN_PASSWORD,
  });
}
const original = await request("GET", "/api/preferences");
let permissionWithdrawn = false,
  pluginDisabled = false;
try {
  assert.equal((await request("GET", "/api/auth/me")).is_admin, true);
  const installed = (await request("GET", "/api/plugins")).find(
    (item) => item.plugin_id === "official.pwa",
  );
  assert.equal(installed?.version, expectedVersion);
  assert.equal(installed.status, "running");
  assert.deepEqual(await request("GET", "/api/themes/manage"), {
    default_theme: "native",
    themes: [],
  });
  if (process.env.PWA_HOST_UPGRADE_SIGNAL) {
    await page.goto(
      origin + "/settings?area=preferences&section=app-installation",
    );
    const before = await controlled();
    const oldPolicy = await page.evaluate(
      async (generation) =>
        (
          await caches.match("/pwa/offline.html", {
            cacheName: "unnamed-tracking:pwa:" + generation,
          })
        )?.headers.get("content-security-policy"),
      before.generation,
    );
    assert.ok(oldPolicy && !oldPolicy.includes("style-src 'self'"));
    await writeFile(
      process.env.PWA_HOST_UPGRADE_SIGNAL,
      JSON.stringify({
        generation: before.generation,
        version: before.version,
      }),
    );
    await waitBrowser(
      async (generation) => {
        try {
          const state = await (
            await fetch("/pwa/status", { cache: "no-store" })
          ).json();
          return state.enabled && state.generation !== generation;
        } catch {
          return false;
        }
      },
      before.generation,
      180000,
    );
    const after = await request("GET", "/pwa/status");
    assert.equal(after.version, before.version);
    await waitBrowser(
      async (values) => {
        const registration = await navigator.serviceWorker.getRegistration("/");
        const cached = await caches.match("/pwa/offline.html", {
          cacheName: "unnamed-tracking:pwa:" + values.after,
        });
        return (
          registration?.active === navigator.serviceWorker.controller &&
          cached?.headers
            .get("content-security-policy")
            ?.includes("style-src 'self'") &&
          !(await caches.keys()).includes(
            "unnamed-tracking:pwa:" + values.before,
          )
        );
      },
      { before: before.generation, after: after.generation },
      90000,
    );
    assert.equal((await request("GET", "/api/auth/me")).is_admin, true);
    report.host_upgrade = {
      previous_generation: before.generation,
      current_generation: after.generation,
      plugin_version: after.version,
    };
    await writeFile(
      path.join(output, "pwa-host-upgrade-conformance.json"),
      JSON.stringify(
        {
          status: "passed",
          ...report.host_upgrade,
          host_source_head: report.host_source_head,
          plugin_package_sha256: report.plugin_package_sha256,
        },
        null,
        2,
      ) + "\n",
    );
    checkpoint(
      "An already controlled PWA receives the new offline policy and retires its old cache after a host-only production upgrade; its plugin version and sign-in remain unchanged",
    );
  }
  for (const item of await request("GET", "/api/plugins")) {
    if (
      [
        "example.help-button",
        "example.ui-playground",
        "example.shortcut-playground",
      ].includes(item.plugin_id) &&
      item.enabled
    ) {
      await request("POST", `/api/plugins/${item.plugin_id}/disable`);
      disabledDemos.push(item.plugin_id);
    }
  }
  for (const id of ["official.forest", "example.purple-blocks"]) {
    const file = `${id}-1.0.0.utt`,
      bytes = await readFile(path.join(themes, file));
    const response = await context.request.post(
      origin + "/api/themes/install",
      {
        multipart: {
          file: { name: file, mimeType: "application/zip", buffer: bytes },
        },
      },
    );
    assert.equal(response.status(), 201);
    installedThemes.push(id);
    const entry = (await request("GET", "/api/themes/manage")).themes.find(
      (theme) => theme.id === id,
    );
    assert.equal(
      entry.digest,
      createHash("sha256").update(bytes).digest("hex"),
    );
    report.themes.push({ id, sha256: entry.digest });
  }
  await request("PATCH", "/api/preferences", {
    ui_welcome_completed: true,
    ui_theme_package: "official.forest",
    ui_theme: "light",
    ui_palette: "green",
  });
  await page.goto(
    origin + "/settings?area=preferences&section=app-installation",
  );
  await controlled();
  const manifest = await request("GET", "/manifest.webmanifest");
  assert.equal(manifest.scope, "/");
  assert.equal(manifest.start_url, "/?pwa=1");
  for (const icon of manifest.icons)
    assert.equal((await context.request.get(origin + icon.src)).status(), 200);
  await page
    .getByText("Installation is available with the PWA plugin", { exact: true })
    .waitFor();
  assert.equal(
    await page
      .locator(".pwa-status button")
      .filter({ hasText: "Install" })
      .count(),
    0,
  );
  // Headless Chromium lacks an OS prompt; only this browser-event boundary is supplied.
  await page.evaluate(() => {
    window.__reviewInstallCalls = 0;
    const event = new Event("beforeinstallprompt", { cancelable: true });
    event.prompt = async () => {
      window.__reviewInstallCalls++;
    };
    event.userChoice = Promise.resolve({ outcome: "accepted" });
    window.dispatchEvent(event);
  });
  const installButton = page.locator(".installation-card").getByRole("button", {
    name: /^Install /,
  });
  report.manifest_name = manifest.name;
  report.install_button = await installButton.innerText();
  await installButton.click();
  assert.equal(await page.evaluate(() => window.__reviewInstallCalls), 1);
  assert.equal(await installButton.isDisabled(), true);
  await save("pwa-production-settings-1440-light.png");
  await page.evaluate(async (name) => {
    const cache = await caches.open(name);
    await cache.put(
      "/pwa-unrelated-review",
      new Response("retain unrelated cache"),
    );
  }, unrelated);
  checkpoint(
    `Actual CI PWA ${expectedVersion} supplies the root worker, manifest and icons; installation is in Settings and consumes the browser event once`,
  );
  for (const [width, mode, id] of [
    [320, "light", "example.purple-blocks"],
    [390, "dark", "official.forest"],
    [768, "dark", "official.forest"],
    [1440, "dark", "example.purple-blocks"],
  ]) {
    await request("PATCH", "/api/preferences", {
      ui_theme: mode,
      ui_theme_package: id,
    });
    await page.setViewportSize({ width, height: width < 500 ? 800 : 1050 });
    const status = await controlled(),
      entry = report.themes.find((theme) => theme.id === id);
    await page.waitForFunction(
      (value) =>
        document.documentElement.dataset.themePackage === value.id &&
        document.documentElement.dataset.themeRevision === value.digest &&
        document.documentElement.dataset.theme === value.mode,
      { id, digest: entry.sha256, mode },
    );
    const cssPath = await page.evaluate(() =>
      localStorage.getItem("ui-theme-stylesheet"),
    );
    assert.ok(cssPath?.startsWith(`/api/themes/assets/${id}/${entry.sha256}/`));
    const css = await context.request.get(origin + cssPath);
    assert.equal(css.status(), 200);
    const cssBytes = await css.text();
    await waitBrowser(
      async (args) => {
        const cached = await caches.match(args.path, {
          cacheName: "unnamed-tracking:pwa:" + args.generation,
        });
        return cached?.ok && (await cached.text()) === args.css;
      },
      { path: cssPath, generation: status.generation, css: cssBytes },
    );
    const online = await page.evaluate(() => ({
      background: getComputedStyle(document.body).backgroundColor,
      color: getComputedStyle(document.body).color,
      bar: document.querySelector('meta[name="theme-color"]').content,
    }));
    if (width === 390) await save("pwa-production-settings-390-dark.png");
    await context.setOffline(true);
    await page.goto(origin + "/?pwa=1");
    await page.waitForFunction(
      (args) =>
        document.documentElement.dataset.themePackage === args.id &&
        document.documentElement.dataset.theme === args.mode &&
        getComputedStyle(document.body).backgroundColor === args.background,
      { id, mode, background: online.background },
    );
    assert.equal(
      await page.evaluate(() => getComputedStyle(document.body).color),
      online.color,
    );
    assert.deepEqual(
      await page.evaluate(() =>
        [
          "--ui-bg",
          "--ui-surface",
          "--ui-text",
          "--ui-dim",
          "--ui-accent",
          "--ui-on-accent",
        ].map((key) => document.documentElement.style.getPropertyValue(key)),
      ),
      ["", "", "", "", "", ""],
      "Loaded offline theme CSS owns its colors without inline palette overrides",
    );
    assert.equal(
      await page.locator('meta[name="theme-color"]').getAttribute("content"),
      online.bar,
    );
    assert.equal(
      await page.evaluate(async () => {
        try {
          await fetch("/api/auth/me");
          return true;
        } catch {
          return false;
        }
      }),
      false,
    );
    await save(`pwa-production-offline-${width}-${mode}.png`);
    await context.setOffline(false);
    await page.goto(
      origin + "/settings?area=preferences&section=app-installation",
    );
    await page
      .getByText("Installation is available with the PWA plugin", {
        exact: true,
      })
      .waitFor();
  }
  const cacheEntries = await page.evaluate(async (ownedPrefix) => {
    const entries = [];
    for (const name of await caches.keys())
      if (name.startsWith(ownedPrefix))
        for (const request of await (await caches.open(name)).keys())
          entries.push(new URL(request.url).pathname);
    return entries;
  }, prefix);
  assert.ok(cacheEntries.some((entry) => entry.endsWith(".css")));
  assert.ok(
    cacheEntries.every(
      (entry) =>
        entry === "/pwa/offline.html" ||
        /^\/api\/themes\/assets\/[a-z0-9][a-z0-9._-]{0,127}\/[a-f0-9]{64}\/.+\.css$/.test(
          entry,
        ),
    ),
  );
  report.cache_entries = cacheEntries;
  checkpoint(
    "Forest and Purple Blocks retain their exact public CSS and browser colors offline at phone, tablet and desktop widths; private APIs and metadata are absent from caches",
  );
  // Remove only the owned cached stylesheet to exercise a real offline load failure.
  const fallbackStatus = await controlled();
  await page.waitForFunction(
    () =>
      document.documentElement.dataset.themePackage ===
        "example.purple-blocks" &&
      document.documentElement.dataset.themeRevision?.length === 64 &&
      localStorage.getItem("ui-theme-stylesheet"),
  );
  const fallbackPath = await page.evaluate(() =>
    localStorage.getItem("ui-theme-stylesheet"),
  );
  await waitBrowser(
    async ({ prefix, generation, cssPath }) =>
      (await caches.match(cssPath, { cacheName: prefix + generation }))?.ok,
    { prefix, generation: fallbackStatus.generation, cssPath: fallbackPath },
  );
  // Immutable CSS also lives in Chromium's HTTP cache. Clear that independent
  // cache so this probe actually reaches the offline stylesheet error path.
  const network = await context.newCDPSession(page);
  await network.send("Network.clearBrowserCache");
  await network.detach();
  await context.setOffline(true);
  assert(
    await page.evaluate(
      async ({ prefix, generation, cssPath }) =>
        (await caches.open(prefix + generation)).delete(cssPath),
      { prefix, generation: fallbackStatus.generation, cssPath: fallbackPath },
    ),
  );
  assert.equal(
    await page.evaluate(
      async ({ prefix, generation, cssPath }) =>
        Boolean(
          await caches.match(cssPath, { cacheName: prefix + generation }),
        ),
      { prefix, generation: fallbackStatus.generation, cssPath: fallbackPath },
    ),
    false,
  );
  await page.goto(origin + "/?pwa=1");
  await page.waitForFunction(
    () =>
      document.documentElement.dataset.themePackage === "native" &&
      document.documentElement.style.getPropertyValue("--ui-bg") === "#141c18",
  );
  await save("pwa-production-missing-theme-fallback-1440-dark.png");
  await context.setOffline(false);
  await page.goto(
    origin + "/settings?area=preferences&section=app-installation",
  );
  await controlled();
  assert.equal(
    (await request("GET", "/api/preferences")).ui_theme_package,
    "example.purple-blocks",
  );
  checkpoint(
    "A missing cached theme stylesheet restores retained native colors offline without changing the account's theme selection",
  );
  await request("POST", plugin + "/disable");
  pluginDisabled = true;
  await retired();
  await request("POST", plugin + "/enable");
  pluginDisabled = false;
  await controlled();
  checkpoint(
    "Disabling the PWA withdraws installability, its worker and its public theme cache while retaining unrelated caches; enabling restores a controlled app",
  );
  await request("POST", plugin + "/permissions/revoke");
  permissionWithdrawn = true;
  await retired();
  await restoreGrant();
  permissionWithdrawn = false;
  await controlled();
  assert.deepEqual(errors, []);
  checkpoint(
    "Withdrawing and explicitly restoring the reviewed site-wide permission retires and restores the production worker without browser exceptions",
  );
  report.status = "passed";
} catch (error) {
  report.status = "failed";
  report.failure_appearance = await page
    .evaluate(() => ({
      theme: document.documentElement.dataset.theme,
      theme_package: document.documentElement.dataset.themePackage,
      palette: document.documentElement.dataset.palette,
      inline_background:
        document.documentElement.style.getPropertyValue("--ui-bg"),
      computed_background: getComputedStyle(document.body).backgroundColor,
      saved_appearance: JSON.parse(
        localStorage.getItem("ui-appearance") || "null",
      ),
    }))
    .catch(() => null);
  await context.setOffline(false);
  await page.screenshot({
    path: path.join(output, "pwa-production-private-failure.png"),
  });
  throw error;
} finally {
  await context.setOffline(false);
  if (permissionWithdrawn) await restoreGrant();
  if (pluginDisabled) await request("POST", plugin + "/enable");
  for (const id of installedThemes.reverse())
    await request("DELETE", `/api/themes/${id}`, undefined, 204);
  await request("PATCH", "/api/preferences", original);
  for (const id of disabledDemos)
    await request("POST", `/api/plugins/${id}/enable`);
  await page.evaluate(async (name) => {
    await caches.delete(name);
  }, unrelated);
  await writeFile(
    path.join(output, "pwa-production-conformance.json"),
    JSON.stringify(report, null, 2) + "\n",
  );
  await browser.close();
}
