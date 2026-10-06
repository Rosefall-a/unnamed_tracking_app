// Exercise the guided tour against real pages, dialogs, shortcuts and API data.
import assert from "node:assert/strict";
import { writeFile } from "node:fs/promises";
import path from "node:path";

export async function checkQuickTour({ browser, admin, origin, evidenceRoot, report, checkOverflow }) {
  const preferences = await (await admin.request.get(origin + "/api/preferences")).json();
  try {
    for (const theme of ["light", "dark"]) for (const width of [1440, 390]) {
      const mobile = width < 760;
      const context = await browser.newContext({
        storageState: await admin.storageState(), viewport: { width, height: mobile ? 600 : 1000 },
        hasTouch: mobile, isMobile: mobile,
      });
      const errors = [];
      const page = await context.newPage();
      page.on("pageerror", error => errors.push(String(error)));
      try {
        assert.equal((await context.request.patch(origin + "/api/preferences", {
          data: { ui_theme: theme, ui_welcome_completed: true },
        })).status(), 200);
        await page.goto(origin + "/");
        await page.getByRole("button", { name: "Quick tour", exact: true }).click();
        const guide = page.locator("[data-tour-guide]");
        const next = () => guide.getByRole("button", { name: "Continue", exact: true });
        async function step(number) {
          await guide.getByText(`Step ${number} of 10`, { exact: true }).waitFor();
          await checkOverflow(page, `tour ${number}/${theme}/${width}`);
        }
        async function screenshot(name) {
          const filename = `tour-${name}-${width}-${theme}.png`;
          await page.screenshot({ path: path.join(evidenceRoot, filename) });
          report.screens.push(filename);
        }
        await step(1); await next().click();
        await step(2);
        assert.equal(await next().isEnabled(), false);
        if (mobile) await guide.getByRole("button", { name: "Open search", exact: true }).click();
        else await page.keyboard.press("Control+k");
        const palette = page.locator('dialog[data-tour="library-search"][open]');
        await palette.waitFor();
        await page.locator('[data-tour="palette-search"]').fill("Settings");
        await page.waitForFunction(() => document.querySelector("[data-tour-guide]")?.closest("dialog")?.dataset.tour === "library-search");
        await page.keyboard.press("Alt+g");
        assert.equal(new URL(page.url()).pathname, "/", "navigation must remain paused in search");
        await screenshot("search");
        await palette.getByRole("button", { name: "Close dialog", exact: true }).click();
        await next().click(); await step(3);
        if (mobile) await page.locator('[data-tour="nav-games"]:visible').last().click();
        else {
          // A mouse navigation alone cannot complete a keyboard practice step.
          await page.locator('.home-shortcuts a[href="/games"]').click();
          assert.equal(await next().isEnabled(), false);
          await guide.focus(); await page.keyboard.press("Alt+g");
        }
        await next().click(); await step(4);
        const filters = page.locator('[data-tour="games-filters"]');
        await filters.click();
        await page.locator('[data-tour="games-filter-panel"]').waitFor();
        assert.equal(await next().isEnabled(), false);
        await filters.click(); await next().click(); await step(5);
        await page.locator('[data-tour="collection-create"]').click();
        const collection = page.locator('dialog[data-tour="collection-editor"][open]');
        await collection.waitFor();
        await page.waitForFunction(() => document.querySelector("[data-tour-guide]")?.closest("dialog")?.dataset.tour === "collection-editor");
        await screenshot("collection");
        await collection.getByRole("button", { name: "Close dialog", exact: true }).click();
        await next().click(); await step(6);
        if (mobile) await page.locator('[data-tour="nav-media"]:visible').last().click();
        else { await guide.focus(); await page.keyboard.press("Alt+m"); }
        await next().click(); await step(7);
        if (mobile) await page.locator('[data-tour="nav-settings"]:visible').last().click();
        else { await guide.focus(); await page.keyboard.press("Alt+p"); }
        await next().click(); await step(8);
        await page.locator('[data-tour="ui-appearance"]').waitFor();
        await screenshot("appearance");
        await next().click(); await step(9);
        await page.locator('[data-tour="customize-home"]').click();
        const widgets = page.locator('dialog[data-tour="home-widget-editor"][open]');
        await widgets.waitFor();
        await page.waitForFunction(() => document.querySelector("[data-tour-guide]")?.closest("dialog")?.dataset.tour === "home-widget-editor");
        await screenshot("home-dialog");
        await widgets.getByRole("button", { name: "Close dialog", exact: true }).click();
        await next().click(); await step(10);
        if (mobile) await guide.getByRole("button", { name: "Open shortcut help", exact: true }).click();
        else { await guide.focus(); await page.keyboard.press("?"); }
        const help = page.locator('dialog[data-tour="shortcut-help"][open]');
        await help.waitFor();
        assert.match(await help.locator("summary").first().innerText(), /Games library/);
        await help.locator("summary").nth(1).click();
        await help.getByRole("button", { name: "Close dialog", exact: true }).click();
        await guide.getByRole("button", { name: "Finish tour", exact: true }).click();
        await guide.waitFor({ state: "detached" });
        assert.equal(await page.locator("[data-tour-highlight]").count(), 0);
        await page.goto(origin + "/settings?section=shortcuts");
        await page.getByRole("button", { name: "Replay guided tour", exact: true }).click();
        await step(1);
        await guide.getByRole("button", { name: "End tour", exact: true }).click();
        await guide.waitFor({ state: "detached" });
        assert.equal(await page.locator("[data-tour-highlight]").count(), 0);
        assert.deepEqual(errors, []);
        report.passed.push(`Guided tour: 10 real steps, required shortcut practice, real modal containment, touch alternatives, replay and cleanup ${theme}/${width}`);
      } catch (error) {
        await page.screenshot({ path: path.join(evidenceRoot, `tour-failure-${theme}-${width}.png`) });
        await writeFile(path.join(evidenceRoot, `tour-debug-${theme}-${width}.json`), JSON.stringify(await page.evaluate(() => ({
          path: location.pathname, guide: document.querySelector('[data-tour-guide]')?.textContent,
          focus: document.activeElement?.tagName,
        })), null, 2));
        throw error;
      } finally {
        if (errors.length) await writeFile(path.join(evidenceRoot, `tour-errors-${theme}-${width}.json`), JSON.stringify(errors));
        await context.close();
      }
    }
  } finally {
    assert.equal((await admin.request.patch(origin + "/api/preferences", { data: preferences })).status(), 200);
  }
}
