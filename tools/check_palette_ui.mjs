// Real account palette saves, menu previews, system changes and populated-page propagation.
import assert from "node:assert/strict";
import path from "node:path";
import { checkDetailUi } from "./check_detail_ui.mjs";

export async function checkPaletteUi(options) {
  const { admin, member, origin, evidenceRoot, report } = options;
  async function json(response) { assert.equal(response.status(), 200, await response.text()); return response.json(); }
  const originals = await Promise.all([admin, member].map(async context => json(await context.request.get(origin + "/api/preferences"))));
  const page = await admin.newPage();
  const errors = []; page.on("pageerror", error => errors.push(String(error)));
  const custom = {
    light: { background: "#f2f1f8", surface: "#ffffff", surface_alt: "#e9e7f4", text: "#222534", muted: "#525568", accent: "#4b4fa8", success: "#216e3e", warning: "#855000", error: "#b42318", info: "#265a8b", purple: "#6951a2" },
    dark: { background: "#1b1725", surface: "#282232", surface_alt: "#352e42", text: "#f0ebf9", muted: "#bdb1ce", accent: "#b9a2ef", success: "#96d5a9", warning: "#f2c87a", error: "#ffa6a0", info: "#a2c8ef", purple: "#c6b5f1" },
  };
  const labels = { background: "Page background", surface: "Cards & menus", surface_alt: "Secondary surfaces", text: "Main text", muted: "Secondary text", accent: "Accent & selected controls", success: "Success", warning: "Warning", error: "Error", info: "Information", purple: "Planning & special status" };
  async function color(label, value) {
    await page.getByLabel(label, { exact: true }).evaluate((input, value) => {
      input.value = value; input.dispatchEvent(new Event("input", { bubbles: true }));
    }, value);
  }
  async function apply() {
    const saved = page.waitForResponse(response => new URL(response.url()).pathname === "/api/preferences" && response.request().method() === "PATCH");
    await page.getByRole("button", { name: "Apply palette", exact: true }).click();
    await json(await saved); await page.getByText("Appearance saved", { exact: true }).waitFor();
  }
  try {
    await json(await admin.request.patch(origin + "/api/preferences", { data: { ui_theme: "system", ui_palette: "orange", ui_high_contrast: false } }));
    await page.setViewportSize({ width: 390, height: 880 });
    await page.emulateMedia({ colorScheme: "light" });
    await page.goto(origin + "/settings?section=appearance");
    await page.getByLabel("Palette", { exact: true }).selectOption("green");
    assert.equal(await page.locator("html").getAttribute("data-palette"), "orange", "Preview does not apply unsaved colors");
    await page.getByRole("button", { name: "Dark preview", exact: true }).click();
    const preview = page.getByLabel("Palette preview", { exact: true });
    assert.equal(await preview.evaluate(element => getComputedStyle(element).colorScheme), "dark");
    await preview.getByText("Account menu", { exact: true }).click();
    assert(await preview.getByRole("button", { name: "Appearance", exact: true }).isVisible());
    await apply(); await page.reload(); await page.getByLabel("Palette", { exact: true }).waitFor();
    assert.equal(await page.locator("html").getAttribute("data-palette"), "green");
    assert.equal((await json(await member.request.get(origin + "/api/preferences"))).ui_palette, originals[1].ui_palette, "Administrator palette never changes the member palette");
    const light = await page.locator("html").evaluate(element => getComputedStyle(element).getPropertyValue("--ui-bg").trim());
    await page.emulateMedia({ colorScheme: "dark" }); await page.waitForFunction(() => document.documentElement.dataset.theme === "dark");
    const dark = await page.locator("html").evaluate(element => getComputedStyle(element).getPropertyValue("--ui-bg").trim());
    assert.notEqual(light, dark, "System mode changes the chosen palette's color set");
    await page.getByLabel("Palette", { exact: true }).selectOption("custom");
    await page.getByRole("button", { name: "Light preview", exact: true }).click();
    await color("Main text (light)", "#ffffff");
    assert(await page.getByRole("button", { name: "Apply palette", exact: true }).isDisabled(), "Unreadable custom text cannot be applied through the editor");
    for (const theme of ["light", "dark"]) {
      await page.getByRole("button", { name: theme === "light" ? "Light preview" : "Dark preview", exact: true }).click();
      for (const [role, value] of Object.entries(custom[theme])) await color(`${labels[role]} (${theme})`, value);
    }
    assert.equal(await page.getByRole("button", { name: "Apply palette", exact: true }).isDisabled(), false);
    await apply(); await page.reload(); await page.getByLabel("Palette", { exact: true }).waitFor();
    const saved = await json(await admin.request.get(origin + "/api/preferences"));
    assert.equal(saved.ui_palette, "custom"); assert.deepEqual(saved.ui_custom_palette, custom);
    assert.equal(saved.ui_theme, "system");
    const invalid = await admin.request.patch(origin + "/api/preferences", { data: { ui_custom_palette: { ...custom, light: { ...custom.light, accent: "url(https://example.invalid)" } } } });
    assert.equal(invalid.status(), 422); assert.deepEqual((await json(await admin.request.get(origin + "/api/preferences"))).ui_custom_palette, custom);
    for (const width of [390, 1440]) {
      await page.setViewportSize({ width, height: 1050 });
      for (const theme of ["light", "dark"]) {
        await page.emulateMedia({ colorScheme: theme });
        await page.getByRole("button", { name: theme === "light" ? "Light preview" : "Dark preview", exact: true }).click();
        await preview.scrollIntoViewIfNeeded();
        await page.evaluate(() => document.activeElement instanceof HTMLElement && document.activeElement.blur());
        await page.screenshot({ path: path.join(evidenceRoot, `stage-palette-preview-${width}-${theme}.png`) });
      }
    }
    await page.close();
    for (const palette of ["green", "custom"]) {
      for (const context of [admin, member]) await json(await context.request.patch(origin + "/api/preferences", { data: { ui_palette: palette, ui_custom_palette: custom } }));
      report.palette = palette;
      const before = report.screens.length;
      await checkDetailUi(options);
      console.log(`${palette}: ${report.screens.length - before} populated page checks passed`);
    }
    assert.deepEqual(errors, []);
    report.passed.push("Real preset/custom editor save, reload and account isolation", "Preview menus and light/dark color sets without changing unsaved app appearance", "System changes retain the chosen palette", "Unreadable text blocked in the editor and arbitrary CSS rejected by the API");
  } finally {
    if (!page.isClosed()) await page.close();
    for (const [index, context] of [admin, member].entries()) {
      const original = originals[index];
      await json(await context.request.patch(origin + "/api/preferences", { data: { ui_theme: original.ui_theme, ui_palette: original.ui_palette, ui_custom_palette: original.ui_custom_palette, ui_high_contrast: original.ui_high_contrast } }));
    }
  }
}
