import assert from "node:assert/strict";
import path from "node:path";

// New accounts, real preference writes and browser cookies; no fabricated API responses.
export async function checkAppearanceWelcome({ browser, admin, origin, evidenceRoot, report, checkOverflow }) {
  for (const mode of ["light", "dark"]) {
    for (const width of [320, 390, 1024, 1440]) {
      const username = `welcome-${mode}-${width}-${Date.now()}`;
      const response = await admin.request.post(origin + "/api/auth/users", { data: {
        username, email: `${username}@example.invalid`, password: process.env.UI_REVIEW_PASSWORD, is_admin: false,
      } });
      assert.equal(response.status(), 201);
      const { id } = await response.json();
      const context = await browser.newContext({ viewport: { width, height: 1050 }, colorScheme: mode });
      try {
        const login = await context.request.post(origin + "/api/auth/login", { data: {
          username_or_email: username, password: process.env.UI_REVIEW_PASSWORD,
        } });
        assert.equal(login.status(), 200);
        const before = await (await context.request.get(origin + "/api/preferences")).json();
        assert.equal(before.ui_welcome_completed, false);
        const page = await context.newPage();
        const errors = []; page.on("pageerror", error => errors.push(String(error)));
        await page.goto(origin + "/settings?section=appearance");
        const dialog = page.getByRole("dialog", { name: "Make yourself at home" });
        await dialog.waitFor();
        await dialog.getByText(`${mode === "dark" ? "Dark" : "Light"} preview`, { exact: true }).waitFor();
        await dialog.getByLabel("Theme", { exact: true }).selectOption(mode);
        await dialog.getByLabel("Color palette", { exact: true }).selectOption("green");
        await dialog.getByLabel("Spacing", { exact: true }).selectOption("compact");
        await dialog.getByLabel("Reduce motion", { exact: true }).check();
        await dialog.getByLabel("Higher contrast", { exact: true }).check();
        await page.waitForFunction(() => document.querySelector(".welcome-preview").style.getPropertyValue("--ui-accent").trim().length > 0);
        await checkOverflow(page, `welcome/${width}/${mode}`);
        assert(await dialog.evaluate(element => element.scrollWidth <= element.clientWidth + 1));
        if (width === 390 && mode === "dark" || width === 1440 && mode === "light")
          await page.screenshot({ path: path.join(evidenceRoot, `appearance-welcome-${width}-${mode}.png`) });
        if (width === 390 && mode === "dark") {
          let failSave = true;
          await page.route("**/api/preferences", async route => {
            if (route.request().method() === "PATCH" && failSave) {
              failSave = false;
              return route.abort("connectionrefused");
            }
            return route.continue();
          });
          await dialog.getByRole("button", { name: "Save & continue", exact: true }).click();
          await dialog.getByRole("alert").waitFor();
          assert.equal((await (await context.request.get(origin + "/api/preferences")).json()).ui_welcome_completed, false);
          await page.unroute("**/api/preferences");
        }
        const takeTour = width === 390 && mode === "dark" || width === 1440 && mode === "light";
        await dialog.getByRole("button", { name: takeTour ? "Save & take a tour" : "Save & continue", exact: true }).click();
        await dialog.waitFor({ state: "detached" });
        if (takeTour) {
          const guide = page.locator("[data-tour-guide]");
          await guide.getByText("Step 1 of 10", { exact: true }).waitFor();
          await page.waitForURL(origin + "/");
          await guide.getByRole("button", { name: "End tour", exact: true }).click();
          await guide.waitFor({ state: "detached" });
          await page.waitForLoadState("networkidle");
          await page.goto(origin + "/settings?section=appearance");
        }
        const saved = await (await context.request.get(origin + "/api/preferences")).json();
        assert.equal(saved.ui_welcome_completed, true);
        assert.equal(saved.ui_theme, mode);
        assert.equal(saved.ui_density, "compact");
        assert.equal(saved.ui_palette, "green");
        assert.equal(saved.ui_reduce_motion, true);
        assert.equal(saved.ui_high_contrast, true);
        const cookie = (await context.cookies()).find(item => item.name === "uta-ui-preferences");
        assert(cookie, "Appearance must be saved to a real browser cookie");
        assert.equal(cookie.path, "/"); assert.equal(cookie.sameSite, "Lax");
        const cache = JSON.parse(decodeURIComponent(cookie.value));
        assert.equal(cache.theme, mode); assert.equal(cache.density, "compact");
        assert(!cookie.value.includes(username) && !cookie.value.includes("welcome"));
        await page.waitForLoadState("networkidle");
        await page.reload();
        await page.getByRole("heading", { name: "Appearance & interface", level: 1 }).waitFor();
        assert.equal(await page.getByRole("dialog", { name: "Make yourself at home" }).count(), 0);
        await page.waitForLoadState("networkidle");
        await context.request.post(origin + "/api/auth/logout");
        // Remove localStorage to prove sign-in appearance comes from the cookie.
        await page.evaluate(() => localStorage.clear());
        await page.goto(origin + "/login");
        await page.waitForFunction(theme => document.documentElement.dataset.theme === theme &&
          document.documentElement.dataset.density === "compact" &&
          document.documentElement.classList.contains("reduce-motion") &&
          document.documentElement.classList.contains("high-contrast"), mode);
        await checkOverflow(page, `cookie-sign-in/${width}/${mode}`);
        assert.deepEqual(errors, []);
        report.screens.push({ width, theme: mode, first_login: true, welcome_once: true, cookie_only_sign_in: true });
      } finally {
        await context.close();
        assert.equal((await admin.request.delete(origin + `/api/auth/users/${id}`)).status(), 200);
      }
    }
  }
  report.passed.push("Eight new-account light/dark phone/desktop welcome flows save personal choices once", "Real cosmetic cookies restore sign-in appearance without localStorage or account data", "A failed welcome save retains choices and completion stays false until a successful retry");
}
