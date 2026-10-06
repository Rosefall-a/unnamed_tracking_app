// Responsive native dialogs against real manager endpoints; no package execution.
import assert from "node:assert/strict";
import path from "node:path";

export async function checkSettingsDialogs({ admin, member, origin, evidenceRoot, report, checkOverflow }) {
  const page = await admin.newPage();
  const settingsUrl = origin + "/api/plugins/manager-settings";
  const original = await (await admin.request.get(settingsUrl)).json();
  const appearance = await (await admin.request.get(origin + "/api/preferences")).json();
  const errors = []; page.on("pageerror", error => errors.push(String(error)));
  try {
    assert.equal((await member.request.get(settingsUrl)).status(), 403);
    for (const theme of ["light", "dark"]) for (const width of report.widths) {
      assert.equal((await admin.request.patch(origin + "/api/preferences", { data: { ui_theme: theme } })).status(), 200);
      await page.setViewportSize({ width, height: width <= 430 ? 880 : 1050 });
      await page.goto(origin + "/settings?section=plugins");
      await page.getByRole("button", { name: "Install package or URL", exact: true }).click();
      const installer = page.getByRole("dialog", { name: "Install package or URL", exact: true });
      await installer.waitFor();
      const bounds = await installer.boundingBox();
      assert(bounds.x >= 0 && bounds.x + bounds.width <= width + 1);
      assert(bounds.y >= 0 && bounds.y + bounds.height <= (width <= 430 ? 880 : 1050) + 1);
      if (width >= 900) {
        assert(bounds.width >= Math.min(1080, width - 64));
        const upload = await installer.locator(".install-method").first().boundingBox();
        const remote = await installer.locator(".install-method").nth(1).boundingBox();
        assert(Math.abs(upload.y - remote.y) <= 1 && remote.x > upload.x);
      }
      await installer.getByLabel("Plugin package", { exact: true }).waitFor();
      await installer.getByText("Install from URL", { exact: true }).first().click();
      await installer.getByRole("textbox", { name: "Plugin package URL", exact: true }).fill("https://example.invalid/review.utp");
      await checkOverflow(page, `plugin installer/${width}/${theme}`);
      if ([390, 1440].includes(width)) await page.screenshot({ path: path.join(evidenceRoot, `stage-plugin-installer-${width}-${theme}.png`) });
      await page.keyboard.press("Escape"); await installer.waitFor({ state: "hidden" });
      assert(await page.getByRole("button", { name: "Install package or URL", exact: true }).evaluate(element => element === document.activeElement));
      await page.getByText("Plugin Manager settings", { exact: true }).click();
      await page.getByRole("button", { name: "Save manager settings", exact: true }).waitFor();
      await checkOverflow(page, `plugin manager settings/${width}/${theme}`);
      report.screens.push({ width, theme, screen: "plugin installer and manager settings" });
    }
    const retained = page.getByRole("spinbutton", { name: "Old package versions to retain", exact: true });
    await retained.fill("0");
    assert(await page.getByRole("button", { name: "Save manager settings", exact: true }).isDisabled());
    const next = original.retained_versions === 2 ? 3 : 2;
    await retained.fill(String(next));
    await page.getByRole("button", { name: "Save manager settings", exact: true }).click();
    await page.getByRole("status").filter({ hasText: "Plugin Manager settings saved." }).waitFor();
    assert.equal((await (await admin.request.get(settingsUrl)).json()).retained_versions, next);
    await page.reload(); await page.getByText("Plugin Manager settings", { exact: true }).click();
    await retained.waitFor(); await page.waitForFunction(expected => document.querySelector('input[aria-label="Old package versions to retain"]').value === String(expected), next);
    assert.deepEqual(errors, []);
    report.passed.push("Responsive wide installer and manager settings across eight widths and light/dark", "Desktop installer columns, phone fit, Escape and focus restoration", "Manager save confirmation, invalid retention blocked, persistence and member authorization");
  } finally {
    assert.equal((await admin.request.put(settingsUrl, { data: original })).status(), 200);
    await admin.request.patch(origin + "/api/preferences", { data: { ui_theme: appearance.ui_theme } });
    await page.close();
  }
}
