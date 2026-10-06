// Real owned records, rendered layout measurements and touch actions; no API mocks.
import assert from "node:assert/strict";
import path from "node:path";

export async function checkLibraryLayouts({ browser, admin, origin, evidenceRoot, report, checkOverflow }) {
  const before = await (await admin.request.get(origin + "/api/preferences")).json();
  const widths = [320, 390, 430, 760, 768, 1024, 1440, 1920];
  report.widths = widths;
  report.browser = browser.browserType().name();
  const records = [], suffix = Date.now();
  const titles = ["Tiny dragons, enormous plans", "Orbital tea party", "Dungeons & paperwork", "Captain Side Quest", "Save Point Sundays", "Moonlight Mechanic", "Attack of the backlog", "Pixel Pigeon Patrol", "Do Not Feed the Boss"];
  const libraries = [["game", "/games", "Games"], ["movie", "/movies", "Movies"], ["tv", "/tv", "TV Shows"], ["anime", "/anime", "Anime"]];
  async function ready(check, label) {
    const deadline = Date.now() + 5000;
    while (Date.now() < deadline) {
      if (await check()) return;
      await new Promise(resolve => setTimeout(resolve, 50));
    }
    assert(await check(), label);
  }
  try {
    for (const [kind] of libraries) for (let i = 0; i < 9; i++) {
      const response = await admin.request.post(`${origin}/api/${kind}/create`, { data: {
        title: titles[i],
        ...(kind === "game" ? { folder_location: `layout-${suffix}-${i}` } : {}),
      } });
      assert.equal(response.status(), 201, await response.text());
      records.push([kind, (await response.json()).id]);
    }
    for (const width of widths) for (const theme of ["light", "dark"]) {
      const height = width <= 760 ? 600 : 900;
      await admin.request.patch(origin + "/api/preferences", { data: { ui_theme: theme } });
      const context = await browser.newContext({ storageState: await admin.storageState(), viewport: { width, height }, hasTouch: width <= 760 });
      const page = await context.newPage(), errors = [];
      page.on("pageerror", error => errors.push(String(error)));
      try {
        for (const [kind, route, title] of libraries) {
          await page.goto(origin + route);
          await page.getByRole("heading", { name: title, exact: true, level: 1 }).waitFor();
          const modes = kind === "game" ? ["Shelves", "List", "Preview"] : ["Shelf", "List", "Board"];
          for (const mode of modes) {
            await page.getByRole("button", { name: mode, exact: true }).click();
            const cardView = mode === "Shelves" || mode === "Shelf" || mode === "Board";
            if (cardView) for (const [density, columns] of [["S", 3], ["M", 2], ["L", 1]]) {
              await page.getByRole("button", { name: density, exact: true }).click();
              const grid = page.locator(mode === "Shelves" ? ".grid-row" : mode === "Shelf" ? ".shelf-grid" : ".board-shelf").first();
              await grid.waitFor();
              if (width <= 760) await ready(async () => {
                const count = await grid.evaluate(element => element.classList.contains("board-shelf") ? element.children.length : getComputedStyle(element).gridTemplateColumns.split(" ").length);
                return count === columns;
              }, `${kind}/${mode}/${density}/${width}: distinct phone column count`);
              await checkOverflow(page, `${kind}/${mode}/${density}/${theme}/${width}`);
              const searchBounds = await page.locator('[data-shortcut="search"]').boundingBox();
              assert(searchBounds.x >= 0 && searchBounds.x + searchBounds.width <= width + 1, "Library search remains on screen");
              const overflows = await page.locator(".game-card, .shelf-card, .board-card").evaluateAll(elements => elements.filter(element => element.scrollWidth > element.clientWidth + 1).map(element => ({ class: element.className, width: element.clientWidth, scroll: element.scrollWidth })));
              assert.deepEqual(overflows, [], `${kind}/${mode}/${density}/${theme}/${width}: card content must fit`);
              if (density === "S" && (width === 390 && theme === "dark" || width === 1440 && theme === "light")) {
                const filename = `library-${kind}-${mode.toLowerCase()}-${width}-${theme}.png`;
                await page.evaluate(() => window.scrollTo(0, 0));
                await page.evaluate(() => Promise.all(document.getAnimations().filter(animation => animation.effect?.getTiming().iterations !== Infinity).map(animation => animation.finished.catch(() => {}))));
                await page.waitForTimeout(200); // Let the selected-tab color transition finish in captures.
                await page.screenshot({ path: path.join(evidenceRoot, filename) }); report.screens.push(filename);
              }
              if (density === "S" && width <= 430) {
                const action = page.getByRole("button", { name: /^Actions for / }).first();
                const bounds = await action.boundingBox(); assert(bounds.width >= 44 && bounds.height >= 44);
                await action.click();
                const dialog = page.getByRole("dialog", { name: /^Actions for / }); await dialog.waitFor();
                await dialog.getByRole("button", { name: "Add favorite", exact: true }).waitFor();
                await checkOverflow(page, `${kind} touch actions/${theme}/${width}`);
                await page.keyboard.press("Escape"); await dialog.waitFor({ state: "hidden" });
              }
            }
            else {
              await page.locator(mode === "Preview" ? ".detail-preview" : kind === "game" ? ".list-row" : ".list-row").first().waitFor();
              await checkOverflow(page, `${kind}/${mode}/${theme}/${width}`);
              if (mode === "Preview") {
                await ready(() => page.locator(".detail-preview").evaluate(element => getComputedStyle(element).opacity === "1"), "Preview transition finishes");
                const title = page.locator(".detail-preview h2");
                await title.waitFor();
                const bounds = await page.locator(".detail-preview").boundingBox();
                const bottom = width <= 760 ? (await page.locator(".mobile-tabs").boundingBox()).y : height;
                assert(bounds.height >= 120 && bounds.y + bounds.height <= bottom + 1, `Preview fits the available screen: ${JSON.stringify({ width, bounds, bottom })}`);
                const titleBounds = await title.boundingBox();
                assert(titleBounds.y < bounds.y + bounds.height && titleBounds.y + titleBounds.height > bounds.y, "Selected game title is immediately visible inside the preview");
                if (width === 390 && theme === "dark" || width === 1440 && theme === "light") {
                  const filename = `library-game-preview-${width}-${theme}.png`;
                  await page.waitForTimeout(200);
                  await page.screenshot({ path: path.join(evidenceRoot, filename) }); report.screens.push(filename);
                }
                if (width <= 430) {
                  await page.locator("#main-content").focus(); await page.keyboard.press("/");
                  assert.equal(await page.locator('[data-shortcut="search"]').evaluate(element => element === document.activeElement), true);
                  await page.keyboard.press("Escape"); await page.keyboard.press("n");
                  const create = page.getByRole("dialog", { name: "Add Game", exact: true }); await create.waitFor();
                  await page.keyboard.press("Escape"); await create.waitFor({ state: "hidden" });
                  await page.getByRole("button", { name: "Library controls", exact: true }).click();
                  await page.getByRole("button", { name: "Random", exact: true }).waitFor();
                  await page.getByRole("button", { name: "Hide controls", exact: true }).click();
                }
              }
            }
            report.passed.push(`${kind} ${mode}: themed layout, card fit and density controls ${theme}/${width}`);
          }
          if (kind !== "game" && width <= 430) {
            await page.locator("#main-content").focus(); await page.keyboard.press("n");
            const create = page.getByRole("dialog"); await create.waitFor();
            await create.getByRole("textbox", { name: "Search media by title", exact: true }).waitFor();
            await page.keyboard.press("Escape"); await create.waitFor({ state: "hidden" });
            await page.getByRole("button", { name: "Library controls", exact: true }).click();
            await page.locator('[data-shortcut="create"]').waitFor();
            await page.getByRole("button", { name: "Hide controls", exact: true }).click();
          }
        }
        if (width <= 430) {
          const timings = [];
          for (let i = 0; i < 6; i++) {
            const name = i % 2 ? "Media" : "Games", heading = i % 2 ? "Movies" : "Games";
            const start = Date.now();
            await page.getByRole("navigation", { name: "Primary navigation" }).getByRole("link", { name, exact: true }).click();
            await page.getByRole("heading", { name: heading, exact: true, level: 1 }).waitFor();
            timings.push(Date.now() - start);
            assert.equal(await page.locator("dialog.navigation[open]").count(), 0);
          }
          assert(Math.max(...timings) < 1500, `Warm phone navigation responds promptly: ${timings}`);
          report.passed.push(`Warm phone Games/Media navigation ${theme}/${width}: ${timings.join(", ")} ms`);
        }
        assert.deepEqual(errors, []);
      } catch (error) {
        await page.screenshot({ path: path.join(evidenceRoot, `layout-failure-${width}-${theme}.png`), fullPage: true });
        throw error;
      } finally { await context.close(); }
    }
  } finally {
    for (const [kind, id] of records) {
      const removed = await admin.request.delete(`${origin}/api/${kind}/delete/${id}`);
      assert.equal(removed.status(), 204, `Delete only the ${kind} record created for this layout run`);
    }
    await admin.request.patch(origin + "/api/preferences", { data: before });
  }
}
