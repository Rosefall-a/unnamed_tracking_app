// Exercise real package updates on a disposable host with a harmless v1.1 example.
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";

export async function checkPluginUpdateUi({
  browser, admin, origin, evidenceRoot, report, checkOverflow,
}) {
  const pluginId = process.env.PLUGIN_UPDATE_ID ?? "example.ui-api";
  const same = process.env.PLUGIN_UPDATE_SAME_PACKAGE;
  const older = process.env.PLUGIN_UPDATE_OLDER_PACKAGE;
  const other = process.env.PLUGIN_UPDATE_OTHER_PACKAGE;
  assert(same && older && other, "Provide current, older and different-ID packages from the companion repository.");
  const original = await (await admin.request.get(origin + "/api/preferences")).json();
  const record = async () => {
    const response = await admin.request.get(origin + "/api/plugins");
    assert.equal(response.status(), 200);
    const item = (await response.json()).find(item => item.plugin_id === pluginId);
    assert(item, "Install the current harmless example before running this stage.");
    return item;
  };
  const initial = await record();
  const files = new Map();
  for (const file of [same, older, other]) files.set(file, await readFile(file));
  async function restore() {
    const response = await admin.request.put(origin + `/api/plugins/${pluginId}/update/preview`, {
      multipart: { file: { name: path.basename(same), mimeType: "application/octet-stream", buffer: files.get(same) } },
    });
    assert.equal(response.status(), 200);
    const preview = await response.json();
    assert(!preview.permissions.some(item => item.highly_privileged), "Use an example without privileged permissions for this stage.");
    const query = new URLSearchParams({ allow_untrusted: "true", version_change_confirmed: "true" });
    for (const permission of preview.permissions) query.append("approved_permissions", permission.key);
    const applied = await admin.request.put(origin + `/api/plugins/${pluginId}/update?${query}`, {
      multipart: {
        file: { name: path.basename(same), mimeType: "application/octet-stream", buffer: files.get(same) },
        expected_installed_version: preview.installed_version,
        expected_digest: preview.digest,
      },
    });
    assert.equal(applied.status(), 200, await applied.text());
    const outcome = await applied.json();
    assert.equal(outcome.status, "running");
    assert(outcome.healthy);
    assert.equal((await record()).version, initial.version);
  }
  try {
    for (const [width, theme] of [[1440, "light"], [390, "dark"], [320, "light"], [1920, "dark"]]) {
      await restore();
      assert.equal((await admin.request.patch(origin + "/api/preferences", { data: { ui_theme: theme } })).status(), 200);
      const context = await browser.newContext({
        storageState: await admin.storageState(), hasTouch: width <= 760,
        viewport: { width, height: width <= 760 ? 800 : 1000 },
      });
      const page = await context.newPage(), errors = [];
      page.on("pageerror", error => errors.push(String(error)));
      const card = () => page.locator("article.plugin").filter({ has: page.getByText(new RegExp(`^${pluginId.replaceAll(".", "\\.")} · v`)) });
      const review = () => page.getByRole("dialog", { name: /^Review / });
      async function drop(target, file, name = path.basename(file)) {
        await page.waitForFunction(() => !document.querySelector('.package-drop-zone[aria-busy="true"]'));
        const transfer = await page.evaluateHandle(({ base64, name }) => {
          const bytes = Uint8Array.from(atob(base64), character => character.charCodeAt(0));
          const data = new DataTransfer();
          data.items.add(new File([bytes], name, { type: "application/octet-stream" }));
          return data;
        }, { base64: files.get(file).toString("base64"), name });
        await target.dispatchEvent("drop", { dataTransfer: transfer });
        await transfer.dispose();
      }
      async function approve() {
        for (const checkbox of await review().getByRole("checkbox").all()) {
          if (!(await checkbox.isDisabled())) await checkbox.setChecked(true);
        }
        await review().getByRole("button", { name: "Update with selected access", exact: true }).click();
      }
      async function screen(name) {
        await checkOverflow(page, `${name}/${width}/${theme}`);
        if ([390, 1440].includes(width)) {
          const filename = `${name}-${width}-${theme}.png`;
          await page.screenshot({ path: path.join(evidenceRoot, filename) });
          report.screens.push(filename);
        }
      }
      try {
        await page.goto(origin + "/settings?section=plugins");
        await card().getByRole("button", { name: "Settings & access", exact: true }).waitFor();
        await drop(card(), same, "current-release.upt");
        await review().waitFor();
        assert.equal(await page.getByRole("dialog", { name: "Already installed", exact: true }).count(), 0);
        await approve();
        const confirmation = page.getByRole("dialog", { name: "Confirm same-version update", exact: true });
        await confirmation.waitFor();
        await screen("plugin-same-version-confirmation");
        await confirmation.getByRole("button", { name: "Cancel", exact: true }).click();
        assert.equal((await record()).version, initial.version);
        await approve();
        await confirmation.getByRole("button", { name: "Apply this version again", exact: true }).click();
        await review().waitFor({ state: "hidden" });
        assert.equal((await record()).installation_id, initial.installation_id);

        // The upload control and the whole installed card both accept drops.
        await drop(card().locator('label:has(input[type="file"])'), older, "older-release.upt");
        await review().waitFor();
        await approve();
        const downgrade = page.getByRole("dialog", { name: "Confirm downgrade", exact: true });
        await downgrade.waitFor();
        await downgrade.getByText("You are about to downgrade this plugin.", { exact: true }).waitFor();
        await screen("plugin-downgrade-confirmation");
        await downgrade.getByRole("button", { name: "Confirm downgrade", exact: true }).click();
        await review().waitFor({ state: "hidden" });
        const downgraded = await record();
        assert.notEqual(downgraded.version, initial.version);
        assert.equal(downgraded.version_pin, downgraded.version);
        assert.equal(downgraded.automatic_updates, "disabled");
        assert.equal(downgraded.installation_id, initial.installation_id);

        await card().getByRole("button", { name: "Settings & access", exact: true }).click();
        const settings = page.getByRole("dialog").filter({ has: page.getByRole("button", { name: "Reinstall this release", exact: true }) });
        await settings.waitFor();
        await drop(settings.getByRole("region", { name: `Update package for ${initial.name}` }), other);
        const failure = settings.getByRole("alert").filter({ hasText: "plugin ID does not match" });
        await failure.waitFor();
        assert(await failure.evaluate(element => element === document.activeElement));
        await screen("plugin-update-active-error");
        await drop(settings.getByRole("region", { name: `Update package for ${initial.name}` }), same);
        await review().waitFor();
        await review().getByRole("button", { name: "Cancel", exact: true }).click();

        await drop(card(), same, "invalid.txt");
        const invalid = card().getByRole("alert");
        await invalid.waitFor();
        assert(await invalid.evaluate(element => element === document.activeElement));
        const errorBox = await invalid.boundingBox();
        assert(errorBox.y >= 0 && errorBox.y + errorBox.height <= (width <= 760 ? 800 : 1000), "Drop validation is visible immediately after focus.");
        await screen("plugin-drop-validation");
        await page.reload();
        const launcher = page.getByRole("region", { name: "Plugin package drop area", exact: true });
        await drop(launcher, same, "matching-release.upt");
        await review().waitFor();
        assert.equal(await page.getByRole("dialog", { name: "Already installed", exact: true }).count(), 0);
        await review().getByRole("button", { name: "Cancel", exact: true }).click();
        assert.deepEqual(errors, []);
        report.passed.push(`${width}/${theme}: direct card, update-control, settings and launcher drops; same-version cancel/apply; downgrade pins; active-dialog error; focused invalid-file warning; stable installation identity`);
        console.log(report.passed.at(-1));
      } catch (error) {
        await page.screenshot({ path: path.join(evidenceRoot, `plugin-update-failure-${width}-${theme}.png`) });
        console.error("Active update alerts: " + JSON.stringify(await page.getByRole("alert").allTextContents()));
        throw error;
      } finally { await context.close(); }
    }
  } finally {
    await restore();
    await admin.request.patch(origin + "/api/preferences", { data: { ui_theme: original.ui_theme } });
  }
}
