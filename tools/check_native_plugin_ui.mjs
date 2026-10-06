// Run only against an owned disposable production host with current CI plugins.
import assert from "node:assert/strict";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { createRequire } from "node:module";
import path from "node:path";

const [pluginsRoot, outputArgument, origin, cookiesFile] =
  process.argv.slice(2);
assert.ok(
  cookiesFile,
  "Usage: check_native_plugin_ui.mjs <plugins> <output> <host-url> <admin-cookies>",
);
const require = createRequire(path.resolve(pluginsRoot, "package.json"));
const { chromium } = require("playwright");
const output = path.resolve(outputArgument);
await mkdir(output, { recursive: true });
const missing = process.env.NATIVE_GATEWAY_STATE === "missing";
const report = {
  status: "running",
  host_source_head: process.env.NATIVE_HOST_HEAD ?? null,
  gateway_state: missing ? "missing" : "configured",
  checks: [],
  captures: [],
};
if (process.env.NATIVE_PACKAGE_REPORT) {
  const provenance = JSON.parse(
    await readFile(process.env.NATIVE_PACKAGE_REPORT, "utf8"),
  );
  report.companion_source_head = provenance.companion_head;
  report.real_downloaded_ci_packages = provenance.real_downloaded_ci_packages;
  report.packages = provenance.packages;
}
const browser = await chromium.launch({
  headless: true,
  args: ["--no-sandbox"],
});
const context = await browser.newContext();
const cookies = JSON.parse(await readFile(cookiesFile, "utf8"));
await context.addCookies(
  cookies.map(({ name, value }) => ({ name, value, url: origin })),
);
const api = async (method, route, data) => {
  const response = await context.request.fetch(origin + "/api" + route, {
    method,
    ...(data ? { data } : {}),
  });
  assert.equal(response.status(), 200, route + " status " + response.status());
  return response.json();
};
const saved = await api("GET", "/preferences");
const installed = await api("GET", "/plugins");
const disabled = [];
const page = await context.newPage(),
  errors = [];
page.on("pageerror", (error) => errors.push(String(error)));
const capture = async (filename) => {
  await page.screenshot({ path: path.join(output, filename) });
  report.captures.push(filename);
};
const fit = async (label) => {
  const dimensions = await page.evaluate(() => ({
    width: innerWidth,
    scroll: document.documentElement.scrollWidth,
    sidebarWidth: document.querySelector(".nav-scroll")?.clientWidth,
    sidebarScroll: document.querySelector(".nav-scroll")?.scrollWidth,
  }));
  assert.ok(
    dimensions.scroll <= dimensions.width + 1,
    label + " page overflow",
  );
  if (dimensions.sidebarWidth)
    assert.ok(
      dimensions.sidebarScroll <= dimensions.sidebarWidth + 1,
      label + " sidebar overflow",
    );
};
const checks = [
  [
    "administration",
    "jellyfin-admin",
    '[data-testid="jf-admin"]',
    "official.jellyfin-media-sync",
    "get-config",
    "Jellyfin servers",
  ],
  [
    "account",
    "jellyfin-accounts",
    ".jf-official.jf-sync",
    "official.jellyfin-media-sync",
    "get-config",
    "Your Jellyfin accounts",
  ],
  [
    "preferences",
    "reader-settings",
    "[data-native-document-settings]",
    "example.scoped-document-viewer",
    null,
    "Document Browser",
  ],
  [
    "account",
    "sessions",
    ".ssm",
    "example.self-service-session-manager",
    "list-sessions",
    "Sessions",
  ],
  [
    "administration",
    "admin-sessions",
    ".ssm",
    "example.self-service-session-manager",
    "list-admin-sessions",
    "Session Manager",
  ],
];
try {
  for (const item of installed) {
    if (
      item.enabled &&
      [
        "example.help-button",
        "example.ui-playground",
        "example.shortcut-playground",
      ].includes(item.plugin_id)
    ) {
      await api("POST", "/plugins/" + item.plugin_id + "/disable");
      disabled.push(item.plugin_id);
    }
  }
  report.layout_demo_overlays_disabled = disabled;
  for (const [width, theme] of missing
    ? [
        [320, "light"],
        [1440, "dark"],
      ]
    : [
        [320, "light"],
        [390, "dark"],
        [1440, "light"],
        [1920, "dark"],
      ]) {
    await page.setViewportSize({ width, height: 1000 });
    await api("PATCH", "/preferences", {
      ui_theme: theme,
      ui_palette: "green",
    });
    if (missing) {
      await page.goto(origin + "/settings?area=administration&section=plugins");
      await page
        .getByText("Plugin pages cannot reach the app", { exact: true })
        .waitFor();
      const warning = page.locator(".gateway-warning");
      assert.match(await warning.innerText(), /PLUGIN_GATEWAY_URL/);
      assert.equal(
        await page.locator(".manager-settings").first().getAttribute("open"),
        "",
      );
      await warning.scrollIntoViewIfNeeded();
      await fit("Gateway warning " + width);
      await capture(`gateway-missing-manager-${width}-${theme}.png`);
    }
    for (const [area, section, marker, plugin, action, title] of checks) {
      if (missing && !action) continue;
      const response = action
        ? page.waitForResponse(
            (reply) =>
              new URL(reply.url()).pathname ===
                `/api/plugins/${plugin}/actions/${action}` &&
              reply.request().method() === "POST",
            { timeout: 60000 },
          )
        : null;
      await page.goto(origin + `/settings?area=${area}&section=${section}`);
      const activeMarker =
        missing && plugin === "official.jellyfin-media-sync"
          ? ".jf-official"
          : marker;
      await page.locator(activeMarker).waitFor({ timeout: 60000 });
      if (response) {
        const loaded = await response;
        assert.equal(loaded.status(), missing ? 503 : 200, title);
        if (missing) {
          await page
            .locator(activeMarker)
            .getByText(/PLUGIN_GATEWAY_URL/)
            .first()
            .waitFor();
        }
      }
      if (!missing) {
        await page
          .locator(marker)
          .getByText(/Loading(?:\.{3}|…)?/)
          .waitFor({ state: "hidden" });
        assert.equal(
          await page.locator(marker + " [role=alert]:visible").count(),
          0,
          title + " native error",
        );
        if (section === "jellyfin-accounts")
          await page
            .getByRole("button", { name: "Sign in", exact: true })
            .waitFor();
        if (section === "reader-settings")
          await page
            .getByRole("button", { name: "Save viewer settings", exact: true })
            .waitFor();
        if (width >= 1440 && section !== "reader-settings") {
          const group = page.locator(".settings-nav-group").filter({
            has: page.getByText(
              area === "account" ? "Account" : "Server management",
              { exact: true },
            ),
          });
          const entry = group.getByRole("button", { name: title, exact: true });
          assert.ok(await entry.isVisible(), title + " direct setting entry");
          assert.equal(
            await entry.locator("xpath=ancestor::details").count(),
            0,
          );
        }
      }
      await fit(title + " " + width);
      await capture(
        `${missing ? "gateway-missing" : "native-current"}-${section}-${width}-${theme}.png`,
      );
    }
  }
  if (!missing) {
    await page.setViewportSize({ width: 1440, height: 1000 });
    await page.goto(origin + "/settings?area=account&section=collector-import");
    const entry = page
      .locator(".settings-nav-group")
      .getByRole("button", { name: "Collector's Archive", exact: true });
    await entry.waitFor({ timeout: 60000 });
    assert.equal(await entry.locator("xpath=ancestor::details").count(), 0);
    const games = page.getByRole("button", { name: "Games", exact: true });
    if ((await games.getAttribute("aria-expanded")) !== "true")
      await games.click();
    for (const label of ["Cards", "Sets", "Bounties"]) {
      const link = page
        .locator("#nav-games")
        .getByRole("link", { name: label, exact: true });
      assert.ok(await link.isVisible(), label + " direct Games entry");
      assert.equal(await link.locator("xpath=ancestor::details").count(), 0);
    }
    await fit("Archive placement");
    await capture("native-current-archive-placement-1440-dark.png");
    report.checks.push(
      "Current native Jellyfin, Session Manager and Document Browser settings load without API/action errors at 320/390/1440/1920; account/admin entries are direct, Archive is flat under Games and Account, and pages/sidebar fit.",
    );
  } else {
    report.checks.push(
      "Real missing production callback produces prominent manager guidance and inline 503 errors on native Jellyfin and Session Manager pages at 320/1440; no invalid-action 422 or hidden main-page message.",
    );
  }
  assert.deepEqual(errors, []);
  report.status = "passed";
  console.log(report.checks[0]);
} catch (error) {
  report.status = "failed";
  await capture("native-current-private-failure.png");
  throw error;
} finally {
  await api("PATCH", "/preferences", saved);
  for (const id of disabled) await api("POST", "/plugins/" + id + "/enable");
  await browser.close();
  await writeFile(
    path.join(
      output,
      missing
        ? "native-missing-gateway-conformance.json"
        : "native-current-conformance.json",
    ),
    JSON.stringify(report, null, 2) + "\n",
  );
}
