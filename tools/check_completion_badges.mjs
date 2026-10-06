// Real saved badge rendering and shared settings preview; no embedded media installed.
import assert from "node:assert/strict";
import path from "node:path";

export async function checkCompletionBadges({ admin, member, origin, evidenceRoot, report, checkOverflow }) {
  async function json(response, status = 200) { assert.equal(response.status(), status, await response.text()); return response.json(); }
  const preferences = await json(await admin.request.get(origin + "/api/preferences"));
  const original = await json(await admin.request.get(origin + "/api/settings/appearance"));
  const other = await json(await member.request.get(origin + "/api/settings/appearance"));
  const game = await json(await admin.request.post(origin + "/api/game/create", { data: { title: "Loot Goblin Academy", folder_location: `ui-ribbon-${Date.now()}`, status: "MASTERED" } }), 201);
  const page = await admin.newPage(); const errors = []; page.on("pageerror", error => errors.push(String(error)));
  const titles = ["Inventory Full Again", "Side Quest: Laundry", "Oops, All Side Quests", "The Final Final Boss", "Save Point Simulator", "One More Turn, Honest", "Loot Goblin Academy", "Achievement: Went Outside"];
  try {
    for (const theme of ["light", "dark"]) {
      await json(await admin.request.patch(origin + "/api/preferences", { data: { ui_theme: theme, ui_high_contrast: false } }));
      for (const width of [320, 390, 1440]) {
        await page.setViewportSize({ width, height: 1000 });
        for (const placement of ["top-left", "top-right", "bottom-left", "bottom-right"]) {
          await json(await admin.request.put(origin + "/api/settings/appearance", { data: { completion_badge_style: "ribbon", completion_badge_color: "#e3bd69", completion_badge_placement: placement } }));
          await page.goto(origin + "/settings?section=appearance");
          const section = page.locator("section").filter({ has: page.getByRole("heading", { name: "Completed game badges", exact: true }) });
          const preview = section.locator(".preview-cover");
          await preview.locator(".ribbon").waitFor();
          await page.waitForFunction(() => { const image = document.querySelector('.preview-art'); return image?.complete && image.naturalWidth > 0; });
          const title = await section.locator(".preview-title").innerText(); assert(titles.includes(title));
          const src = await preview.locator(".preview-art").getAttribute("src");
          const art = await admin.request.get(origin + src); assert.equal(art.status(), 200); assert((await art.text()).includes("NO COVER ART"));
          assert.equal(new URL(src, origin).searchParams.get("title"), title);
          const geometry = await preview.locator(".ribbon .badge-face").evaluate(element => ({ height: element.clientHeight, width: element.clientWidth, shape: getComputedStyle(element).clipPath, background: getComputedStyle(element).backgroundImage }));
          assert(geometry.height > geometry.width && geometry.shape.startsWith("polygon(") && geometry.background.includes("linear-gradient"), "A notched ribbon with shaded folds replaces the floating star");
          await checkOverflow(page, `ribbon preview/${theme}/${width}/${placement}`);
          await preview.evaluate(element => element.scrollIntoView({ block: "center" }));
          if ([390, 1440].includes(width) && placement === "top-right") await page.screenshot({ path: path.join(evidenceRoot, `stage-ribbon-preview-${width}-${theme}.png`) });
          await page.goto(origin + "/games");
          await page.getByRole("button", { name: "Cards view", exact: true }).click();
          await page.waitForFunction(() => document.querySelectorAll('.game-card').length > 0);
          const card = page.locator(".game-card-wrap").filter({ hasText: game.title });
          await card.locator(`.completion-badge.ribbon.${placement}`).waitFor();
          const live = await card.locator(".badge-face").evaluate(element => ({ height: element.clientHeight, width: element.clientWidth, shape: getComputedStyle(element).clipPath, background: getComputedStyle(element).backgroundImage }));
          assert.deepEqual(live, geometry, "Real saved card and preview share the same ribbon rendering");
          await checkOverflow(page, `saved ribbon/${theme}/${width}/${placement}`);
          if (width === 1440 && theme === "dark" && placement === "top-right") await card.screenshot({ path: path.join(evidenceRoot, "stage-ribbon-card-dark.png") });
          report.screens.push({ theme, width, placement, preview: true, savedCard: true });
        }
      }
    }
    assert.deepEqual(await json(await member.request.get(origin + "/api/settings/appearance")), other);
    assert.deepEqual(errors, []);
    report.passed.push("24 real ribbon preview/card cases across all corners, 320/390/1440 widths and both themes", "Existing fallback cover icon and eight refresh titles; no preview games created", "Personal badge changes leave the other account unchanged");
  } finally {
    await admin.request.delete(`${origin}/api/game/delete/${game.id}`);
    await admin.request.put(origin + "/api/settings/appearance", { data: { completion_badge_style: original.completion_badge_style, completion_badge_color: original.completion_badge_color, completion_badge_placement: original.completion_badge_placement } });
    await admin.request.patch(origin + "/api/preferences", { data: { ui_theme: preferences.ui_theme, ui_high_contrast: preferences.ui_high_contrast } });
    await page.close();
  }
}
