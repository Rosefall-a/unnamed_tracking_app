import assert from "node:assert/strict";
import path from "node:path";

// Real phone touch input, using the authenticated disposable backend.
export async function checkMobileNavigation({ admin, browser, origin, evidenceRoot, report, checkOverflow }) {
  const original = await (await admin.request.get(origin + "/api/preferences")).json();
  const context = await browser.newContext({ storageState: await admin.storageState(), isMobile: true, hasTouch: true });
  const page = await context.newPage();
  const errors = [];
  page.on("pageerror", error => errors.push(String(error)));
  page.on("console", message => { if (["warning", "error"].includes(message.type()) && /Teleport|TypeError|ReferenceError/.test(message.text())) errors.push(message.text()); });
  const tabs = page.getByRole("navigation", { name: "Primary navigation", exact: true });
  const menu = page.getByRole("dialog", { name: "Main navigation", exact: true });
  try {
    for (const theme of ["light", "dark"]) {
      assert.equal((await admin.request.patch(origin + "/api/preferences", { data: { ui_theme: theme } })).status(), 200);
      for (const width of [320, 390, 430, 760]) {
        await page.setViewportSize({ width, height: 844 });
        await page.goto(origin + "/games"); await page.locator("#main-content h1").waitFor();
        await tabs.getByRole("button", { name: "Library", exact: true }).tap();
        await menu.getByRole("link", { name: "All games", exact: true }).waitFor();
        assert(await tabs.evaluate(element => Boolean(element.closest("dialog[open]"))), "Phone tabs stay inside the modal top layer");
        for (let repeat = 0; repeat < 3; repeat++) {
          await menu.locator(".nav-scroll").evaluate(element => { element.scrollTop = element.scrollHeight; });
          await tabs.getByRole("button", { name: "Media", exact: true }).tap();
          await menu.getByRole("link", { name: "Movies", exact: true }).waitFor();
          const movies = await menu.getByRole("link", { name: "Movies", exact: true }).boundingBox();
          const scrollBounds = await menu.locator(".nav-scroll").boundingBox();
          assert(movies.y >= scrollBounds.y - 1 && movies.y + movies.height <= scrollBounds.y + scrollBounds.height + 1, "Switching category reveals its links without another scroll");
          await tabs.getByRole("button", { name: "Library", exact: true }).tap();
          await menu.getByRole("link", { name: "All games", exact: true }).waitFor();
        }
        for (let repeat = 0; repeat < 2; repeat++) {
          await tabs.getByRole("button", { name: "Media", exact: true }).tap();
          await menu.getByRole("link", { name: "Movies", exact: true }).tap(); await page.waitForURL(origin + "/movies");
          await tabs.getByRole("button", { name: "Library", exact: true }).tap();
          await menu.getByRole("link", { name: "All games", exact: true }).tap(); await page.waitForURL(origin + "/games");
        }
        await tabs.getByRole("button", { name: "More", exact: true }).tap();
        await menu.getByRole("button", { name: "Cards", exact: true }).tap();
        for (const name of ["All cards", "Sets", "Bounties"]) assert(await menu.getByRole("link", { name, exact: true }).count(), `${name} remains available`);
        assert(await tabs.evaluate(element => [...element.children].every(child => { const box = child.getBoundingClientRect(); return box.width >= 44 && box.height >= 44; })));
        const footer = await menu.locator(".nav-footer").boundingBox(); const tabBounds = await tabs.boundingBox();
        assert(footer.y + footer.height <= tabBounds.y + 1, "Bottom tabs do not cover menu footer controls");
        for (let index = 0; index < 12; index++) { await page.keyboard.press("Tab"); assert(await menu.evaluate(element => element.contains(document.activeElement))); }
        await checkOverflow(page, `phone navigation/${theme}/${width}`);
        if (width === 390) {
          await menu.locator(".nav-scroll").evaluate(element => { element.scrollTop = 0; });
          await page.screenshot({ path: path.join(evidenceRoot, `mobile-navigation-${theme}.png`) });
        }
        await page.keyboard.press("Escape"); await menu.waitFor({ state: "hidden" });
        assert.equal(await page.evaluate(() => document.body.style.overflow), "");
        await tabs.getByRole("button", { name: "Library", exact: true }).tap(); await menu.waitFor();
        await tabs.getByRole("link", { name: "Home", exact: true }).tap(); await page.waitForURL(origin + "/"); await menu.waitFor({ state: "hidden" });
        await tabs.getByRole("button", { name: "Library", exact: true }).tap(); await menu.waitFor();
        await tabs.getByRole("link", { name: "Home", exact: true }).tap(); await menu.waitFor({ state: "hidden" });
        // Orientation/breakpoint changes must not leave the tabs in a removed pane.
        await tabs.getByRole("button", { name: "Media", exact: true }).tap(); await menu.waitFor();
        await page.setViewportSize({ width: 1024, height: 768 });
        await page.getByRole("button", { name: "Expand navigation", exact: true }).waitFor();
        await page.setViewportSize({ width, height: 844 });
        await tabs.getByRole("button", { name: "Media", exact: true }).tap();
        await menu.getByRole("link", { name: "Movies", exact: true }).tap(); await page.waitForURL(origin + "/movies");
        report.screens.push({ theme, width, screen: "phone-touch-navigation" });
      }
      await page.setViewportSize({ width: 1440, height: 900 }); await page.goto(origin + "/games");
      await page.locator("#main-content h1").waitFor(); assert.equal(await tabs.count(), 0);
      const desktop = page.getByRole("navigation", { name: "Library and tools", exact: true });
      await desktop.getByRole("button", { name: "Media", exact: true }).click();
      await desktop.getByRole("link", { name: "Movies", exact: true }).click(); await page.waitForURL(origin + "/movies");
    }
    assert.deepEqual(errors, []);
    report.passed.push("Eight real touch cases across four phone widths and Light/Dark", "Library/Media switching in an open menu, repeated route changes, focus containment and dismissal", "Phone/tablet resizing, desktop navigation and preserved Cards/Sets/Bounties");
  } finally {
    await admin.request.patch(origin + "/api/preferences", { data: { ui_theme: original.ui_theme } });
    await context.close();
  }
}
