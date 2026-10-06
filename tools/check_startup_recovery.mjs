import assert from "node:assert/strict";
import path from "node:path";

export async function checkStartupRecovery({ browser, admin, origin, evidenceRoot, report, checkOverflow }) {
  const original = await (await admin.request.get(origin + "/api/preferences")).json();
  const destination = "/settings?section=appearance&source=startup-check";
  try {
    for (const theme of ["light", "dark"]) {
      assert.equal((await admin.request.patch(origin + "/api/preferences", { data: { ui_theme: theme } })).status(), 200);
      for (const width of [320, 390, 1024, 1440]) {
        for (const failedPath of ["/api/setup/status", "/api/auth/me"]) {
          const context = await browser.newContext({ storageState: await admin.storageState(), viewport: { width, height: 1000 }, colorScheme: theme });
          try {
            const page = await context.newPage();
            const errors = []; page.on("pageerror", error => errors.push(String(error)));
            let unavailable = true;
            await page.route("**" + failedPath, route => {
              if (unavailable) { unavailable = false; return route.abort("connectionrefused"); }
              return route.continue();
            });
            await page.addInitScript(() => { window.startupDocumentIdentity = Math.random(); });
            await page.goto(origin + destination);
            await page.getByRole("heading", { name: "Backend unavailable", exact: true }).waitFor();
            const identity = await page.evaluate(() => window.startupDocumentIdentity);
            await checkOverflow(page, `startup/${failedPath}/${width}/${theme}`);
            if (width === 390 && theme === "dark" && failedPath === "/api/auth/me") {
              await page.screenshot({ path: path.join(evidenceRoot, "startup-unavailable-390-dark.png"), fullPage: true });
            }
            await page.getByRole("button", { name: "Retry connection", exact: true }).click();
            await page.getByRole("heading", { name: "Appearance & interface", level: 1, exact: true }).waitFor();
            assert.equal(new URL(page.url()).pathname + new URL(page.url()).search, destination);
            assert.equal(await page.evaluate(() => window.startupDocumentIdentity), identity, "Recovery preserves the same loaded document");
            await page.waitForFunction(mode => document.documentElement.dataset.theme === mode, theme);
            await checkOverflow(page, `recovered/${width}/${theme}`);
            assert.deepEqual(errors, []);
            report.screens.push({ theme, width, screen: destination, failed_request: failedPath, recovered_without_reload: true });
          } finally { await context.close(); }
        }
      }
    }
    const context = await browser.newContext({ storageState: await admin.storageState() });
    try {
      const page = await context.newPage(); let first = true;
      await page.route("**/api/auth/me", route => { if (first) { first = false; return route.abort("connectionrefused"); } return route.continue(); });
      await page.goto(origin + destination);
      await page.getByRole("heading", { name: "Backend unavailable", exact: true }).waitFor();
      await page.getByRole("heading", { name: "Appearance & interface", level: 1, exact: true }).waitFor({ timeout: 15000 });
    } finally { await context.close(); }
    report.passed.push("16 real-backend startup connection failures recover without reloading, preserving route and theme", "Automatic startup authentication recovery after the backend becomes available");
  } finally {
    await admin.request.patch(origin + "/api/preferences", { data: { ui_theme: original.ui_theme } });
  }
}
