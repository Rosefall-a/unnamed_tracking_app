// Real static package inspection: version failures must dominate the install review.
import assert from "node:assert/strict";
import path from "node:path";

export async function checkPluginReviewUi({ admin, origin, evidenceRoot, report, checkOverflow }) {
  const file = process.env.PLUGIN_COMPATIBILITY_REVIEW_PACKAGE;
  assert(file, "Provide a package with incompatible API, SDK and application requirements.");
  const original = await (await admin.request.get(origin + "/api/preferences")).json();
  const page = await admin.newPage(), errors = [];
  page.on("pageerror", error => errors.push(String(error)));
  try {
    for (const theme of ["light", "dark"]) for (const width of [320, 390, 760, 1440, 1920]) {
      assert.equal((await admin.request.patch(origin + "/api/preferences", { data: { ui_theme: theme } })).status(), 200);
      await page.setViewportSize({ width, height: width < 760 ? 720 : 1050 });
      await page.goto(origin + "/settings?section=plugins");
      await page.getByRole("button", { name: "Install package or URL", exact: true }).click();
      const chooser = page.getByRole("dialog", { name: "Install package or URL", exact: true });
      if (!(await chooser.locator("details").first().evaluate(element => element.open))) {
        await chooser.getByText("Upload package", { exact: true }).click();
      }
      await chooser.getByLabel("Plugin package", { exact: true }).setInputFiles(file);
      await chooser.getByRole("button", { name: "Review package", exact: true }).click();
      const review = page.getByRole("dialog", { name: /^Review .*UI/ });
      await review.getByRole("heading", { name: "Unable to install this release", exact: true }).waitFor();
      const blockedButton = review.getByRole("button", { name: "Unable to install", exact: true });
      assert(await blockedButton.isDisabled());
      assert.equal(await review.locator(".version-info .incompatible").count(), 3);
      assert.equal(await review.getByRole("button", { name: "Install with selected access", exact: true }).count(), 0);
      const blocker = review.locator(".install-blocker");
      assert(await blocker.evaluate(element => document.activeElement === element));
      const box = await blocker.boundingBox();
      assert(box.y >= 0 && box.y + box.height <= (width < 760 ? 720 : 1050), `Blocker is visible immediately: ${JSON.stringify({ width, theme, box })}`);
      await checkOverflow(page, `compatibility blocker/${width}/${theme}`);
      if ([390, 1440].includes(width)) await page.screenshot({ path: path.join(evidenceRoot, `plugin-install-blocker-${width}-${theme}.png`) });
      await review.getByRole("button", { name: "Release & documentation", exact: true }).click();
      assert.equal(await review.locator("details.readme").getAttribute("open"), "");
      assert(await blockedButton.isDisabled());
      await page.keyboard.press("Escape");
      await review.waitFor({ state: "hidden" });
      report.screens.push({ theme, width, screen: "three highlighted version failures, visible blocker and expanded documentation" });
    }
    assert.deepEqual(errors, []);
    report.passed.push("10 real incompatible-package reviews; every failed boundary highlighted, focused blocker visible, install unavailable in both views");
  } finally {
    await admin.request.patch(origin + "/api/preferences", { data: { ui_theme: original.ui_theme } });
    await page.close();
  }
}
