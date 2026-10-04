// Native save/edit/rating/picker/calendar interactions on disposable real data.
import assert from "node:assert/strict";
import path from "node:path";

export async function checkLibraryWorkflows({ admin, origin, evidenceRoot, report, checkOverflow }) {
  const before = await (await admin.request.get(origin + "/api/preferences")).json();
  const page = await admin.newPage(), games = [], movies = [], events = [], activity = [], errors = [];
  page.on("pageerror", error => errors.push(String(error)));
  async function dialog(name) {
    const item = page.getByRole("dialog", { name, exact: true }); await item.waitFor();
    assert(await item.evaluate(element => element instanceof HTMLDialogElement && element.open));
    for (let index = 0; index < 10; index++) {
      await page.keyboard.press("Tab"); assert(await item.evaluate(element => element.contains(document.activeElement)));
    }
    await checkOverflow(page, name); return item;
  }
  try {
    for (const theme of ["light", "dark"]) for (const width of [390, 1440]) {
      await admin.request.patch(origin + "/api/preferences", { data: { ui_theme: theme, library_default_layout: "list" } });
      await page.setViewportSize({ width, height: 1050 });
      await page.goto(origin + "/games"); await page.getByRole("heading", { name: "Games", exact: true }).waitFor();
      await page.locator("#main-content").focus(); await page.keyboard.press("n");
      const create = await dialog("Add Game"); await create.getByRole("button", { name: "Skip", exact: true }).click();
      const title = `The Quest for a Working Save Button ${width} ${theme}`;
      await create.getByLabel("Title", { exact: true }).fill(title);
      await create.getByLabel("Folder name", { exact: true }).fill(`ui-workflow-${width}-${theme}-${Date.now()}`);
      await create.getByRole("button", { name: "Ratings & Tags", exact: true }).click();
      await create.getByRole("spinbutton", { name: "Atmosphere", exact: true }).fill("8.5");
      await create.getByRole("spinbutton", { name: "Story", exact: true }).fill("7.5");
      await create.getByRole("button", { name: "Ownership", exact: true }).click();
      const saved = page.waitForResponse(response => new URL(response.url()).pathname === "/api/game/create" && response.request().method() === "POST");
      await create.getByRole("button", { name: "Add Game", exact: true }).click();
      const response = await saved; assert.equal(response.status(), 201, await response.text());
      const game = await response.json(); games.push(game.id); await create.waitFor({ state: "hidden" });
      await page.goto(origin + "/games/" + game.id); await page.getByRole("heading", { name: title, exact: true }).waitFor();
      await page.getByRole("button", { name: "Edit", exact: true }).first().click();
      const edit = await dialog("Edit Game");
      await edit.getByRole("button", { name: "General", exact: true }).click();
      await edit.getByLabel(/^Status/).selectOption("beaten");
      await edit.getByRole("button", { name: "Ratings & Tags", exact: true }).click();
      await edit.getByRole("spinbutton", { name: "Gameplay", exact: true }).fill("9.2");
      await edit.getByRole("button", { name: "Ownership", exact: true }).click();
      await edit.getByLabel("100% completion date", { exact: true }).fill("2026-10-05");
      const updated = page.waitForResponse(response => response.url().includes("/api/game/update/" + game.id) && response.request().method() === "PATCH");
      await edit.getByRole("button", { name: "Save Changes", exact: true }).click();
      assert.equal((await updated).status(), 200); await edit.waitFor({ state: "hidden" });
      const persisted = await (await admin.request.get(origin + "/api/game/get/" + game.id)).json();
      assert.equal(persisted.status, "BEATEN"); assert.equal(Number(persisted.rating_gameplay), 9.2); assert(persisted.completion_date);
      await page.getByRole("heading", { name: title, exact: true }).waitFor();
      await checkOverflow(page, `game save/completion/${width}/${theme}`);
      await page.screenshot({ path: path.join(evidenceRoot, `game-workflow-${width}-${theme}.png`) });
      await page.goto(origin + "/games"); await page.getByRole("button", { name: "Random", exact: true }).click();
      const picker = await dialog("Pick something to play");
      await picker.getByRole("button", { name: "Reset", exact: true }).click();
      await picker.getByRole("button", { name: "beaten", exact: true }).click();
      await picker.getByRole("button", { name: "Pick a game", exact: true }).click();
      await picker.getByRole("button", { name: "Open game", exact: true }).waitFor();
      await checkOverflow(page, `random picker/${width}/${theme}`);
      await page.screenshot({ path: path.join(evidenceRoot, `random-picker-${width}-${theme}.png`) });
      await page.keyboard.press("Escape"); await picker.waitFor({ state: "hidden" });
      const movieResponse = await admin.request.post(origin + "/api/movie/create", { data: { title: `A calendar-worthy movie ${theme} ${width}` } });
      assert.equal(movieResponse.status(), 201); const movie = await movieResponse.json(); movies.push(movie.id);
      await page.goto(origin + "/movies/" + movie.id); await page.locator(".rating-pill").waitFor();
      await page.locator(".rating-pill").click();
      const score = page.getByRole("dialog", { name: "Your score", exact: true });
      await score.getByLabel("Your score", { exact: true }).fill("11"); await score.getByRole("button", { name: "Save", exact: true }).click();
      await score.getByText("Enter a number from 0 to 10.", { exact: true }).waitFor();
      await score.getByLabel("Your score", { exact: true }).fill("8.5");
      const rated = page.waitForResponse(response => response.url().includes("/api/movie/update/" + movie.id) && response.request().method() === "PATCH");
      await score.getByRole("button", { name: "Save", exact: true }).click(); assert.equal((await rated).status(), 200);
      assert.equal(Number((await (await admin.request.get(origin + "/api/movie/get/" + movie.id)).json()).rating_overall), 8.5);
      await page.locator(".rating-pill").click();
      const cleared = page.waitForResponse(response => response.url().includes("/api/movie/update/" + movie.id) && response.request().method() === "PATCH");
      await score.getByRole("button", { name: "Clear", exact: true }).click(); assert.equal((await cleared).status(), 200);
      assert.equal((await (await admin.request.get(origin + "/api/movie/get/" + movie.id)).json()).rating_overall, null);
      await page.goto(origin + "/calendar"); await page.getByRole("button", { name: "+ Add Entry", exact: true }).click();
      const event = await dialog("Add a calendar entry");
      await event.getByLabel("Title", { exact: true }).fill(`A tiny celebration ${theme} ${width}`);
      await event.getByLabel("Date", { exact: true }).fill("2026-10-05");
      const added = page.waitForResponse(response => new URL(response.url()).pathname === "/api/calendar/events" && response.request().method() === "POST");
      await event.getByRole("button", { name: "Save", exact: true }).click();
      const entry = await added; assert.equal(entry.status(), 201); events.push((await entry.json()).id); await event.waitFor({ state: "hidden" });
      await page.getByRole("button", { name: "+ Log Watched", exact: true }).click();
      const history = await dialog("Log a history entry");
      await history.getByLabel("Title", { exact: true }).fill(movie.title);
      await history.locator(".modal-search-result").filter({ hasText: movie.title }).click();
      await history.getByLabel(/^What happened/).selectOption("rewatched");
      await history.getByLabel("Note (optional)", { exact: true }).fill("A real saved history entry");
      await page.screenshot({ path: path.join(evidenceRoot, `calendar-history-${width}-${theme}.png`) });
      const logged = page.waitForResponse(response => new URL(response.url()).pathname === "/api/activity" && response.request().method() === "POST");
      await history.getByRole("button", { name: "Log entry", exact: true }).click();
      const historyResponse = await logged; assert.equal(historyResponse.status(), 201); const entrySaved = await historyResponse.json(); activity.push(entrySaved.id);
      assert.equal(entrySaved.media_id, movie.id); assert.equal(entrySaved.detail, "A real saved history entry");
      await history.waitFor({ state: "hidden" });
      await page.getByRole("button", { name: "Subscribe", exact: true }).click();
      const feed = await dialog("Subscribe in your calendar app");
      await feed.getByRole("textbox", { name: "Calendar subscription link", exact: true }).waitFor();
      // Subscription credentials are never captured in public evidence.
      await page.keyboard.press("Escape"); await feed.waitFor({ state: "hidden" });
      report.screens.push({ theme, width, screen: "real game creation/edit/ratings/completion, random selection, calendar save/history/feed dialogs" });
    }
    assert.deepEqual(errors, []); report.passed.push("Four real game/calendar workflow cases across phone/desktop light/dark; persisted game saves, ratings and completion; movie rating bounds/save/clear; random picker; saved calendar events and manual history; shared dialog focus/Escape; subscription secret excluded from evidence");
  } finally {
    for (const id of events) await admin.request.delete(origin + "/api/calendar/events/" + id);
    for (const id of activity) await admin.request.delete(origin + "/api/activity/" + id);
    for (const id of movies) await admin.request.delete(origin + "/api/movie/delete/" + id);
    for (const id of games) await admin.request.delete(origin + "/api/game/delete/" + id);
    await admin.request.patch(origin + "/api/preferences", { data: { ui_theme: before.ui_theme, library_default_layout: before.library_default_layout } });
    await page.close();
  }
}
