// Populated core detail/media pages, themes, settings and navigation on real data.
// Cards, Sets and Bounties are covered by the official Collector's Archive plugin checker.
import assert from "node:assert/strict";
import path from "node:path";

export async function checkDetailUi({ admin, member, origin, evidenceRoot, report, pluginsRoot }) {
  const errors = [];
  async function json(response, expected = 200) {
    assert.equal(response.status(), expected, await response.text());
    return response.json();
  }
  async function noOverflow(page, label) {
    const bounds = await page.evaluate(() => ({ width: innerWidth, document: document.documentElement.scrollWidth }));
    if (bounds.document > bounds.width + 1) console.error(await page.locator("body *").evaluateAll(elements => elements.map(element => ({ tag: element.tagName, class: element.className, right: element.getBoundingClientRect().right })).filter(item => item.right > innerWidth + 1)));
    assert(bounds.document <= bounds.width + 1, `${label}: ${JSON.stringify(bounds)}`);
  }
  async function surface(page, selector, token) {
    const colors = await page.locator(selector).first().evaluate((element, token) => {
      const swatch = document.createElement("div"); swatch.style.background = `var(${token})`; element.append(swatch);
      const result = [getComputedStyle(element).backgroundColor, getComputedStyle(swatch).backgroundColor]; swatch.remove(); return result;
    }, token);
    assert.deepEqual(colors.slice(0, 1), colors.slice(1), `${selector} follows ${token}`);
  }
  async function focusDialog(page, dialog) {
    await dialog.waitFor();
    assert.equal(await dialog.evaluate(element => element instanceof HTMLDialogElement && element.open), true);
    for (let index = 0; index < 16; index++) {
      await page.keyboard.press("Tab");
      assert(await dialog.evaluate(element => element.contains(document.activeElement)), "Dialog retains keyboard focus");
    }
    await noOverflow(page, "dialog");
  }
  for (const [role, context] of [["admin", admin], ["member", member]]) {
    const created = [], original = await json(await context.request.get(origin + "/api/preferences"));
    const page = await context.newPage(); page.on("pageerror", error => errors.push(String(error)));
    try {
      const game = await json(await context.request.post(origin + "/api/game/create", { data: { title: "A themed collection adventure", folder_location: `theme-detail-${role}-${Date.now()}`, status: "BEATEN", collections: ["Theme review/Adventures"], description: "A real title used for theme and detail acceptance." } }), 201);
      created.push(["game/delete", game.id]);
      const media = [];
      for (const [kind, title] of [["movie", "A quiet film"], ["tv", "A long-running show"], ["anime", "A hand-drawn adventure"]]) {
        const item = await json(await context.request.post(`${origin}/api/${kind}/create`, { data: { title, description: "Real library metadata, no external provider required.", status: kind === "movie" ? "WATCHED" : "IN_PROGRESS" } }), 201);
        media.push([kind, item]); created.push([`${kind}/delete`, item.id]);
      }
      const list = await json(await context.request.post(origin + "/api/lists", { data: { name: "A populated media list" } }), 201); created.push(["lists", list.id]);
      for (const [kind, item] of media) await json(await context.request.post(`${origin}/api/lists/${list.id}/items`, { data: { media_type: kind, media_id: item.id } }), 201);
      const routes = [
        ["/games", "Games", ".library", "--ui-bg"],
        [`/games/${game.id}`, game.title, ".detail", "--ui-bg"],
        [`/collections/${encodeURIComponent("Theme review/Adventures")}`, "Adventures", ".ui-page", "--ui-bg"],
        ["/movies", "Movies", ".lib-root", "--ui-bg"], ["/tv", "TV Shows", ".lib-root", "--ui-bg"], ["/anime", "Anime", ".lib-root", "--ui-bg"],
        ...media.map(([kind, item]) => [`/${kind === "movie" ? "movies" : kind}/${item.id}`, item.title, ".detail", "--ui-bg"]),
        [`/lists/${list.id}`, list.name, ".ui-page", "--ui-bg"], ["/statistics", "Statistics", ".ui-page", "--ui-bg"],
      ];
      for (const theme of ["light", "dark"]) {
        await json(await context.request.patch(origin + "/api/preferences", { data: { ui_theme: theme } }));
        for (const width of report.widths) {
          await page.setViewportSize({ width, height: width <= 430 ? 880 : 1050 });
          for (const [route, title, selector, token] of routes) {
            await page.goto(origin + route);
            await page.locator("h1").first().waitFor();
            await page.waitForFunction(theme => document.documentElement.dataset.theme === theme, theme);
            await page.waitForFunction(() => !Array.from(document.querySelectorAll("main p, .lib-root p")).some(element => element.textContent.trim() === "Loading…"));
            if (title) assert((await page.locator("h1").first().innerText()).includes(title));
            await surface(page, selector, token); await noOverflow(page, `${role}/${theme}/${width}/${route}`);
            if (route === "/statistics") {
              const heatColors = await page.locator(".heat-cell.l0").first().evaluate(element => [getComputedStyle(element).backgroundColor, getComputedStyle(element.closest(".stats-panel")).backgroundColor]);
              assert.notEqual(heatColors[0], heatColors[1], "Empty heatmap days remain visible against the statistics panel");
            }
            if (await page.locator(".media-topbar").count()) {
              const bar = await page.locator(".media-topbar").evaluate(element => ({ color: getComputedStyle(element).backgroundColor, dark: getComputedStyle(element).colorScheme }));
              assert.equal(bar.dark, theme);
              const overlaps = await page.locator(".media-topbar").evaluate(element => {
                const chip = element.querySelector(".account-chip")?.getBoundingClientRect();
                return Array.from(element.querySelectorAll(".topbar-left a, .topbar-left button, .media-topbar-actions a, .media-topbar-actions button")).some(item => { const r = item.getBoundingClientRect(); return chip && r.right > chip.left && r.left < chip.right && r.bottom > chip.top && r.top < chip.bottom; });
              }); assert.equal(overlaps, false, "Top-bar controls do not overlap the account menu");
            }
            report.screens.push({ role, theme, palette: report.palette ?? "orange", width, screen: route.replace(/[0-9a-f]{8}-[0-9a-f-]{27}/g, ":id") });
            if (role === "admin" && [390, 1440].includes(width) && ["/statistics", "/movies", `/games/${game.id}`, `/collections/${encodeURIComponent("Theme review/Adventures")}`].includes(route)) await page.screenshot({ path: path.join(evidenceRoot, `stage-detail-${route.split("/")[1]}-${width}-${theme}.png`), fullPage: width > 430 });
          }
          await page.goto(origin + "/statistics"); await page.locator(".stats-summary").waitFor();
          for (const name of ["Games", "Movies", "TV Shows", "Anime", "Overview"]) {
            await page.getByLabel("Statistics sections", { exact: true }).getByRole("button", { name, exact: true }).click();
            await page.locator(".stats-summary").waitFor(); await noOverflow(page, `statistics/${name}`);
          }
          if (role === "admin") {
            let titleStyle;
            for (const [section, title] of [["users", "Users"], ["oidc", "Single sign-on"], ["server-integrations", "Server integrations"], ["limits", "Limits"], ["dev-tools", "Developer tools"], ["plugins", "Plugins"]]) {
              await page.goto(origin + `/settings?section=${section}`); await page.getByRole("heading", { name: title, level: 1, exact: true }).waitFor();
              const style = await page.locator(".page-header h1").evaluate(element => { const s = getComputedStyle(element); return [s.fontSize,s.fontWeight,s.lineHeight]; });
              titleStyle ??= style; assert.deepEqual(style, titleStyle); await noOverflow(page, `administration/${section}/${width}`);
            }
            const launcher = page.getByRole("button", { name: "Install package or URL", exact: true });
            const colors = await launcher.evaluate(element => ({ foreground: getComputedStyle(element).color, background: getComputedStyle(element).backgroundColor }));
            function luminance(color) { const rgb = color.match(/[\d.]+/g).slice(0,3).map(Number).map(v => { v/=255; return v<=0.04045 ? v/12.92 : ((v+0.055)/1.055)**2.4; }); return rgb[0]*0.2126+rgb[1]*0.7152+rgb[2]*0.0722; }
            const [low,high] = [luminance(colors.foreground),luminance(colors.background)].sort((a,b)=>a-b);
            assert((high+0.05)/(low+0.05)>=4.5, "Install button text meets 4.5:1 contrast");
            await launcher.click(); const dialog = page.getByRole("dialog", { name: "Install package or URL", exact: true }); await focusDialog(page, dialog); await page.keyboard.press("Escape"); await dialog.waitFor({ state: "hidden" });
            assert(await launcher.evaluate(element => element === document.activeElement));
          }
        }
      }
      if (role === "admin") {
        await page.setViewportSize({ width: 390, height: 880 });
        await page.goto(origin + "/settings?section=plugins");
        await page.getByRole("button", { name: "Install package or URL", exact: true }).click();
        const installer = page.getByRole("dialog", { name: "Install package or URL", exact: true });
        await installer.getByLabel("Plugin package", { exact: true }).setInputFiles(path.join(pluginsRoot, ".validation/dist/example.playtime-report-1.2.0.utp"));
        const previewResponse = page.waitForResponse(response => new URL(response.url()).pathname === "/api/plugins/install/preview");
        await installer.getByRole("button", { name: "Review package", exact: true }).click();
        const preview = await json(await previewResponse);
        const consent = page.getByRole("dialog", { name: /^Review / }); await focusDialog(page, consent);
        const summary = consent.getByLabel("Requested permission risks").first();
        assert.equal(preview.permissions.some(permission => permission.risk === "critical"), false, "This maintained package exercises absent critical risk");
        assert.equal(await summary.locator(".risk-bubble").count(), new Set(preview.permissions.map(permission => permission.risk)).size);
        for (const risk of ["critical", "high", "medium", "low"]) {
          const count = preview.permissions.filter(permission => permission.risk === risk).length;
          if (count) assert.match(await summary.locator(`.risk-bubble.${risk}`).innerText(), new RegExp(`^${count}\\s`));
          else assert.equal(await summary.locator(`.risk-bubble.${risk}`).count(), 0, "Unrequested risks stay hidden");
        }
        const disclosure = consent.locator(".disclosure").first();
        assert((await disclosure.boundingBox()).height >= 44);
        await disclosure.click(); assert.equal(await disclosure.getAttribute("aria-expanded"), "false");
        await disclosure.click(); assert.equal(await disclosure.getAttribute("aria-expanded"), "true");
        await page.screenshot({ path: path.join(evidenceRoot, "stage-detail-consent-390-dark.png") });
        await page.keyboard.press("Escape"); await consent.waitFor({ state: "hidden" });
        await page.keyboard.press("Escape"); await installer.waitFor({ state: "hidden" });
        const limitsBefore = await json(await context.request.get(origin + "/api/settings/upload-limits"));
        try {
          await page.goto(origin + "/settings?section=limits");
          for (const label of ["Images & general files (MB)", "Save archives (MB)", "Video clips (MB)", "World saves & modpacks (MB)"]) await page.getByRole("spinbutton", { name: label, exact: true }).fill("1");
          await page.getByRole("button", { name: "Save limits", exact: true }).click();
          await page.getByRole("status").filter({ hasText: "Limits saved." }).waitFor();
          await page.reload(); await page.getByRole("spinbutton", { name: "Save archives (MB)", exact: true }).waitFor();
          for (const value of Object.values(await json(await context.request.get(origin + "/api/settings/upload-limits")))) assert.equal(value, 1);
          assert.equal(await page.getByRole("spinbutton", { name: "Video clips (MB)", exact: true }).inputValue(), "1");
          const payload = Buffer.alloc(1024*1024+1, 1);
          for (const [endpoint, filename, mimeType] of [[`/api/game/${game.id}/screenshots`, "too-large.mp4", "video/mp4"], [`/api/game/${game.id}/screenshots`, "too-large.png", "image/png"], [`/api/game/${game.id}/files/modpack`, "too-large.zip", "application/zip"]]) {
            const response = await json(await context.request.post(origin + endpoint, { multipart: { file: { name: filename, mimeType, buffer: payload } } }));
            assert(JSON.stringify(response).includes("Larger than 1 MB."), "Actual upload handler enforces saved cap");
          }
          for (const kind of ["save", "world_save"]) {
            const response = await context.request.post(`${origin}/api/game/${game.id}/archives/${kind}`, { multipart: { name: "Oversized test archive", file: { name: "too-large.zip", mimeType: "application/zip", buffer: payload } } });
            assert.equal(response.status(), 400); assert((await response.text()).includes("Larger than 1 MB."));
          }
          await page.getByRole("button", { name: "Reset all to server defaults", exact: true }).click();
          await page.getByRole("status").filter({ hasText: "All limits reset" }).waitFor();
          const defaults = await json(await context.request.get(origin + "/api/settings/upload-limits"));
          assert.deepEqual(defaults, { max_upload_size_mb: 15, max_save_archive_size_mb: 4096, max_clip_size_mb: 500, max_world_save_size_mb: 2000 });
        } finally { await json(await context.request.put(origin + "/api/settings/upload-limit", { data: limitsBefore })); }
        report.passed.push("Real package preview renders only requested risk categories and usable disclosure arrows", "All four upload caps persist through real settings UI and enforce oversized file, clip, modpack, save and world-save rejection", "Reset clears all overrides to the configured environment defaults");
      }
      // Fresh in-app navigation resets a scrolled page; a detail return preserves library context.
      await page.setViewportSize({ width: 390, height: 620 });
      await page.goto(origin + `/lists/${list.id}`); await page.locator("h1").waitFor();
      await page.evaluate(() => window.scrollTo(0, 160));
      await page.getByRole("button", { name: "Open menu", exact: true }).click();
      const navigation = page.getByRole("dialog", { name: "Main navigation", exact: true });
      const allGames = navigation.getByRole("link", { name: "All games", exact: true });
      if (!await allGames.isVisible()) await navigation.getByRole("button", { name: "Games", exact: true }).click();
      await allGames.click();
      await page.getByRole("heading", { name: "Games", level: 1, exact: true }).waitFor();
      await page.waitForFunction(() => scrollY === 0);
      await page.close();
    } finally {
      if (!page.isClosed()) await page.close();
      await context.request.patch(origin + "/api/preferences", { data: { ui_theme: original.ui_theme } });
      for (const [endpoint, id] of created.reverse()) {
        const response = await context.request.delete(`${origin}/api/${endpoint}/${id}`);
        assert([200,204].includes(response.status()), await response.text());
        if (endpoint.endsWith("/delete") && !endpoint.startsWith("game")) {
          const purge = await context.request.delete(`${origin}/api/${endpoint.split("/")[0]}/${id}/purge`); assert.equal(purge.status(), 204);
        }
      }
    }
  }
  assert.deepEqual(errors, []);
  report.passed.push(`${report.screens.length} populated detail/media/theme/width/role cases`, `All five statistics tabs at ${report.widths.length} widths in both themes`, "Separate administration sections retain consistent title styles", "Install button text contrast at least 4.5:1 in both themes", "Native installer keyboard focus, Escape and restored focus", "Media top bars follow theme and avoid overlapping account controls", "Fresh in-app Games navigation starts at the top");
}
