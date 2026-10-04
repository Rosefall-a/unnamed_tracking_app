// Real library search and route-aware shortcut help; requests are never mocked.
import assert from "node:assert/strict";
import path from "node:path";

export async function checkSearchShortcuts({ admin, member, origin, evidenceRoot, report, checkOverflow }) {
  async function json(response, status = 200) { assert.equal(response.status(), status, await response.text()); return response.json(); }
  const original = await json(await admin.request.get(origin + "/api/preferences"));
  const created = [];
  const page = await admin.newPage(); const errors = []; page.on("pageerror", error => errors.push(String(error)));
  const memberPage = await member.newPage(); memberPage.on("pageerror", error => errors.push(String(error)));
  const dialog = page.getByRole("dialog", { name: "Search library", exact: true });
  async function openSearch() { await page.keyboard.press("Control+k"); await dialog.waitFor(); }
  async function bodyFocus() { await page.locator('h1').first().click(); }
  async function contain(target) { for (let index = 0; index < 12; index++) { await page.keyboard.press('Tab'); assert(await target.evaluate(element => element.contains(document.activeElement))); } }
  try {
    const game = await json(await admin.request.post(origin + '/api/game/create', { data: { title: 'Nebula inventory adventure', folder_location: `ui-search-${Date.now()}`, collections: ['Nebula favorites'] } }), 201); created.push(['game/delete', game.id]);
    for (const [kind, title] of [['movie', 'Nebula film'], ['tv', 'Nebula series'], ['anime', 'Nebula animation']]) {
      const item = await json(await admin.request.post(`${origin}/api/${kind}/create`, { data: { title } }), 201); created.push([`${kind}/delete`, item.id]);
    }
    const goal = await json(await admin.request.post(origin + '/api/bounties', { data: { title: 'Nebula completion goal', type: 'challenge', game_id: game.id, progress_target: 2 } })); created.push(['bounties', goal.bounty.id]);
    await page.setViewportSize({ width: 1440, height: 1000 }); await page.goto(origin + '/statistics');
    await admin.route('**/api/game/list?*', async route => { await new Promise(resolve => setTimeout(resolve, 250)); await route.continue(); });
    assert.equal(await page.locator('.navigation a[href="/statistics"]').getAttribute('title'), 'Statistics · Alt + R'); assert.equal(await page.locator('.navigation a[href="/statistics"]').getAttribute('aria-keyshortcuts'), 'Alt+R'); await page.getByRole('button', { name: 'Search library', exact: true }).click();
    await dialog.getByRole('textbox', { name: 'Search library', exact: true }).fill('Nebula');
    for (const title of ['Nebula inventory adventure', 'Nebula favorites', 'Nebula film', 'Nebula series', 'Nebula animation', 'Nebula completion goal']) await dialog.locator('.palette-item').filter({ hasText: title }).waitFor();
    await admin.unroute('**/api/game/list?*');
    await page.screenshot({ path: path.join(evidenceRoot, 'stage-search-library-desktop.png') });
    await dialog.getByRole('textbox', { name: 'Search library', exact: true }).fill('Nebula film');
    await dialog.locator('.palette-item').filter({ hasText: 'Nebula film' }).waitFor();
    await page.keyboard.press('Enter'); await page.waitForURL(/\/movies\/[0-9a-f-]+$/);
    await openSearch(); await dialog.getByRole('textbox', { name: 'Search library', exact: true }).fill('Nebula');
    await admin.setOffline(true); await page.keyboard.press('Escape'); await openSearch();
    await dialog.getByRole('textbox', { name: 'Search library', exact: true }).fill('Nebula');
    await dialog.getByRole('button', { name: 'Retry', exact: true }).waitFor();
    assert(await dialog.locator('.palette-item').filter({ hasText: 'Nebula inventory adventure' }).isVisible(), 'A failed reload retains available game results');
    await admin.setOffline(false); await dialog.getByRole('button', { name: 'Retry', exact: true }).click();
    await dialog.locator('.palette-item').filter({ hasText: 'Nebula film' }).waitFor(); await page.keyboard.press('Escape');
    const fresh = await json(await admin.request.post(origin + '/api/game/create', { data: { title: 'A freshly added searchable game', folder_location: `ui-search-fresh-${Date.now()}` } }), 201); created.push(['game/delete', fresh.id]);
    await openSearch(); await dialog.getByRole('textbox', { name: 'Search library', exact: true }).fill(fresh.title); await dialog.locator('.palette-item').filter({ hasText: fresh.title }).waitFor(); await page.keyboard.press('Escape');
    const routes = [['h','/','Anywhere'], ['g','/games','Games library'], ['c','/collections','Collections & lists'], ['m','/movies','Media libraries'], ['t','/tv','Media libraries'], ['a','/anime','Media libraries'], ['l','/lists','Collections & lists'], ['e','/cards','Cards'], ['s','/sets','Sets'], ['b','/bounties','Bounties'], ['v','/calendar','Calendar'], ['r','/statistics','Anywhere'], ['p','/settings','Anywhere']];
    for (const theme of ['light','dark']) {
      await json(await admin.request.patch(origin + '/api/preferences', { data: { ui_theme: theme } }));
      for (const width of [390,1440]) {
        await page.setViewportSize({ width, height: 1000 }); await page.goto(origin + '/statistics');
        for (const [key, route, group] of routes) {
          await bodyFocus(); await page.keyboard.press('Alt+' + key); await page.waitForURL(origin + route); await page.locator('h1').first().waitFor();
          await bodyFocus(); await page.keyboard.press('?'); const help = page.getByRole('dialog', { name: 'Keyboard shortcuts', exact: true }); await help.waitFor();
          assert((await help.locator('.shortcut-group').first().innerText()).startsWith(group)); assert(await help.locator('.shortcut-group').first().evaluate(element => element.open));
          const second = help.locator('.shortcut-group').nth(1); await second.locator('summary').click(); assert(await second.evaluate(element => element.open)); await second.locator('summary').click(); assert(!await second.evaluate(element => element.open));
          await contain(help); await checkOverflow(page, `${theme}/${width}/${route}/help`);
          if (route === '/movies' && width === 1440 && theme === 'dark') await page.screenshot({ path: path.join(evidenceRoot, 'stage-shortcuts-current-page.png') });
          await page.keyboard.press('Escape'); await help.waitFor({ state: 'hidden' });
          await bodyFocus(); await page.keyboard.press('Control+k'); await dialog.waitFor(); await page.keyboard.press('Escape');
          report.screens.push({ theme, width, route, search: true, help: true, navigation: true });
        }
      }
    }
    await page.goto(origin + '/statistics'); await bodyFocus(); await page.keyboard.press('n'); await page.keyboard.press('Enter');
    assert.equal(new URL(page.url()).pathname, '/statistics'); assert.equal(await page.locator('dialog[open]').count(), 0, 'Inactive cached library handlers cannot open games or editors on another page');
    for (const route of ['/games','/collections','/lists','/movies','/tv','/anime','/bounties']) {
      await page.goto(origin + route); await bodyFocus(); await page.keyboard.press('/');
      assert(await page.evaluate(() => document.activeElement?.getAttribute('data-shortcut') === 'search'), `${route}: slash focuses its search`);
      await page.keyboard.type('gmn?'); await page.keyboard.press('Alt+m'); assert.equal(new URL(page.url()).pathname, route, 'Typing never triggers global navigation/help');
      await bodyFocus(); await page.keyboard.press('n'); console.log(`Checking new control on ${route}`); const editor = page.locator('dialog[open]'); await editor.waitFor(); await contain(editor);
      await page.keyboard.press('Control+k'); assert.equal(await dialog.count(), 0, 'Search does not cover another native dialog'); await page.keyboard.press('Alt+r'); assert.equal(new URL(page.url()).pathname, route, 'Alt navigation does not dismiss an editor');
      await checkOverflow(page, `${route}/new`); await page.keyboard.press('Escape'); await editor.waitFor({ state: 'hidden' });
    }
    await memberPage.goto(origin + '/statistics'); await memberPage.getByRole('heading', { name: 'Statistics', exact: true }).waitFor(); await memberPage.keyboard.press('Control+k');
    const memberDialog = memberPage.getByRole('dialog', { name: 'Search library', exact: true }); await memberDialog.getByRole('textbox', { name: 'Search library', exact: true }).fill('Nebula');
    await memberPage.waitForResponse(response => response.url().includes('/api/anime/list?')); assert.equal(await memberDialog.locator('.palette-item').count(), 0, 'Private search results belong to their account');
    await memberDialog.getByRole('textbox', { name: 'Search library', exact: true }).fill('Single sign-on'); await memberPage.waitForResponse(response => response.url().includes('/api/anime/list?')); assert.equal(await memberDialog.locator('.palette-item').count(), 0, 'Members do not see administrator settings results');
    assert.deepEqual(errors, []);
    report.passed.push('Sidebar first-open search with delayed real loading, games/collections/goals/all media, keyboard Enter navigation, new-game refresh and offline retry', '52 route/theme/width combinations with Alt navigation, Search library and current-page-first expandable keyboard help', 'Local slash/new controls, typing guards and native dialog containment', 'Member search excludes another account and administrator-only settings');
  } finally {
    await admin.setOffline(false); await admin.unroute('**/api/game/list?*');
    for (const [endpoint,id] of created.reverse()) await admin.request.delete(`${origin}/api/${endpoint}/${id}`);
    await admin.request.patch(origin + '/api/preferences', { data: { ui_theme: original.ui_theme } });
    await page.close(); await memberPage.close();
  }
}
