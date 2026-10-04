import assert from "node:assert/strict";
import path from "node:path";

export async function checkAppearanceSettings({ admin, origin, evidenceRoot, report, checkOverflow }) {
  const original = await (await admin.request.get(origin + '/api/preferences')).json();
  const page = await admin.newPage();
  const errors = []; page.on('pageerror', error => errors.push(String(error)));
  try {
    for (const theme of ['light', 'dark']) {
      assert.equal((await admin.request.patch(origin + '/api/preferences', { data: { ui_theme: theme } })).status(), 200);
      for (const width of report.widths) {
        await page.setViewportSize({ width, height: 1000 });
        for (const section of ['appearance', 'interface']) {
          await page.goto(`${origin}/settings?section=${section}`);
          await page.getByRole('heading', { name: 'Appearance & interface', level: 1, exact: true }).waitFor();
          await page.getByLabel('Theme', { exact: true }).waitFor();
          for (const title of ['Theme & layout', 'Navigation & library defaults', 'Completed game badges']) {
            assert.equal(await page.getByRole('heading', { name: title, level: 2, exact: true }).count(), 1);
          }
          assert.equal(await page.getByRole('button', { name: 'User Interface', exact: true }).count(), 0);
          await checkOverflow(page, `${theme}/${width}/${section}`);
          report.screens.push({ theme, width, screen: `/settings?section=${section}` });
          if (section === 'appearance' && [390, 1440].includes(width)) {
            await page.getByRole('heading', { name: 'Navigation & library defaults', exact: true }).scrollIntoViewIfNeeded();
            await page.screenshot({ path: path.join(evidenceRoot, `stage-settings-combined-${width}-${theme}.png`) });
          }
        }
      }
    }
    await page.getByRole('button', { name: 'List + preview', exact: true }).click();
    await page.getByRole('button', { name: 'Recently played', exact: true }).click();
    await page.getByRole('button', { name: 'Icon rail', exact: true }).click();
    await page.reload(); await page.getByLabel('Theme', { exact: true }).waitFor();
    for (const name of ['List + preview', 'Recently played', 'Icon rail']) {
      assert.equal(await page.getByRole('button', { name, exact: true }).getAttribute('aria-pressed'), 'true');
    }
    assert.deepEqual(errors, []);
    report.passed.push('32 combined Appearance and Interface route cases across eight widths and both themes', 'One menu entry with theme, layout, navigation, library defaults and personal badges', 'Device defaults persist after reload and legacy bookmarks retain access');
  } finally {
    await admin.request.patch(origin + '/api/preferences', { data: { ui_theme: original.ui_theme } });
    await page.close();
  }
}
