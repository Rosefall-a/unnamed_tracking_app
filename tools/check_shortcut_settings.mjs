// Actual preferences, controls and persistence; no API mocks or synthetic registry.
import assert from "node:assert/strict";
import path from "node:path";

export async function checkShortcutSettings({ browser, admin, origin, evidenceRoot, report, checkOverflow }) {
  const original = await (await admin.request.get(origin + "/api/preferences")).json();
  try {
    for (const [theme, width] of [["light", 1440], ["dark", 390], ["light", 320], ["dark", 1920]]) {
      const context = await browser.newContext({ storageState: await admin.storageState(), viewport: { width, height: 900 } });
      const page = await context.newPage(), errors = [];
      page.on("pageerror", error => errors.push(String(error)));
      try {
        assert.equal((await context.request.patch(origin + "/api/preferences", { data: { ui_theme: theme, keyboard_shortcuts_enabled: true, keyboard_shortcut_overrides: {} } })).status(), 200);
        await page.goto(origin + "/settings?section=shortcuts");
        await page.getByRole("heading", { name: "Keyboard Shortcuts", exact: true, level: 1 }).waitFor();
        assert.equal(await page.locator('[data-shortcut-id^="nav."]').count(), 12);
        assert.equal(await page.locator('[data-shortcut-id="nav.e"], [data-shortcut-id="nav.s"], [data-shortcut-id="nav.b"]').count(), 0);
        const binding = id => page.locator(`[data-shortcut-id="${id}"]`);
        async function edit(id) {
          const section = page.locator(`details:has([data-shortcut-id="${id}"])`);
          if (!await section.evaluate(element => element.open)) await section.locator("summary").click();
          await binding(id).getByRole("button", { name: /Change keys/ }).click();
          const dialog = page.getByRole("dialog", { name: /^Change shortcut:/ });
          await dialog.waitFor(); return dialog;
        }
        async function save(dialog) {
          const response = page.waitForResponse(item => item.url().endsWith("/api/preferences") && item.request().method() === "PATCH");
          await dialog.getByRole("button", { name: "Save keys", exact: true }).click();
          assert.equal((await response).status(), 200);
          await dialog.waitFor({ state: "detached" });
        }
        let dialog = await edit("nav.g");
        await dialog.getByRole("button", { name: "Record keys", exact: true }).click();
        await page.keyboard.press("Alt+Shift+g");
        assert.equal(await dialog.getByRole("textbox", { name: "Key combination 1", exact: true }).inputValue(), "Alt+Shift+G");
        await save(dialog);
        await page.reload(); await binding("nav.g").waitFor();
        assert.match(await binding("nav.g").innerText(), /Alt \+ Shift \+ G/);
        if (width > 760) assert.match(await page.locator('.navigation [data-tour="nav-games"]').getAttribute("title"), /Alt \+ Shift \+ G/);
        await page.locator("h1").first().click(); await page.keyboard.press("Alt+g");
        assert.equal(new URL(page.url()).pathname, "/settings");
        await page.keyboard.press("Alt+Shift+g"); await page.waitForURL(origin + "/games");
        await page.goto(origin + "/settings?section=shortcuts");
        dialog = await edit("app.search");
        await dialog.getByRole("textbox", { name: "Key combination 1", exact: true }).fill("CtrlOrMeta+J");
        await save(dialog);
        await page.locator("h1").first().click(); await page.keyboard.press("Control+k");
        assert.equal(await page.getByRole("dialog", { name: "Search library", exact: true }).count(), 0);
        await page.keyboard.press("Control+j");
        const search = page.getByRole("dialog", { name: "Search library", exact: true }); await search.waitFor();
        await page.keyboard.press("Escape"); await search.waitFor({ state: "detached" });
        dialog = await edit("nav.m");
        await dialog.getByRole("textbox", { name: "Key combination 1", exact: true }).fill("Alt+Shift+G");
        await dialog.getByText(/is used by Go to Games/).waitFor();
        await checkOverflow(page, `shortcut conflict ${theme}/${width}`);
        const screenshot = `shortcut-conflict-${width}-${theme}.png`;
        await page.screenshot({ path: path.join(evidenceRoot, screenshot) }); report.screens.push(screenshot);
        await save(dialog);
        assert.match(await binding("nav.m").innerText(), /existing shortcut stays active/);
        await page.locator("h1").first().click(); await page.keyboard.press("Alt+Shift+g"); await page.waitForURL(origin + "/games");
        await page.goto(origin + "/settings?section=shortcuts");
        const response = page.waitForResponse(item => item.url().endsWith("/api/preferences") && item.request().method() === "PATCH");
        await page.getByRole("checkbox", { name: "Enable keyboard shortcuts", exact: true }).uncheck();
        assert.equal((await response).status(), 200);
        await page.locator("h1").first().click(); await page.keyboard.press("Alt+Shift+g"); await page.keyboard.press("Control+j"); await page.keyboard.press("?");
        assert.equal(new URL(page.url()).pathname, "/settings"); assert.equal(await page.locator("dialog[open]").count(), 0);
        await page.getByRole("button", { name: "Replay guided tour", exact: true }).click();
        const guide = page.locator("[data-tour-guide]"); await guide.getByRole("button", { name: "Continue", exact: true }).click();
        await guide.getByText("Step 2 of 10", { exact: true }).waitFor();
        await guide.getByRole("button", { name: "Open search", exact: true }).click(); await search.waitFor();
        await page.keyboard.press("Escape"); await search.waitFor({ state: "detached" });
        await guide.getByRole("button", { name: "Continue", exact: true }).waitFor({ state: "visible" });
        await guide.getByRole("button", { name: "End tour", exact: true }).click();
        await page.goto(origin + "/settings?section=shortcuts");
        await page.getByRole("button", { name: "Restore all defaults", exact: true }).click();
        await page.getByRole("checkbox", { name: "Enable keyboard shortcuts", exact: true }).waitFor();
        await page.waitForFunction(() => document.querySelector('[data-shortcut-id="nav.g"] kbd')?.textContent?.trim() === "Alt + G");
        await checkOverflow(page, `shortcut settings ${theme}/${width}`);
        assert.deepEqual(errors, []);
        report.passed.push(`Shortcut record/remap/reload, conflict priority, master disable and clickable tour: ${theme}/${width}`);
      } catch (error) {
        await page.screenshot({ path: path.join(evidenceRoot, `failure-${width}-${theme}.png`) });
        console.error(await page.evaluate(() => ({ tour: document.querySelector('[data-tour-guide]')?.textContent,
          tourDialog: document.querySelector('[data-tour-guide]')?.closest('dialog')?.open, dialogs: [...document.querySelectorAll('dialog')].map(item => ({ open: item.open, text: item.textContent?.slice(0, 80) })) })));
        throw error;
      } finally { await context.close(); }
    }
  } finally {
    await admin.request.patch(origin + "/api/preferences", { data: { ui_theme: original.ui_theme,
      keyboard_shortcuts_enabled: original.keyboard_shortcuts_enabled, keyboard_shortcut_overrides: original.keyboard_shortcut_overrides } });
  }
}
