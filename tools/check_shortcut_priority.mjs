// Public-API/browser acceptance with an installed v1.1 Shortcut Playground.
import assert from "node:assert/strict";
import path from "node:path";

export async function checkShortcutPriority({
  browser,
  admin,
  origin,
  evidenceRoot,
  report,
  checkOverflow,
}) {
  const saved = await (
    await admin.request.get(origin + "/api/preferences")
  ).json();
  const pluginId = "example.shortcut-playground";
  const shortcutId = `plugin:${pluginId}:search-conflict`;
  const route = `/plugins/${pluginId}/playground`;
  try {
    for (const [width, theme] of [
      [1440, "light"],
      [390, "dark"],
      [320, "light"],
      [1920, "dark"],
    ]) {
      const context = await browser.newContext({
        storageState: await admin.storageState(),
        hasTouch: width <= 760,
        viewport: { width, height: width <= 760 ? 800 : 1000 },
      });
      const page = await context.newPage(),
        errors = [];
      page.on("pageerror", (error) => errors.push(String(error)));
      page.on("console", (message) => {
        if (message.type() === "error") errors.push(message.text());
      });
      const binding = (id) => page.locator(`[data-shortcut-id="${id}"]`);
      const notice = page.locator(".shortcut-notice");
      async function setEnabled(id, enabled) {
        const group = binding(id).locator("..");
        if (!(await group.evaluate((element) => element.open)))
          await group.locator("summary").click();
        const response = page.waitForResponse(
          (item) =>
            item.url().endsWith("/api/preferences") &&
            item.request().method() === "PATCH",
        );
        await binding(id).getByRole("checkbox").setChecked(enabled);
        assert.equal((await response).status(), 200);
        await page
          .getByText("Shortcut preferences saved to your account.", {
            exact: true,
          })
          .waitFor();
      }
      async function capture(name) {
        await checkOverflow(page, `shortcut ${name} ${width}/${theme}`);
        await page.waitForTimeout(220);
        const file = `shortcut-${name}-${width}-${theme}.png`;
        await page.screenshot({ path: path.join(evidenceRoot, file) });
        report.screens.push(file);
      }
      try {
        assert.equal(
          (
            await context.request.patch(origin + "/api/preferences", {
              data: {
                ui_theme: theme,
                ui_welcome_completed: true,
                keyboard_shortcuts_enabled: true,
                keyboard_shortcut_overrides: {},
              },
            })
          ).status(),
          200,
        );
        await page.goto(origin + route);
        await page
          .getByRole("button", { name: "Add random shortcut", exact: true })
          .waitFor();
        await notice
          .getByText("New shortcut could not be added", { exact: true })
          .waitFor();
        assert.match(
          await notice.innerText(),
          /Intentional Search conflict was disabled/,
        );
        await capture("new-conflict");
        if (width <= 760) {
          await page.getByRole("button", { name: "Open menu", exact: true }).click();
          const menu = page.getByRole("dialog", { name: "Main navigation" });
          await menu.waitFor();
          await page.keyboard.press("Escape");
          await menu.waitFor({ state: "hidden" });
          await notice.waitFor();
        }
        await notice
          .getByRole("link", { name: "Change keys", exact: true })
          .click();
        let editor = page.getByRole("dialog", {
          name: "Change shortcut: Intentional Search conflict",
          exact: true,
        });
        await editor.waitFor();
        assert.equal(
          new URL(page.url()).searchParams.get("binding"),
          shortcutId,
        );
        await checkOverflow(page, `linked editor ${width}/${theme}`);
        await page.keyboard.press("Escape");
        await editor.waitFor({ state: "hidden" });
        assert.equal(
          await binding(shortcutId).getByRole("checkbox").isChecked(),
          false,
        );
        await setEnabled("app.search", false);
        await setEnabled(shortcutId, true);
        assert.equal(
          await binding(shortcutId).getByRole("checkbox").isChecked(),
          true,
        );
        await page.locator("h1").first().click();
        await page.keyboard.press("Control+k");
        await page.waitForURL(origin + route);
        await page
          .getByRole("status")
          .filter({
            hasText:
              "You resolved the Search conflict and ran the example binding.",
          })
          .waitFor();
        assert.equal(
          await page
            .getByRole("dialog", { name: "Search library", exact: true })
            .count(),
          0,
        );
        await page.goto(origin + "/settings?section=shortcuts");
        await binding("app.search").waitFor();
        await setEnabled("app.search", true);
        await notice
          .getByText("New shortcut could not be added", { exact: true })
          .waitFor();
        assert.equal(
          await binding("app.search").getByRole("checkbox").isChecked(),
          false,
        );
        assert.match(
          await binding("app.search").innerText(),
          /Intentional Search conflict/,
        );
        await capture("oldest-owner");
        await notice
          .getByRole("button", {
            name: "Dismiss shortcut conflict",
            exact: true,
          })
          .click();
        await page.reload();
        await binding(shortcutId).waitFor({ state: "attached" });
        await page.waitForFunction(
          (id) =>
            document.querySelector(`[data-shortcut-id="${id}"] input`)?.checked,
          shortcutId,
        );
        assert.equal(
          await binding("app.search").getByRole("checkbox").isChecked(),
          false,
        );
        assert.equal(
          await notice.count(),
          0,
          "Persisted blocked bindings do not notify again on reload",
        );
        await page.locator("h1").first().click();
        await page.keyboard.press("Control+k");
        await page.waitForURL(origin + route);
        await page
          .getByRole("status")
          .filter({
            hasText:
              "You resolved the Search conflict and ran the example binding.",
          })
          .waitFor();
        await page.goto(origin + "/settings?section=shortcuts");
        await binding("app.search")
          .getByRole("button", {
            name: "Change keys for Search library",
            exact: true,
          })
          .click();
        editor = page.getByRole("dialog", {
          name: "Change shortcut: Search library",
          exact: true,
        });
        await editor
          .getByRole("textbox", { name: "Key combination 1", exact: true })
          .fill("CtrlOrMeta+J");
        const remapped = page.waitForResponse(
          (item) =>
            item.url().endsWith("/api/preferences") &&
            item.request().method() === "PATCH",
        );
        await editor
          .getByRole("button", { name: "Save & enable", exact: true })
          .click();
        assert.equal((await remapped).status(), 200);
        await editor.waitFor({ state: "hidden" });
        assert.equal(
          await binding("app.search").getByRole("checkbox").isChecked(),
          true,
        );
        await page.locator("h1").first().click();
        await page.keyboard.press("Control+j");
        const search = page.getByRole("dialog", {
          name: "Search library",
          exact: true,
        });
        await search.waitFor();
        await page.keyboard.press("Escape");
        await search.waitFor({ state: "hidden" });
        await page.goto(origin + route);
        await page
          .getByRole("button", { name: "Add random shortcut", exact: true })
          .click();
        const random = page.locator(".shortcut-playground li").first();
        const keys = await random.locator("kbd").innerText();
        const label = await random.locator("strong").innerText();
        await page.keyboard.press(keys.replaceAll(" ", ""));
        await page
          .getByRole("status")
          .filter({ hasText: /Random shortcut .* ran/ })
          .waitFor();
        await random
          .getByRole("button", { name: /^Remove random shortcut/ })
          .click();
        await page.goto(origin + "/settings?section=shortcuts");
        assert.equal(await page.getByText(label, { exact: true }).count(), 0);
        if (width === 1440) {
          const before = await (
            await context.request.get(origin + "/api/preferences")
          ).json();
          assert.equal(
            (
              await context.request.post(
                origin + `/api/plugins/${pluginId}/disable`,
              )
            ).status(),
            200,
          );
          await binding(shortcutId).waitFor({
            state: "detached",
            timeout: 15000,
          });
          assert.equal(
            (
              await context.request.post(
                origin + `/api/plugins/${pluginId}/enable`,
              )
            ).status(),
            200,
          );
          await page.reload();
          await binding(shortcutId).waitFor({ state: "attached" });
          const after = await (
            await context.request.get(origin + "/api/preferences")
          ).json();
          assert.equal(
            after.keyboard_shortcut_overrides[shortcutId].enabled_order,
            before.keyboard_shortcut_overrides[shortcutId].enabled_order,
          );
        }
        assert.deepEqual(errors, []);
        report.passed.push(
          `Oldest-enabled plugin/core ownership, linked remap, saved disabling/reload, random keys and cleanup: ${width}/${theme}`,
        );
      } catch (error) {
        await page.screenshot({
          path: path.join(
            evidenceRoot,
            "shortcut-priority-private-failure.png",
          ),
        });
        console.error(
          JSON.stringify({
            errors,
            notice: await notice.allTextContents(),
            dialogs: await page.locator("dialog[open]").allTextContents(),
          }),
        );
        throw error;
      } finally {
        await context.close();
      }
    }
  } finally {
    await admin.request.patch(origin + "/api/preferences", { data: saved });
  }
}
