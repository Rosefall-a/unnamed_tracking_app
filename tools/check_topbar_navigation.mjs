import assert from "node:assert/strict";
import path from "node:path";

export async function checkTopbarNavigation({ admin, origin, evidenceRoot, report, checkOverflow }) {
  async function json(response, status = 200) { assert.equal(response.status(), status, await response.text()); return response.json(); }
  const original = await json(await admin.request.get(origin + "/api/preferences"));
  const created = [];
  const page = await admin.newPage(); const errors = []; page.on("pageerror", error => errors.push(String(error)));
  try {
    for (const title of ["A new episode is ready", "Your movie release reminder"]) {
      const notification = await json(await admin.request.post(origin + "/api/notifications/test", { data: { kind: "movie_released", media_type: "movie", title, body: "Real notification for palette and keyboard review." } }), 201); created.push(notification.id);
    }
    for (const palette of ["orange", "green", "custom"]) {
      await json(await admin.request.patch(origin + "/api/preferences", { data: { ui_palette: palette } }));
      for (const theme of ["light", "dark"]) {
        await json(await admin.request.patch(origin + "/api/preferences", { data: { ui_theme: theme } }));
        for (const width of report.widths) {
          await page.setViewportSize({ width, height: 880 }); await page.goto(origin + "/statistics");
          const bell = page.getByRole("button", { name: "Notifications", exact: true }); await bell.click();
          const panel = page.getByRole("region", { name: "Recent notifications", exact: true }); await panel.waitFor();
          await panel.getByText("A new episode is ready", { exact: true }).waitFor();
          assert(await panel.locator('.notification-row').evaluateAll(rows => rows.every((row, index) => index === 0 || rows[index - 1].getBoundingClientRect().bottom <= row.getBoundingClientRect().top + 1)), "Scrollable notification rows never overlap");
          assert(await panel.evaluate(element => element.contains(document.activeElement)), "Opening the popup moves keyboard focus to its controls");
          const colors = await panel.evaluate(element => {
            const sample = document.createElement('span'); sample.style.color = 'var(--ui-text)'; sample.style.backgroundColor = 'var(--ui-popover)'; element.append(sample);
            const actual = [getComputedStyle(element).color, getComputedStyle(element).backgroundColor]; const expected = [getComputedStyle(sample).color, getComputedStyle(sample).backgroundColor]; sample.remove(); return { actual, expected };
          }); assert.deepEqual(colors.actual, colors.expected, "The popup follows text and popover palette roles");
          const selected = await bell.evaluate(element => {
            const sample = document.createElement('span'); sample.style.color = 'var(--ui-on-accent)'; sample.style.backgroundColor = 'var(--ui-accent)'; element.append(sample);
            const actual = [getComputedStyle(element).color, getComputedStyle(element).backgroundColor]; const expected = [getComputedStyle(sample).color, getComputedStyle(sample).backgroundColor]; sample.remove(); return { actual, expected, width: element.clientWidth, height: element.clientHeight };
          }); assert.deepEqual(selected.actual, selected.expected, "Selected bell uses a solid accent and contrasting icon"); assert(selected.width >= 44 && selected.height >= 44);
          const bounds = await panel.boundingBox(); assert(bounds.x >= 0 && bounds.x + bounds.width <= width + 1);
          await checkOverflow(page, `notifications/${palette}/${theme}/${width}`);
          if (palette === "green" && [390, 1440].includes(width)) await page.screenshot({ path: path.join(evidenceRoot, `stage-notifications-${width}-${theme}.png`) });
          await page.keyboard.press("Escape"); await panel.waitFor({ state: "hidden" }); assert(await bell.evaluate(element => element === document.activeElement));
          report.screens.push({ palette, theme, width, screen: "notifications-popup" });
        }
      }
    }
    await page.setViewportSize({ width: 1024, height: 880 }); await page.goto(origin + "/statistics");
    await page.getByRole("button", { name: "Expand navigation", exact: true }).click();
    await page.locator('#app-navigation').getByRole('button', { name: 'Games', exact: true }).click();
    await page.locator('#app-navigation').getByRole('link', { name: 'All games', exact: true }).click();
    await page.waitForURL(origin + "/games"); await page.getByRole("button", { name: "Expand navigation", exact: true }).waitFor();
    assert(await page.locator('#app-navigation').evaluate(element => element.classList.contains('collapsed')));
    await page.getByRole("button", { name: "Expand navigation", exact: true }).click();
    await page.locator('#app-navigation').getByRole('link', { name: 'All games', exact: true }).click();
    await page.getByRole("button", { name: "Expand navigation", exact: true }).waitFor();
    assert.deepEqual(errors, []);
    report.passed.push("48 populated notification popup cases across eight widths, three palettes and both themes", "Solid selected-bell colors, 44px targets, semantic popup colors and Escape focus return", "Expanded icon rail collapses after navigation and selecting the current page");
  } finally {
    for (const id of created) await admin.request.delete(`${origin}/api/notifications/${id}`);
    await admin.request.patch(origin + "/api/preferences", { data: { ui_theme: original.ui_theme, ui_palette: original.ui_palette } });
    await page.close();
  }
}
