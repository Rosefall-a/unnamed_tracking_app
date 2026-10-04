// Called by check_ui_redevelopment.mjs with the same real-backend proxy and clean inventory.
import assert from "node:assert/strict";
import path from "node:path";

export async function checkHomeWidgets({ admin, member, origin, evidenceRoot, report, checkOverflow }) {
  const page = await admin.newPage();
  const errors = [];
  page.on("pageerror", error => errors.push(String(error)));
  const original = await (await admin.request.get(origin + "/api/preferences")).json();
  const gameIds = [];
  const ids = ["continue-playing", "library-summary", "goals", "weekly-digest", "collection:Weekend", "recently-added", "backlog", "on-this-day", "random-picker", "getting-started"];
  try {
    for (const [index, title] of ["A quiet adventure", "The long way home"].entries()) {
      const response = await admin.request.post(origin + "/api/game/create", { data: {
        title, folder_location: `ui-widget-check-${Date.now()}-${index}`, status: index ? "BACKLOG" : "PLAYING", collections: ["Weekend"], favorite: !index,
        description: "Disposable public review data for Home widget acceptance.",
      } });
      assert.equal(response.status(), 201, await response.text());
      gameIds.push((await response.json()).id);
    }
    for (const theme of ["light", "dark"]) {
      for (const width of report.widths) {
        await page.setViewportSize({ width, height: width <= 430 ? 880 : 1050 });
        assert.equal((await admin.request.patch(origin + "/api/preferences", { data: { ui_theme: theme, ui_reduce_motion: false, home_widgets: [] } })).status(), 200);
        await page.goto(origin);
        await page.getByRole("heading", { name: "Make yourself at home.", exact: true }).waitFor();
        await page.waitForFunction(expected => document.documentElement.dataset.theme === expected, theme);
        assert.equal(await page.locator(".home-widget").count(), 0);
        assert.equal(await page.getByRole("dialog").count(), 0, "Minimal Home never forces a welcome dialog.");
        await checkOverflow(page, `minimal Home/${width}/${theme}`);
        report.screens.push({ width, theme, screen: "minimal Home" });
        if ([390, 1440].includes(width)) await page.screenshot({ path: path.join(evidenceRoot, `stage-home-minimal-${width}-${theme}.png`), fullPage: width > 430 });
        const add = page.getByRole("button", { name: "Add widgets", exact: true });
        await add.click();
        const picker = page.getByRole("dialog", { name: "Customize Home", exact: true });
        await picker.getByRole("checkbox", { name: "Weekend", exact: false }).waitFor();
        for (const name of ["Continue playing", "Library summary", "Goals & bounties", "This week", "Weekend"]) await picker.getByRole("checkbox", { name, exact: false }).check();
        await picker.getByRole("button", { name: "Move Weekend up", exact: true }).click();
        const desired = ["continue-playing", "library-summary", "goals", "collection:Weekend", "weekly-digest"];
        for (let index = 0; index < 32; index++) {
          await page.keyboard.press("Tab");
          assert(await picker.evaluate(element => element.contains(document.activeElement)), "Widget chooser focus remains inside.");
        }
        const bounds = await picker.boundingBox();
        assert(bounds.x >= 0 && bounds.x + bounds.width <= width + 1, "Widget chooser fits viewport.");
        await checkOverflow(page, `Home chooser/${width}/${theme}`);
        report.screens.push({ width, theme, screen: "widget chooser" });
        if (width === 390) await page.screenshot({ path: path.join(evidenceRoot, `stage-home-chooser-${width}-${theme}.png`) });
        await picker.getByRole("button", { name: "Save Home", exact: true }).click();
        await picker.waitFor({ state: "hidden" });
        await page.getByText("Home saved to your account.", { exact: true }).waitFor();
        assert.deepEqual((await (await admin.request.get(origin + "/api/preferences")).json()).home_widgets, desired);
        await page.reload();
        await page.locator('.home-widget[data-widget-id="continue-playing"] .game-card-wrap').first().waitFor();
        await page.waitForFunction(() => !document.querySelector(".widget-loading"));
        assert.deepEqual(await page.locator(".home-widget").evaluateAll(elements => elements.map(element => element.dataset.widgetId)), desired);
        await checkOverflow(page, `personal Home/${width}/${theme}`);
        report.screens.push({ width, theme, screen: "personal Home" });
        if ([390, 1024, 1440].includes(width)) await page.screenshot({ path: path.join(evidenceRoot, `stage-home-widgets-${width}-${theme}.png`), fullPage: width > 430 });
        await page.getByRole("button", { name: "Quick tour", exact: true }).click();
        const tour = page.getByRole("dialog", { name: "A quick tour of your library", exact: true });
        await tour.waitFor();
        await page.keyboard.press("Escape");
        await tour.waitFor({ state: "hidden" });
        assert(await page.getByRole("button", { name: "Quick tour", exact: true }).evaluate(element => element === document.activeElement), "Tour restores its opening control.");
      }
    }
    // Real network failure: keep the draft in the chooser and retry after reconnecting.
    await page.getByRole("button", { name: "Customize Home", exact: true }).click();
    const picker = page.getByRole("dialog", { name: "Customize Home", exact: true });
    await picker.getByRole("checkbox", { name: "Recently added", exact: false }).check();
    await admin.setOffline(true);
    await picker.getByRole("button", { name: "Save Home", exact: true }).click();
    await picker.getByRole("alert").waitFor();
    assert(await picker.getByRole("checkbox", { name: "Recently added", exact: false }).isChecked());
    await admin.setOffline(false);
    await picker.getByRole("button", { name: "Save Home", exact: true }).click();
    await picker.waitFor({ state: "hidden" });
    assert((await (await admin.request.get(origin + "/api/preferences")).json()).home_widgets.includes("recently-added"));

    // The absent plugin selection remains stored and has an explicit unavailable state.
    assert.equal((await admin.request.patch(origin + "/api/preferences", { data: { home_widgets: [...ids, "plugin:temporarily-disabled:progress"] } })).status(), 200);
    await page.reload();
    await page.locator('.home-widget[data-widget-id="plugin:temporarily-disabled:progress"]').getByText("This widget is unavailable. Your selection is retained until it returns or you remove it.", { exact: true }).waitFor();
    await page.waitForFunction(() => !document.querySelector(".widget-loading"));
    for (const id of ids) assert.equal(await page.locator(`.home-widget[data-widget-id="${id}"]`).count(), 1);
    await page.setViewportSize({ width: 390, height: 880 });
    const playing = page.locator('.home-widget[data-widget-id="continue-playing"]');
    const favoriteSaved = page.waitForResponse(response => response.url().endsWith(`/api/game/update/${gameIds[0]}`) && response.request().method() === "PATCH");
    await playing.getByRole("button", { name: "Unfavorite A quiet adventure", exact: true }).click();
    assert.equal((await favoriteSaved).status(), 200);
    await playing.getByRole("button", { name: "Favorite A quiet adventure", exact: true }).waitFor();
    assert.equal((await (await admin.request.get(origin + `/api/game/get/${gameIds[0]}`)).json()).favorite, false);
    const actions = playing.getByRole("button", { name: "Actions for A quiet adventure", exact: true });
    await actions.click();
    const menu = page.getByRole("group", { name: "Actions for A quiet adventure", exact: true });
    await menu.waitFor();
    const menuBounds = await menu.boundingBox();
    assert(menuBounds.x >= 0 && menuBounds.x + menuBounds.width <= 391);
    assert(menuBounds.y >= 0 && menuBounds.y + menuBounds.height <= 881);
    await page.keyboard.press("Escape");
    await menu.waitFor({ state: "hidden" });
    assert(await actions.evaluate(element => element === document.activeElement));
    assert.equal((await admin.request.patch(origin + "/api/preferences", { data: { home_widgets: ["goals", "goals"] } })).status(), 422);
    assert((await (await admin.request.get(origin + "/api/preferences")).json()).home_widgets.includes("plugin:temporarily-disabled:progress"));

    // Separate account starts minimal, and changing its Home never changes the administrator's.
    assert.deepEqual((await (await member.request.get(origin + "/api/preferences")).json()).home_widgets, []);
    const memberPage = await member.newPage();
    await memberPage.goto(origin);
    await memberPage.getByRole("button", { name: "Add widgets", exact: true }).click();
    const memberPicker = memberPage.getByRole("dialog", { name: "Customize Home", exact: true });
    await memberPicker.getByRole("checkbox", { name: "Goals & bounties", exact: false }).check();
    await memberPicker.getByRole("button", { name: "Save Home", exact: true }).click();
    await memberPicker.waitFor({ state: "hidden" });
    assert.deepEqual((await (await member.request.get(origin + "/api/preferences")).json()).home_widgets, ["goals"]);
    assert((await (await admin.request.get(origin + "/api/preferences")).json()).home_widgets.includes("plugin:temporarily-disabled:progress"));
    await memberPage.close();
    assert.deepEqual(errors, []);
    report.passed.push("48 real Home/theme/width cases", "Widget selection and button ordering persist after reload", "Personal Home is isolated between accounts", "Real offline save failure preserves draft and retries", "Unavailable plugin selection retained", "All original core Home features selectable", "Native chooser/tour keyboard containment and focus restoration", "Real card favorite change, contained phone action menu and Escape focus return", "No forced welcome tour, page overflow or JavaScript errors");
  } finally {
    await admin.setOffline(false);
    await admin.request.patch(origin + "/api/preferences", { data: { home_widgets: original.home_widgets, ui_theme: original.ui_theme, ui_reduce_motion: original.ui_reduce_motion } });
    for (const id of gameIds) await admin.request.delete(origin + `/api/game/delete/${id}`);
    await page.close();
  }
}
