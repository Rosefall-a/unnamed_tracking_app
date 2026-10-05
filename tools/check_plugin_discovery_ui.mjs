// Responsive discovery and acquisition against real catalogue/review endpoints.
import assert from "node:assert/strict";
import path from "node:path";

export async function checkPluginDiscoveryUi({ admin, origin, evidenceRoot, report, checkOverflow }) {
  const original = await (await admin.request.get(origin + "/api/preferences")).json();
  const page = await admin.newPage(), errors = [];
  page.on("pageerror", error => errors.push(String(error)));
  try {
    for (const theme of ["light", "dark"]) for (const width of [320, 390, 760, 1024, 1440, 1920]) {
      assert.equal((await admin.request.patch(origin + "/api/preferences", { data: { ui_theme: theme } })).status(), 200);
      await page.setViewportSize({ width, height: 1050 });
      await page.goto(origin + "/settings?section=plugins");
      const launcher = page.getByRole("button", { name: "Install a plugin", exact: true });
      await launcher.waitFor();
      await page.waitForFunction(mode => document.documentElement.dataset.theme === mode, theme);
      await launcher.click();
      assert.equal(await page.getByRole("dialog").count(), 0, "Discovery is a direct page view");
      await page.getByRole("button", { name: "Discover", exact: true }).waitFor();
      await page.getByRole("combobox", { name: "Filter by plugin source", exact: true }).selectOption("demo");
      await page.getByRole("searchbox", { name: "Filter plugins", exact: true }).fill("Jellyfin");
      const card = page.locator("article.plugin").filter({ has: page.getByRole("heading", { name: /Jellyfin/ }) });
      await card.waitFor();
      assert.equal(await page.getByRole("heading", { name: "Example plugins", exact: true }).count(), 1);
      assert.equal(await page.getByRole("heading", { name: "Official plugins", exact: true }).count(), 0);
      assert.equal(await card.locator(".source-category").innerText(), "Example");
      await checkOverflow(page, `discovery/${width}/${theme}`);
      await card.scrollIntoViewIfNeeded();
      if ([390, 1440].includes(width)) await page.screenshot({ path: path.join(evidenceRoot, `plugin-discovery-${width}-${theme}.png`) });
      const release = card.getByRole("combobox", { name: /^Release for/ });
      const options = await release.locator("option").evaluateAll(items => items.map(item => item.value));
      assert(options.length > 1, "Published release history is available");
      await card.getByRole("button", { name: /Jellyfin/ }).click();
      const overview = page.getByRole("dialog", { name: /^Review .*Jellyfin/ });
      await overview.waitFor();
      assert.equal(await overview.locator("details.readme").getAttribute("open"), "");
      await overview.locator(".metadata").getByText("Publisher", { exact: true }).waitFor();
      await checkOverflow(page, `expanded plugin overview/${width}/${theme}`);
      if ([390, 1440].includes(width)) await page.screenshot({ path: path.join(evidenceRoot, `plugin-expanded-overview-${width}-${theme}.png`) });
      await overview.locator("details.readme > summary").scrollIntoViewIfNeeded();
      if ([390, 1440].includes(width)) await page.screenshot({ path: path.join(evidenceRoot, `plugin-expanded-readme-${width}-${theme}.png`) });
      await page.keyboard.press("Escape"); await overview.waitFor({ state: "hidden" });
      await release.selectOption(options.at(-1));
      await card.getByRole("button", { name: /^Review \d/ }).click();
      const consent = page.getByRole("dialog", { name: /^Review .*Jellyfin/ });
      await consent.waitFor();
      await consent.locator(".version-pin").waitFor();
      await consent.getByText("Built for the old UI · limited support", { exact: true }).waitFor();
      assert.match(await consent.locator(".version-pin").innerText(), /automatic updates will be disabled/);
      await checkOverflow(page, `retained release review/${width}/${theme}`);
      if ([390, 1440].includes(width)) await page.screenshot({ path: path.join(evidenceRoot, `plugin-release-review-${width}-${theme}.png`) });
      await page.keyboard.press("Escape"); await consent.waitFor({ state: "hidden" });
      await page.getByRole("button", { name: "Install package or URL", exact: true }).click();
      const acquisition = page.getByRole("dialog", { name: "Install package or URL", exact: true });
      await acquisition.getByLabel("Plugin package", { exact: true }).waitFor();
      await acquisition.getByText("Install from URL", { exact: true }).click();
      await acquisition.getByRole("textbox", { name: "Plugin package URL", exact: true }).waitFor();
      assert.equal(await acquisition.locator(".catalogue-entry").count(), 0);
      const padding = await acquisition.locator(".installer-dialog").evaluate(element => parseFloat(getComputedStyle(element).paddingTop));
      assert(padding >= 12, "Acquisition dialog has breathing space");
      if (width >= 1024) {
        const boxes = await acquisition.locator(".install-method").evaluateAll(items => items.map(item => { const rect = item.getBoundingClientRect(); return { x: rect.x, y: rect.y }; }));
        assert.equal(boxes[0].y, boxes[1].y); assert(boxes[1].x > boxes[0].x);
      }
      await checkOverflow(page, `package chooser/${width}/${theme}`);
      if ([390, 1440].includes(width)) await page.screenshot({ path: path.join(evidenceRoot, `plugin-package-chooser-${width}-${theme}.png`) });
      await page.keyboard.press("Escape"); await acquisition.waitFor({ state: "hidden" });
      report.screens.push({ theme, width, screen: "direct discovery, grouped examples, historical release review, spacious package chooser" });
    }
    assert.deepEqual(errors, []);
    report.passed.push("12 real responsive discovery/release-review/acquisition cases; separate categories, retained releases, theme tokens and dialog layout");
  } finally {
    await admin.request.patch(origin + "/api/preferences", { data: { ui_theme: original.ui_theme } });
    await page.close();
  }
}
