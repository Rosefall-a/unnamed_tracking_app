// Native schedule validation/save feedback against real API responses.
import assert from "node:assert/strict";
import path from "node:path";

export async function checkTasksUi({ browser, admin, origin, evidenceRoot, report, checkOverflow }) {
  const original = await (await admin.request.get(origin + "/api/settings/jobs")).json();
  const preferences = await (await admin.request.get(origin + "/api/preferences")).json();
  try {
    for (const [theme, width] of [["light", 1440], ["light", 320], ["dark", 390], ["dark", 1920]]) {
      await admin.request.put(origin + "/api/settings/jobs/airing_check", { data: { interval_minutes: 30 } });
      await admin.request.put(origin + "/api/settings/jobs/media_refresh", { data: { interval_minutes: 1440 } });
      await admin.request.patch(origin + "/api/preferences", { data: { ui_theme: theme } });
      const context = await browser.newContext({ storageState: await admin.storageState(), viewport: { width, height: 900 } });
      const page = await context.newPage(), errors = [];
      page.on("pageerror", error => errors.push(String(error)));
      try {
        await page.goto(origin + "/settings?section=tasks");
        await page.getByRole("heading", { name: /^Background tasks$/i, level: 1 }).waitFor();
        const tile = name => page.locator(".tile").filter({ has: page.getByRole("heading", { name, exact: true }) });
        const airing = tile("Airing episode check"), refresh = tile("Media refresh");
        await airing.locator(".job-amount").waitFor();
        await airing.locator(".job-amount").fill("1");
        await airing.locator(".job-amount").press("Tab");
        await airing.getByRole("alert").filter({ hasText: /Choose between/ }).waitFor();
        assert.equal(await airing.locator(".job-amount").inputValue(), "1");
        assert.equal(await airing.locator(".job-amount").getAttribute("aria-invalid"), "true");
        assert.equal(await page.locator(".settings-section > .form-error").count(), 0);
        await refresh.locator(".job-amount").fill("31");
        await refresh.locator(".job-amount").press("Tab");
        await refresh.getByRole("alert").filter({ hasText: /Choose between/ }).waitFor();
        const response = page.waitForResponse(item => item.url().includes("/api/settings/jobs/airing_check") && item.request().method() === "PUT");
        await airing.locator(".job-amount").fill("15");
        await airing.locator(".job-amount").press("Tab");
        assert.equal((await response).status(), 200);
        await airing.locator('.job-amount[aria-invalid="false"]').waitFor();
        assert.equal(await refresh.locator(".job-amount").inputValue(), "31");
        await refresh.getByRole("alert").waitFor();
        await page.locator(".save-status.saved").filter({ hasText: "All changes saved" }).waitFor();
        await checkOverflow(page, `Tasks field validation ${theme}/${width}`);
        const snapshot = `tasks-validation-${width}-${theme}.png`;
        await page.evaluate(() => window.scrollTo(0, 0));
        await page.screenshot({ path: path.join(evidenceRoot, snapshot), fullPage: true }); report.screens.push(snapshot);
        const colors = await airing.locator(".job-amount").evaluate(element => {
          const root = getComputedStyle(document.documentElement), input = getComputedStyle(element);
          return { text: input.color, background: input.backgroundColor, role: root.getPropertyValue("--ui-text").trim(), scroll: input.scrollbarColor };
        });
        assert(colors.text !== colors.background, "task text must contrast with its field background");
        assert(!colors.scroll.includes("auto"), "native controls must inherit themed scrollbars");
        if (width === 1440) {
          await page.locator(".save-status.settled").filter({ hasText: "Saved" }).waitFor({ timeout: 16_000 });
          assert.equal(await page.locator(".save-status.saved").count(), 0);
        }
        assert.deepEqual(errors, []);
        report.passed.push(`Task period errors stay beside their field; drafts survive another save, themed controls and save confirmation: ${theme}/${width}`);
      } finally { await context.close(); }
    }
  } finally {
    for (const job of original) await admin.request.put(origin + "/api/settings/jobs/" + job.id, { data: { enabled: job.enabled, interval_minutes: job.interval_minutes } });
    await admin.request.patch(origin + "/api/preferences", { data: preferences });
  }
}
