// Real application acceptance for the shared Games, Collections, Cards, Sets and Bounties UI.
import assert from "node:assert/strict";
import path from "node:path";

export async function checkContentUi({ admin, member, origin, evidenceRoot, report, checkOverflow }) {
  const gameIds = [], cardIds = [], setIds = [], bountyIds = [], errors = [];
  const originals = [];
  async function json(response, status) {
    assert.equal(response.status(), status, await response.text());
    return response.json();
  }
  async function settled(page, title, theme) {
    await page.getByRole("heading", { name: title, exact: true, level: 1 }).waitFor();
    await page.waitForFunction(theme => document.documentElement.dataset.theme === theme, theme);
    await page.waitForFunction(() => !Array.from(document.querySelectorAll("main p, main .empty-state")).some(element => element.textContent.trim() === "Loading…"));
  }
  async function modal(page, opener, title, label) {
    await opener.click();
    const dialog = page.getByRole("dialog", { name: title, exact: true });
    await dialog.waitFor();
    const box = await dialog.boundingBox(), viewport = page.viewportSize();
    assert(box.x >= 0 && box.y >= 0 && box.x + box.width <= viewport.width + 1 && box.y + box.height <= viewport.height + 1, `${label}: dialog fits the viewport`);
    for (let index = 0; index < 15; index++) {
      await page.keyboard.press("Tab");
      assert(await dialog.evaluate(element => element.contains(document.activeElement)), `${label}: focus is contained`);
    }
    await page.keyboard.press("Escape");
    await dialog.waitFor({ state: "hidden" });
    assert(await opener.evaluate(element => element === document.activeElement), `${label}: focus returns to opener`);
  }
  try {
    for (const [index, status] of ["PLAYING", "BEATEN", "MASTERED"].entries()) {
      const game = await json(await admin.request.post(origin + "/api/game/create", { data: {
        title: ["A quiet adventure", "The long way home", "A collection worth keeping"][index],
        folder_location: `ui-content-2693-${Date.now()}-${index}`, status, collections: ["Weekend/Adventures"], favorite: index === 0,
        description: "Disposable real library data for responsive acceptance.",
      } }), 201);
      gameIds.push(game.id);
    }
    const fixtureCard = await json(await admin.request.post(origin + "/api/cards", { data: { game_id: gameIds[2], rarity: "rare" } }), 201);
    cardIds.push(fixtureCard.id);
    const fixtureSet = await json(await admin.request.post(origin + "/api/sets", { data: { name: "Weekend adventures", target_total: 3 } }), 201);
    setIds.push(fixtureSet.id);
    const { bounty: fixtureBounty } = await json(await admin.request.post(origin + "/api/bounties", { data: { title: "Finish a quiet adventure", type: "challenge", game_id: gameIds[0], progress_target: 5 } }), 200);
    bountyIds.push(fixtureBounty.id);
    for (const [role, context] of [["admin", admin], ["member", member]]) {
      originals.push([context, await json(await context.request.get(origin + "/api/preferences"), 200)]);
      const page = await context.newPage();
      page.on("pageerror", error => errors.push(String(error)));
      for (const theme of ["light", "dark"]) {
        await json(await context.request.patch(origin + "/api/preferences", { data: { ui_theme: theme } }), 200);
        for (const width of report.widths) {
          await page.setViewportSize({ width, height: width <= 430 ? 880 : 1050 });
          let titleStyle;
          for (const [route, title] of [["games", "Games"], ["collections", "Collections"], ["cards", "Cards"], ["sets", "Sets"], ["bounties", "Bounties"]]) {
            await page.goto(origin + "/" + route);
            await settled(page, title, theme);
            const style = await page.locator("main h1").evaluate(element => { const style = getComputedStyle(element); return [style.fontSize, style.fontWeight, style.lineHeight, style.letterSpacing]; });
            if (titleStyle) assert.deepEqual(style, titleStyle, `${role}/${width}/${theme}: consistent page title`);
            titleStyle = style;
            try { await checkOverflow(page, `${route}/${role}/${width}/${theme}`); }
            catch (error) {
              console.error(await page.locator("main *").evaluateAll(elements => elements.map(element => ({ tag: element.tagName, class: element.className, right: element.getBoundingClientRect().right, width: element.getBoundingClientRect().width })).filter(item => item.right > innerWidth + 1)));
              await page.screenshot({ path: path.join(evidenceRoot, "diagnostic-overflow.png") });
              throw error;
            }
            assert.equal(await page.getByRole("link", { name: "Administration", exact: true }).count(), role === "admin" && width > 760 ? 1 : 0);
            report.screens.push({ width, theme, role, screen: title });
            if (route === "collections") await modal(page, page.getByRole("button", { name: "Smart collection", exact: true }), "New smart collection", route);
            if (route === "cards") await modal(page, page.getByRole("button", { name: "New card", exact: true }), "New card", route);
            if (route === "bounties") await modal(page, page.getByRole("button", { name: "+ New Bounty", exact: true }), "New bounty", route);
            if (role === "admin" && [390, 1440].includes(width)) await page.screenshot({ path: path.join(evidenceRoot, `stage-content-${route}-${width}-${theme}.png`), fullPage: width > 430 });
          }
          if (role === "admin") {
            await page.goto(origin + "/games");
            await settled(page, "Games", theme);
            for (const view of ["Cards view", "List view", "List and preview view", "Shelves view"]) {
              await page.getByRole("button", { name: view, exact: true }).click();
              await checkOverflow(page, `${view}/${width}/${theme}`);
              assert(await page.getByRole("button", { name: view, exact: true }).getAttribute("aria-pressed") === "true");
              if (view === "List view") {
                await page.locator(".list-row").first().waitFor();
                assert.equal(await page.locator(".list-row").count(), gameIds.length);
                await page.locator(".list-row").first().getByRole("button", { name: "A collection worth keeping", exact: true }).waitFor();
                if (width === 390) assert.equal(await page.locator(".list-header").isVisible(), false);
                if ([390, 1440].includes(width)) await page.screenshot({ path: path.join(evidenceRoot, `stage-content-game-list-${width}-${theme}.png`), fullPage: width > 430 });
              }
            }
            await page.getByRole("button", { name: "Cards view", exact: true }).click();
            const genre = page.getByRole("combobox", { name: "Genre", exact: true });
            await genre.focus();
            await page.keyboard.press("ArrowDown");
            await page.keyboard.press("Enter");
            assert.equal(await genre.getAttribute("aria-expanded"), "false");
            assert(await genre.evaluate(element => element === document.activeElement), "Keyboard filter selection retains focus");
            await genre.fill("No matching genre");
            await page.getByText("No matches", { exact: true }).waitFor();
            await page.keyboard.press("Escape");
            assert.equal(await genre.getAttribute("aria-expanded"), "false");
            await page.keyboard.press("ArrowDown");
            await page.keyboard.press("Enter");
            assert.equal(await genre.inputValue(), "All genres");
            await page.getByRole("combobox", { name: "Filter by status", exact: true }).selectOption("all");
          }
        }
      }
      await page.close();
    }
    const page = await admin.newPage();
    page.on("pageerror", error => errors.push(String(error)));
    await page.setViewportSize({ width: 390, height: 880 });
    await page.goto(origin + "/sets");
    await page.getByLabel("New set name", { exact: true }).fill("An actual set created on a phone");
    await page.getByLabel("Expected card total (optional)", { exact: true }).fill("7");
    const setResponse = page.waitForResponse(response => response.url().endsWith("/api/sets") && response.request().method() === "POST");
    await page.getByRole("button", { name: "+ Create Set", exact: true }).click();
    const createdSet = await json(await setResponse, 201); setIds.push(createdSet.id);
    assert.equal(createdSet.target_total, 7);
    await page.getByRole("heading", { name: createdSet.name, exact: true }).waitFor();
    await page.goto(origin + "/bounties");
    await page.getByRole("button", { name: "+ New Bounty", exact: true }).click();
    const bountyDialog = page.getByRole("dialog", { name: "New bounty", exact: true });
    await bountyDialog.getByLabel("Title", { exact: true }).fill("A real personal goal from a phone");
    await bountyDialog.getByRole("combobox", { name: "Bounty type", exact: true }).selectOption("custom");
    const bountyResponse = page.waitForResponse(response => response.url().endsWith("/api/bounties") && response.request().method() === "POST");
    await bountyDialog.getByRole("button", { name: "Create", exact: true }).click();
    const { bounty: createdBounty } = await json(await bountyResponse, 200); bountyIds.push(createdBounty.id);
    await bountyDialog.waitFor({ state: "hidden" });
    await page.getByText(createdBounty.title, { exact: true }).waitFor();
    await page.goto(origin + "/cards");
    await page.getByRole("button", { name: "New card", exact: true }).click();
    const cardDialog = page.getByRole("dialog", { name: "New card", exact: true });
    await cardDialog.getByRole("textbox", { name: "Search eligible games", exact: true }).fill("The long way home");
    const cardResponse = page.waitForResponse(response => response.url().endsWith("/api/cards") && response.request().method() === "POST");
    await cardDialog.getByRole("button", { name: "Create", exact: true }).click();
    const createdCard = await json(await cardResponse, 201); cardIds.push(createdCard.id);
    await page.waitForURL(origin + "/cards/" + createdCard.id);
    assert.equal(createdCard.game_id, gameIds[1]);
    await page.goto(origin + "/collections");
    await page.getByRole("button", { name: "Smart collection", exact: true }).click();
    const smartDialog = page.getByRole("dialog", { name: "New smart collection", exact: true });
    await smartDialog.getByLabel("Name", { exact: true }).fill("Favorites for the weekend");
    await smartDialog.getByRole("combobox", { name: "Smart collection rule", exact: true }).selectOption("favorite");
    await smartDialog.getByRole("button", { name: "Create", exact: true }).click();
    await smartDialog.waitFor({ state: "hidden" });
    const smartOpen = page.getByRole("button", { name: "Open collection Favorites for the weekend", exact: true });
    await smartOpen.waitFor();
    assert.equal(await page.getByRole("button", { name: "Delete smart collection Favorites for the weekend", exact: true }).evaluate(element => getComputedStyle(element).opacity), "1", "Phone collection actions remain visible without hover");
    assert.equal(await page.locator("button button").count(), 0, "Collection controls do not nest interactive buttons");
    await page.screenshot({ path: path.join(evidenceRoot, "stage-content-smart-collections-390-dark.png") });
    await smartOpen.focus();
    await page.keyboard.press("Enter");
    await page.waitForURL(/\/collections\//);
    await page.goBack();
    const smartDelete = page.getByRole("button", { name: "Delete smart collection Favorites for the weekend", exact: true });
    await smartDelete.focus();
    await page.keyboard.press("Enter");
    const deleteDialog = page.getByRole("dialog", { name: "Delete smart collection", exact: true });
    await deleteDialog.getByRole("button", { name: "Delete", exact: true }).click();
    await smartOpen.waitFor({ state: "hidden" });
    assert.equal(new URL(page.url()).pathname, "/collections", "Deleting a rule does not open its collection");
    await page.close();
    assert.deepEqual(errors, []);
    report.passed.push("160 real content page/theme/width/role cases", "Four preserved Games views at all eight widths in both themes", "Shared page title typography", "Native collection/card/bounty dialogs contain focus, fit viewport and restore focus on Escape", "Keyboard filter selection and Escape retain input focus", "Phone Games list retains every field and action without horizontal scrolling", "Real phone set, bounty and eligible-game card creation", "Actual smart collection creation, keyboard open/deep link and separate keyboard deletion", "No JavaScript errors or document/page overflow");
  } finally {
    for (const [context, original] of originals) await context.request.patch(origin + "/api/preferences", { data: { ui_theme: original.ui_theme } });
    for (const id of cardIds) await admin.request.delete(origin + `/api/cards/${id}`);
    for (const id of setIds) await admin.request.delete(origin + `/api/sets/${id}`);
    for (const id of bountyIds) await admin.request.delete(origin + `/api/bounties/${id}`);
    for (const id of gameIds) await admin.request.delete(origin + `/api/game/delete/${id}`);
  }
}
