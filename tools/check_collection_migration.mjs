// Verify main's collection redesign against disposable public-API data.
import assert from "node:assert/strict";
import path from "node:path";

export async function checkCollectionMigration({
  admin,
  origin,
  evidenceRoot,
  report,
  checkOverflow,
}) {
  const page = await admin.newPage(),
    games = [],
    movies = [],
    lists = [],
    errors = [];
  const before = await (
    await admin.request.get(origin + "/api/preferences")
  ).json();
  const suffix = crypto.randomUUID().slice(0, 8);
  const manualName = `Migration ${suffix}/Weekend quests`;
  const renamed = `Migration ${suffix}/After the rename`;
  let storageBefore;
  const storageKeys = [
    "manualCollections",
    "smartCollections",
    "collectionMeta",
    "collectionCoverPicks",
    "collectionGameOrder",
  ];
  page.on("pageerror", (error) => errors.push(String(error)));
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });
  async function request(method, route, data, expected = 200) {
    const response = await admin.request.fetch(origin + "/api" + route, {
      method,
      ...(data ? { data } : {}),
    });
    assert.equal(
      response.status(),
      expected,
      route +
        ": " +
        (response.status() === expected ? "" : await response.text()),
    );
    return expected === 204 ? null : response.json();
  }
  const card = (name) =>
    page
      .locator(".collection-card-wrap")
      .filter({ has: page.getByRole("button", { name, exact: true }) });
  async function nativeDialog(name, target = page) {
    const dialog = target.getByRole("dialog", { name, exact: true });
    await dialog.waitFor();
    assert(
      await dialog.evaluate(
        (element) => element instanceof HTMLDialogElement && element.open,
      ),
    );
    for (let index = 0; index < 8; index++) {
      await target.keyboard.press("Tab");
      assert(
        await dialog.evaluate((element) =>
          element.contains(document.activeElement),
        ),
        "Native modal contains keyboard focus",
      );
    }
    await checkOverflow(target, name);
    return dialog;
  }
  async function createCollection(name, rule) {
    await page.goto(origin + "/collections");
    await page
      .getByRole("button", { name: "+ Create Collection", exact: true })
      .click();
    const dialog = await nativeDialog("Create a collection");
    if (rule) {
      await dialog.getByRole("button", { name: /^Smart/ }).click();
      await dialog
        .getByRole("combobox", { name: /^Rule/ })
        .selectOption(rule.field);
      if (rule.field !== "favorite") {
        const value = dialog.getByRole(
          rule.field === "playtime_hours" ? "spinbutton" : "combobox",
          {
            name: {
              status: "Value",
              playtime_hours: "Hours",
              tag: "Tag",
              source: "Source",
            }[rule.field],
            exact: true,
          },
        );
        if (rule.field === "status") await value.selectOption(rule.value);
        else await value.fill(rule.value);
      }
    }
    await dialog.getByLabel("Name", { exact: false }).fill(name);
    await dialog
      .getByLabel("Description (optional)", { exact: true })
      .fill("Preserved collection workflow");
    await dialog.getByRole("button", { name: "Create", exact: true }).click();
    await dialog.waitFor({ state: "hidden" });
    await page.waitForURL(origin + "/collections/" + encodeURIComponent(name));
    await page.getByRole("heading", { level: 1 }).waitFor();
  }
  try {
    await page.goto(origin + "/collections");
    storageBefore = await page.evaluate(
      (keys) =>
        Object.fromEntries(keys.map((key) => [key, localStorage.getItem(key)])),
      storageKeys,
    );
    for (const [index, title] of [
      "Quest for the Missing Sock",
      "The Last Cup of Tea",
      "Revenge of the Loading Screen",
    ].entries()) {
      const game = await request(
        "POST",
        "/game/create",
        {
          title,
          folder_location: `migration-${suffix}-${index}`,
          status: index === 2 ? "BACKLOG" : "BEATEN",
          favorite: index === 0,
          tags: index === 0 ? ["migration-" + suffix] : [],
          source: index === 0 ? "migration-" + suffix : "other",
        },
        201,
      );
      games.push(game);
    }
    await request("PATCH", "/game/update/" + games[0].id, {
      playtime_seconds: 10800,
      rating_overall: 8.5,
    });
    await createCollection(manualName);
    const addButton = page.getByRole("button", {
      name: "+ Add Games",
      exact: true,
    });
    await addButton.click();
    let dialog = await nativeDialog("Add games");
    for (const game of games) {
      const saved = page.waitForResponse(
        (response) =>
          response.url().includes("/api/game/update/" + game.id) &&
          response.request().method() === "PATCH",
      );
      await dialog.locator(".add-row").filter({ hasText: game.title }).click();
      assert.equal((await saved).status(), 200);
    }
    await page.keyboard.press("Escape");
    await dialog.waitFor({ state: "hidden" });
    assert(
      await addButton.evaluate((element) => element === document.activeElement),
      "Native picker returns focus to Add Games",
    );
    assert.equal(await page.locator(".count-badge").innerText(), "3 games");
    await page.getByRole("button", { name: "Reorder", exact: true }).click();
    const initialOrder = await page.locator(".grid .title").allTextContents();
    assert.deepEqual(
      [...initialOrder].sort(),
      games.map((game) => game.title).sort(),
    );
    const expectedOrder = [initialOrder[1], initialOrder[0], initialOrder[2]];
    const expectedIds = expectedOrder.map(
      (title) => games.find((game) => game.title === title).id,
    );
    await page.getByTitle("Move later", { exact: true }).first().click();
    await page.getByRole("button", { name: "Done", exact: true }).click();
    await page.reload();
    await page.getByRole("heading", { level: 1 }).waitFor();
    const ordered = await page.locator(".grid .title").allTextContents();
    assert.deepEqual(ordered, expectedOrder);
    await page
      .locator(".item-card")
      .filter({ has: page.getByText(games[2].title, { exact: true }) })
      .getByTitle("Use as the collection cover", { exact: true })
      .click();
    const coverId = await page.evaluate(
      (name) => JSON.parse(localStorage.getItem("collectionCoverPicks"))[name],
      manualName,
    );
    assert.equal(coverId, games[2].id);
    await page.getByRole("button", { name: "Edit", exact: true }).click();
    dialog = await nativeDialog("Edit collection");
    await dialog.getByLabel("Name", { exact: false }).fill(renamed);
    await dialog.getByRole("button", { name: "Save", exact: true }).click();
    await page.waitForURL(
      origin + "/collections/" + encodeURIComponent(renamed),
    );
    const metadata = await page.evaluate(
      (name) => ({
        cover: JSON.parse(localStorage.getItem("collectionCoverPicks"))[name],
        order: JSON.parse(localStorage.getItem("collectionGameOrder"))[name],
        description: JSON.parse(localStorage.getItem("collectionMeta"))[name]
          ?.description,
      }),
      renamed,
    );
    assert.equal(metadata.cover, games[2].id);
    assert.deepEqual(metadata.order, expectedIds);
    assert.equal(metadata.description, "Preserved collection workflow");
    for (const game of games) {
      const stored = await request("GET", "/game/get/" + game.id);
      assert(stored.collections.includes(renamed));
      assert(!stored.collections.includes(manualName));
    }
    const rules = [
      { field: "favorite", value: "", expected: [games[0].title] },
      {
        field: "status",
        value: "beaten",
        expected: [games[0].title, games[1].title],
      },
      {
        field: "tag",
        value: "migration-" + suffix,
        expected: [games[0].title],
      },
      {
        field: "source",
        value: "migration-" + suffix,
        expected: [games[0].title],
      },
      { field: "playtime_hours", value: "2", expected: [games[0].title] },
    ];
    for (const rule of rules) {
      const name =
        {
          favorite: "Favorite quests",
          status: "Finished games",
          tag: "Tagged adventures",
          source: "From one source",
          playtime_hours: "Long play sessions",
        }[rule.field] +
        " " +
        suffix;
      await createCollection(name, rule);
      const titles = await page.locator(".grid .title").allTextContents();
      assert.deepEqual(
        titles
          .filter((title) => games.some((game) => game.title === title))
          .sort(),
        [...rule.expected].sort(),
      );
      assert.equal(
        await page
          .getByRole("button", { name: "+ Add Games", exact: true })
          .count(),
        0,
      );
      assert.equal(
        await page
          .getByTitle("Remove from collection", { exact: true })
          .count(),
        0,
      );
    }
    await page.goto(origin + "/collections");
    await card("After the rename")
      .getByTitle("Pin this collection", { exact: true })
      .click();
    await page.reload();
    await card("After the rename")
      .getByTitle("Unpin this collection", { exact: true })
      .waitFor();
    await page
      .getByLabel("Search collections", { exact: true })
      .fill("After the rename");
    assert.equal(await page.locator(".collection-card-wrap").count(), 1);
    await page.getByLabel("Search collections", { exact: true }).fill("");
    await page
      .getByRole("button", { name: "Open Favorites", exact: true })
      .click();
    assert.equal(
      await page.getByRole("button", { name: "Edit", exact: true }).count(),
      0,
    );
    assert.equal(
      await page.getByRole("button", { name: "Delete", exact: true }).count(),
      0,
    );
    const movie = await request(
      "POST",
      "/movie/create",
      { title: "A Movie About Lost Socks" },
      201,
    );
    movies.push(movie.id);
    const list = await request(
      "POST",
      "/lists",
      {
        name: "Weekend films " + suffix,
        description: "Matching media presentation",
      },
      201,
    );
    lists.push(list.id);
    await request(
      "POST",
      "/lists/" + list.id + "/items",
      { media_type: "movie", media_id: movie.id },
      201,
    );
    for (const [width, theme] of [
      [320, "light"],
      [390, "dark"],
      [1440, "light"],
      [1920, "dark"],
    ]) {
      await request("PATCH", "/preferences", { ui_theme: theme });
      const layoutContext = await admin.browser().newContext({
        storageState: await admin.storageState(),
        viewport: { width, height: width <= 760 ? 700 : 1000 },
        hasTouch: width <= 760,
      });
      const layoutPage = await layoutContext.newPage();
      layoutPage.on("pageerror", (error) => errors.push(String(error)));
      try {
        for (const [route, title, label] of [
          ["/collections", "Collections", "games"],
          ["/lists", "Lists", "media"],
        ]) {
          await layoutPage.goto(origin + route);
          await layoutPage
            .getByRole("heading", { name: title, exact: true })
            .waitFor();
          await layoutPage.waitForFunction(
            (theme) => document.documentElement.dataset.theme === theme,
            theme,
          );
          await layoutPage
            .locator(".collection-card-wrap .open-title")
            .first()
            .waitFor();
          await checkOverflow(
            layoutPage,
            label + " collection overview " + width,
          );
          if (width <= 760) {
            const controls = await layoutPage
              .locator(".card-actions button")
              .evaluateAll((items) =>
                items.map((element) =>
                  element.getBoundingClientRect().toJSON(),
                ),
              );
            assert(
              controls.every((rect) => rect.width >= 44 && rect.height >= 44),
              "Touch actions remain at least 44px",
            );
            assert(
              await layoutPage
                .locator(".card-actions")
                .evaluateAll((items) =>
                  items.every(
                    (element) =>
                      element.getBoundingClientRect().bottom <=
                      element.closest(".cover").getBoundingClientRect().bottom,
                  ),
                ),
              "All touch actions fit inside their card",
            );
          }
          const typography = await layoutPage
            .locator("h1")
            .evaluate((element) => ({
              font: getComputedStyle(element).font,
              color: getComputedStyle(element).color,
            }));
          report.collectionTypography ??= {};
          const key = width + "/" + theme;
          if (label === "games") report.collectionTypography[key] = typography;
          else
            assert.deepEqual(
              typography,
              report.collectionTypography[key],
              "Games and Media use the same heading style",
            );
          const filename =
            "migration-" +
            label +
            "-collections-" +
            width +
            "-" +
            theme +
            ".png";
          await layoutPage.screenshot({
            path: path.join(evidenceRoot, filename),
          });
          report.screens.push(filename);
        }
        await layoutPage.goto(origin + "/games");
        await layoutPage
          .getByRole("heading", { name: "Games", exact: true })
          .waitFor();
        for (const mode of ["Shelves", "List", "Preview"]) {
          await layoutPage
            .getByRole("button", { name: mode, exact: true })
            .click();
          await checkOverflow(layoutPage, "Games " + mode + " " + width);
        }
        await layoutPage
          .getByRole("button", { name: "List", exact: true })
          .click();
        await layoutPage
          .locator(".rank-cell")
          .first()
          .waitFor({ state: "attached" });
        assert.equal(
          await layoutPage.locator(".rank-cell").count(),
          games.length,
        );
        await layoutPage
          .getByLabel("Search games", { exact: true })
          .fill(games[0].title);
        assert.equal(await layoutPage.locator(".rank-cell").count(), 1);
        await layoutPage.getByLabel("Search games", { exact: true }).fill("");
        const sort = layoutPage.getByLabel("Sort by", { exact: true });
        if (!(await sort.isVisible()))
          await layoutPage
            .getByRole("button", { name: "Library controls", exact: true })
            .click();
        await sort.selectOption("name");
        if (width <= 760)
          await layoutPage
            .getByRole("button", { name: "Hide controls", exact: true })
            .click();
        await layoutPage.waitForTimeout(200);
        const gameScreen =
          "migration-games-library-" + width + "-" + theme + ".png";
        await layoutPage.screenshot({
          path: path.join(evidenceRoot, gameScreen),
        });
        report.screens.push(gameScreen);
        for (const [route, name] of [
          ["/collections/" + encodeURIComponent(renamed), "Add games"],
          ["/lists/" + list.id, "Add titles"],
        ]) {
          await layoutPage.goto(origin + route);
          const opener = layoutPage.getByRole("button", {
            name: name === "Add games" ? "+ Add Games" : "+ Add Titles",
            exact: true,
          });
          await opener.click();
          dialog = await nativeDialog(name, layoutPage);
          await layoutPage.keyboard.press("Escape");
          await dialog.waitFor({ state: "hidden" });
          assert(
            await opener.evaluate(
              (element) => element === document.activeElement,
            ),
          );
          await checkOverflow(layoutPage, name + " detail " + width);
        }
      } finally {
        await layoutContext.close();
      }
    }
    await page.goto(origin + "/collections/" + encodeURIComponent(renamed));
    const removed = page.waitForResponse((response) =>
      response.url().includes("/api/game/update/" + games[1].id),
    );
    await page
      .locator(".item-card")
      .filter({ has: page.getByText(games[1].title, { exact: true }) })
      .getByTitle("Remove from collection", { exact: true })
      .click();
    assert.equal((await removed).status(), 200);
    assert(
      !(await request("GET", "/game/get/" + games[1].id)).collections.includes(
        renamed,
      ),
    );
    assert.deepEqual(errors, []);
    report.passed.push(
      "Main's five smart rules, manual membership/rename/order/cover/pin/search, protected Favorites and reload persistence survive the migration",
      "Games and Media overview headings and native picker behavior match at 320/390/1440/1920 in light/dark modes",
    );
  } catch (error) {
    await page.screenshot({
      path: path.join(evidenceRoot, "collection-migration-private-failure.png"),
    });
    console.error(
      JSON.stringify({
        browserErrors: errors,
        dialogText: await page.locator("dialog[open]").allTextContents(),
      }),
    );
    throw error;
  } finally {
    for (const id of lists)
      await admin.request.delete(origin + "/api/lists/" + id);
    for (const id of movies)
      await admin.request.delete(origin + "/api/movie/delete/" + id);
    for (const game of games)
      await admin.request.delete(origin + "/api/game/delete/" + game.id);
    await admin.request.patch(origin + "/api/preferences", { data: before });
    if (storageBefore)
      await page.evaluate((values) => {
        for (const [key, value] of Object.entries(values)) {
          if (value === null) localStorage.removeItem(key);
          else localStorage.setItem(key, value);
        }
      }, storageBefore);
    await page.close();
  }
}
