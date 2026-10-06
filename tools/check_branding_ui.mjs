// Real deployment branding and account badge checks. Called only after media inventory guard.
import assert from "node:assert/strict";
import path from "node:path";

export async function checkBrandingUi({ admin, member, browser, origin, evidenceRoot, report, checkOverflow }) {
  const original = await (await admin.request.get(origin + "/api/branding")).json();
  assert.equal(original.logo_url, null, "Branding review requires a clean disposable identity.");
  assert.equal(original.favicon_url, "/api/branding/default-icon.svg");
  const preferences = await (await admin.request.get(origin + "/api/preferences")).json();
  const badges = await (await admin.request.get(origin + "/api/settings/appearance")).json();
  const page = await admin.newPage();
  const errors = [];
  page.on("pageerror", error => errors.push(String(error)));
  const publicContext = await browser.newContext();
  const publicPage = await publicContext.newPage();
  const memberPage = await member.newPage();
  for (const other of [publicPage, memberPage]) other.on("pageerror", error => errors.push(String(error)));
  try {
    await page.goto(origin + "/settings?section=branding");
    await page.getByLabel("Application name", { exact: true }).waitFor();
    await page.waitForFunction(() => { const input = document.querySelector('#branding-name'); return input && !input.matches(':disabled'); });
    await page.getByLabel("Application name", { exact: true }).fill("Weekend Archive");
    await page.getByRole("button", { name: "Save name", exact: true }).click();
    await page.getByText("Branding saved.", { exact: true }).waitFor();
    await page.waitForFunction(() => /^(?:\(\d+\+?\) )?App branding \| Weekend Archive$/.test(document.title));
    const png = Buffer.from(await page.evaluate(() => {
      const canvas = document.createElement("canvas"); canvas.width = 64; canvas.height = 64;
      const context = canvas.getContext("2d"); context.fillStyle = "#a4520d"; context.fillRect(0, 0, 64, 64);
      context.fillStyle = "#ffffff"; context.fillRect(16, 16, 32, 32);
      return canvas.toDataURL("image/png").split(",")[1];
    }), "base64");
    await page.getByLabel("App logo", { exact: true }).setInputFiles({ name: "review-logo.png", mimeType: "image/png", buffer: png });
    await page.getByRole("button", { name: "Remove logo", exact: true }).waitFor();
    const uploaded = await (await admin.request.get(origin + "/api/branding")).json();
    assert.equal(uploaded.favicon_url, uploaded.logo_url);
    await page.waitForFunction(url => document.querySelector('link[rel="icon"]').getAttribute("href") === url, uploaded.favicon_url);
    assert.equal((await publicContext.request.get(origin + uploaded.logo_url)).status(), 200);
    await page.getByLabel("Browser icon", { exact: true }).setInputFiles({ name: "bad.svg", mimeType: "image/svg+xml", buffer: Buffer.from("<svg/>") });
    await page.getByRole("alert").filter({ hasText: "could not be decoded" }).waitFor();
    assert.deepEqual(await (await admin.request.get(origin + "/api/branding")).json(), uploaded);
    for (const theme of ["light", "dark"]) {
      assert.equal((await admin.request.patch(origin + "/api/preferences", { data: { ui_theme: theme } })).status(), 200);
      assert.equal((await member.request.patch(origin + "/api/preferences", { data: { ui_theme: theme } })).status(), 200);
      await publicContext.addInitScript(value => localStorage.setItem("ui-theme", value), theme);
      await publicPage.emulateMedia({ colorScheme: theme });
      for (const width of report.widths) {
        for (const [role, target, screen] of [["admin", page, "/settings?section=branding"], ["member", memberPage, "/settings?section=branding"], ["public", publicPage, "/login"]]) {
          await target.setViewportSize({ width, height: width <= 430 ? 880 : 1050 });
          await target.goto(origin + screen);
          await target.locator(role === "public" ? ".login-card" : ".page-header h1").waitFor();
          await target.waitForFunction(() => document.title.endsWith("Weekend Archive"));
          await target.waitForFunction(expected => document.documentElement.dataset.theme === expected, theme);
          await target.waitForFunction(() => [...document.querySelectorAll(".app-brand-symbol img")].every(image => image.complete && image.naturalWidth > 0));
          if (role === "admin") await target.getByLabel("Application name", { exact: true }).waitFor();
          else assert.equal(await target.getByLabel("Application name", { exact: true }).count(), 0);
          await checkOverflow(target, `${role}/${theme}/${width}`);
          report.screens.push({ role, theme, width, screen });
          if (role !== "member" && [390, 1440].includes(width)) await target.screenshot({ path: path.join(evidenceRoot, `stage-branding-${role}-${width}-${theme}.png`), fullPage: width > 430 });
          if (role === "admin" && width === 390) {
            await target.getByLabel("App logo", { exact: true }).scrollIntoViewIfNeeded();
            await target.screenshot({ path: path.join(evidenceRoot, `stage-branding-controls-${width}-${theme}.png`) });
          }
        }
      }
    }
    assert.equal((await member.request.put(origin + "/api/branding", { data: { app_name: "Other" } })).status(), 403);
    assert.equal((await publicContext.request.put(origin + "/api/branding", { data: { app_name: "Other" } })).status(), 401);
    assert.equal((await admin.request.put(origin + "/api/settings/appearance", { data: { completion_badge_style: "border", completion_badge_color: "#a4520d" } })).status(), 200);
    assert.equal((await member.request.put(origin + "/api/settings/appearance", { data: { completion_badge_style: "ribbon", completion_badge_color: "#245789" } })).status(), 200);
    assert.equal((await (await admin.request.get(origin + "/api/settings/appearance")).json()).completion_badge_style, "border");
    assert.equal((await (await member.request.get(origin + "/api/settings/appearance")).json()).completion_badge_style, "ribbon");
    await page.goto(origin + "/settings?section=branding");
    await page.waitForFunction(() => { const input = document.querySelector('#branding-name'); return input && !input.matches(':disabled'); });
    await page.getByLabel("Application name", { exact: true }).fill("Retry name");
    await admin.setOffline(true);
    await page.getByRole("button", { name: "Save name", exact: true }).click();
    await page.getByRole("alert").waitFor();
    assert((await page.title()).endsWith("Weekend Archive"));
    await admin.setOffline(false);
    await page.getByRole("button", { name: "Save name", exact: true }).click();
    await page.waitForFunction(() => document.title.endsWith("Retry name"));
    assert.deepEqual(errors, []);
    report.passed.push("48 branding role/theme/width cases with no overflow or JavaScript errors", "Name, normalized logo and favicon persist and update public pages", "Anonymous/member branding writes denied", "Malformed upload preserves current branding", "Offline name save reports failure and retries without losing input", "Badges remain distinct between two accounts");
  } finally {
    await admin.setOffline(false);
    await admin.request.put(origin + "/api/branding", { data: { app_name: original.app_name } });
    await admin.request.delete(origin + "/api/branding/assets/logo");
    await admin.request.delete(origin + "/api/branding/assets/favicon");
    await admin.request.put(origin + "/api/settings/appearance", { data: { completion_badge_style: badges.completion_badge_style, completion_badge_color: badges.completion_badge_color, completion_badge_placement: badges.completion_badge_placement } });
    await admin.request.patch(origin + "/api/preferences", { data: { ui_theme: preferences.ui_theme } });
    await publicContext.close();
    await page.close();
    await memberPage.close();
  }
}
