import assert from "node:assert/strict";
import path from "node:path";

// Real phone touch input, including short viewports with space reserved for browser chrome.
export async function checkMobileNavigation({ admin, browser, origin, evidenceRoot, report, checkOverflow }) {
  const original = await (await admin.request.get(origin + "/api/preferences")).json();
  const context = await browser.newContext({ storageState: await admin.storageState(), isMobile: true, hasTouch: true });
  const page = await context.newPage();
  const errors = [];
  page.on("pageerror", error => errors.push(String(error)));
  page.on("console", message => { if (["warning", "error"].includes(message.type()) && /Teleport|TypeError|ReferenceError/.test(message.text())) errors.push(message.text()); });
  const tabs = page.getByRole("navigation", { name: "Primary navigation", exact: true });
  const menu = page.getByRole("dialog", { name: "Main navigation", exact: true });
  const openMenu = page.getByRole("button", { name: "Open menu", exact: true });
  try {
    for (const theme of ["light", "dark"]) {
      assert.equal((await admin.request.patch(origin + "/api/preferences", { data: { ui_theme: theme } })).status(), 200);
      for (const [width, height] of [[320, 568], [390, 600], [430, 844], [760, 600]]) {
        await page.setViewportSize({ width, height });
        await page.goto(origin + "/games"); await page.locator("#main-content h1").waitFor();
        for (let repeat = 0; repeat < 3; repeat++) {
          await tabs.getByRole("link", { name: "Media", exact: true }).tap(); await page.waitForURL(origin + "/movies");
          await menu.waitFor({ state: "hidden" });
          await tabs.getByRole("link", { name: "Games", exact: true }).tap(); await page.waitForURL(origin + "/games");
          await menu.waitFor({ state: "hidden" });
          await tabs.getByRole("link", { name: "Settings", exact: true }).tap(); await page.waitForURL(origin + "/settings");
          await openMenu.tap(); await menu.waitFor();
          assert(await tabs.evaluate(element => Boolean(element.closest("dialog[open]"))), "Phone tabs remain in the modal top layer");
          await tabs.getByRole("link", { name: "Games", exact: true }).tap(); await page.waitForURL(origin + "/games");
          await menu.waitFor({ state: "hidden" });
        }
        await openMenu.tap(); await menu.waitFor();
        const body = menu.locator(".nav-body");
        const bodyBounds = await body.boundingBox(); const tabBounds = await tabs.boundingBox();
        assert(bodyBounds.height >= height * 0.45, "Library entries retain at least 45% of the short viewport");
        assert(bodyBounds.y + bodyBounds.height <= tabBounds.y + 1, "Tabs do not cover the menu scroll area");
        await body.evaluate(element => { element.scrollTop = element.scrollHeight; });
        for (const name of ["Preferences", "Administration", "Your account", "Sign out"]) {
          const control = menu.getByRole(name === "Sign out" ? "button" : "link", { name, exact: true });
          await control.scrollIntoViewIfNeeded();
          const bounds = await control.boundingBox();
          assert(bounds.height >= 44 && bounds.y + bounds.height <= tabBounds.y + 1, `${name} remains reachable and touch sized`);
        }
        assert(await tabs.evaluate(element => [...element.children].every(child => { const box = child.getBoundingClientRect(); return box.width >= 44 && box.height >= 44; })));
        for (let index = 0; index < 12; index++) { await page.keyboard.press("Tab"); assert(await menu.evaluate(element => element.contains(document.activeElement))); }
        await checkOverflow(page, `phone navigation/${theme}/${width}`);
        if (width === 390) {
          await body.evaluate(element => { element.scrollTop = 0; });
          await page.screenshot({ path: path.join(evidenceRoot, `mobile-navigation-${theme}.png`) });
        }
        await page.keyboard.press("Escape"); await menu.waitFor({ state: "hidden" });
        assert.equal(await page.evaluate(() => document.body.style.overflow), "");
        await openMenu.tap(); await menu.waitFor();
        await tabs.getByRole("link", { name: "Home", exact: true }).tap(); await page.waitForURL(origin + "/"); await menu.waitFor({ state: "hidden" });
        await openMenu.tap(); await menu.waitFor();
        await tabs.getByRole("link", { name: "Home", exact: true }).tap(); await menu.waitFor({ state: "hidden" });
        await openMenu.tap(); await menu.waitFor();
        await page.setViewportSize({ width: 1024, height: 768 });
        await page.getByRole("button", { name: "Expand navigation", exact: true }).waitFor();
        await page.setViewportSize({ width, height });
        await tabs.getByRole("link", { name: "Media", exact: true }).tap(); await page.waitForURL(origin + "/movies");
        report.screens.push({ theme, width, height, screen: "phone-touch-navigation" });
      }
      await page.setViewportSize({ width: 1440, height: 900 }); await page.goto(origin + "/games");
      await page.locator("#main-content h1").waitFor(); assert.equal(await tabs.count(), 0);
      const desktop = page.getByRole("navigation", { name: "Library and tools", exact: true });
      await desktop.getByRole("button", { name: "Media", exact: true }).click();
      await desktop.getByRole("link", { name: "Movies", exact: true }).click(); await page.waitForURL(origin + "/movies");
    }
    await page.setViewportSize({ width: 390, height: 600 });
    await openMenu.tap(); await menu.getByRole("button", { name: "Sign out", exact: true }).tap();
    const confirmation = page.getByRole("dialog", { name: "Sign out?", exact: true });
    await confirmation.getByRole("button", { name: "Cancel", exact: true }).tap();
    assert.equal((await context.request.get(origin + "/api/auth/me")).status(), 200);
    await page.locator(".profile-menu-trigger").tap();
    await page.getByRole("button", { name: "Log Out", exact: true }).tap();
    await confirmation.getByRole("button", { name: "Cancel", exact: true }).tap();
    assert.equal((await context.request.get(origin + "/api/auth/me")).status(), 200);
    await openMenu.tap(); await menu.getByRole("button", { name: "Sign out", exact: true }).tap();
    await confirmation.getByRole("button", { name: "Sign out", exact: true }).tap(); await page.waitForURL(origin + "/login");
    assert.equal((await context.request.get(origin + "/api/auth/me")).status(), 401);
    assert.deepEqual(errors, []);
    report.passed.push("Eight touch cases across four phone widths and Light/Dark, including short viewports", "Direct Games/Movies/Settings navigation, hamburger, modal tabs, focus containment and dismissal", "Scrollable compact menu footer and 44px controls", "Both logout controls cancel safely; confirmed logout revokes the real session", "Phone/tablet resizing and desktop navigation");
  } finally {
    await admin.request.patch(origin + "/api/preferences", { data: { ui_theme: original.ui_theme } });
    await context.close();
  }
}
