import assert from "node:assert/strict";
import path from "node:path";

export async function checkLibraryEditors({ admin, origin, evidenceRoot, report, checkOverflow }) {
  async function json(response, status = 200) { assert.equal(response.status(), status, await response.text()); return response.json(); }
  const original = await json(await admin.request.get(origin + '/api/preferences'));
  const created = []; const page = await admin.newPage(); const errors = []; page.on('pageerror', error => errors.push(String(error)));
  async function inspect(name, label, wide = false) {
    const dialog = page.getByRole('dialog', { name, exact: true }); await dialog.waitFor();
    assert(await dialog.evaluate(element => element instanceof HTMLDialogElement && element.open));
    const bounds = await dialog.boundingBox(); assert(bounds.x >= 0 && bounds.x + bounds.width <= page.viewportSize().width + 1);
    if (wide && page.viewportSize().width >= 1440) assert(bounds.width >= 1000, 'Content-heavy editors use wide desktop space');
    for (let index = 0; index < 12; index++) { await page.keyboard.press('Tab'); assert(await dialog.evaluate(element => element.contains(document.activeElement))); }
    await checkOverflow(page, label);
    const surface = await dialog.evaluate(element => { const sample = document.createElement('span'); sample.style.background = 'var(--ui-surface)'; element.append(sample); const result = [getComputedStyle(element).backgroundColor, getComputedStyle(sample).backgroundColor]; sample.remove(); return result; }); assert.equal(surface[0], surface[1]);
    report.screens.push({ theme: await page.locator('html').getAttribute('data-theme'), width: page.viewportSize().width, editor: label }); return dialog;
  }
  try {
    const media = [];
    for (const [kind, route] of [['movie','movies'],['tv','tv'],['anime','anime']]) {
      const item = await json(await admin.request.post(`${origin}/api/${kind}/create`, { data: { title: `A real ${kind} editor title` } }), 201); media.push([kind,route,item]); created.push([`${kind}/delete`,item.id]);
    }
    for (const theme of ['light','dark']) {
      await json(await admin.request.patch(origin + '/api/preferences', { data: { ui_theme: theme, library_default_layout: 'list' } }));
      for (const width of report.widths) {
        await page.setViewportSize({ width, height: 1000 });
        for (const [kind,route,item] of media) {
          await page.goto(`${origin}/${route}`); await page.getByRole('heading', { name: kind === 'movie' ? 'Movies' : kind === 'tv' ? 'TV Shows' : 'Anime', exact: true }).waitFor();
          const addButton = page.locator('[data-shortcut="create"]'); const addTitle = (await addButton.innerText()).replace(/^\+\s*/, '').trim(); await addButton.click(); const add = await inspect(addTitle, `${kind}/quick-add`, true);
          if (kind === 'movie' && [390,1440].includes(width)) await page.screenshot({ path: path.join(evidenceRoot, `stage-media-add-${width}-${theme}.png`) });
          await page.keyboard.press('Escape'); await add.waitFor({ state: 'hidden' });
          await page.getByRole('button', { name: 'Add note', exact: true }).first().click(); const note = await inspect('Notes', `${kind}/notes`);
          await note.getByLabel('Personal media notes', { exact: true }).fill('A note saved through the native editor.'); const savedNote = page.waitForResponse(response => response.url().includes(`/api/${kind}/update/${item.id}`) && response.request().method() === 'PATCH'); await note.getByRole('button', { name: 'Save', exact: true }).click(); await json(await savedNote);
          const editButton = page.getByRole('button', { name: 'Edit', exact: true }).first(); await editButton.scrollIntoViewIfNeeded(); assert(await editButton.evaluate(button => { const bounds = button.getBoundingClientRect(); return button.contains(document.elementFromPoint(bounds.x + bounds.width / 2, bounds.y + bounds.height / 2)); }), 'Media edit targets remain unobstructed by neighboring progress cells'); await editButton.click(); const edit = await inspect('Quick edit', `${kind}/quick-edit`);
          await page.keyboard.press('Escape'); await edit.waitFor({ state: 'hidden' });
          await json(await admin.request.patch(`${origin}/api/${kind}/update/${item.id}`, { data: { note: null } }));
        }
        await page.goto(origin + '/games'); await page.getByRole('heading', { name: 'Games', exact: true }).waitFor(); await page.keyboard.press('n'); const game = await inspect('Add Game', 'game/create', true);
        if (width === 1440 && theme === 'light') await page.screenshot({ path: path.join(evidenceRoot, 'stage-game-editor-desktop.png') });
        await page.keyboard.press('Escape'); await game.waitFor({ state: 'hidden' });
      }
    }
    assert.deepEqual(errors, []); report.passed.push('160 native game/media editor cases across eight widths and both themes', 'Wide content-heavy editors, semantic surfaces, dialog bounds and keyboard containment', 'Personal media notes save through real update endpoints');
  } finally {
    for (const [endpoint,id] of created.reverse()) await admin.request.delete(`${origin}/api/${endpoint}/${id}`);
    await admin.request.patch(origin + '/api/preferences', { data: { ui_theme: original.ui_theme, library_default_layout: original.library_default_layout } }); await page.close();
  }
}
