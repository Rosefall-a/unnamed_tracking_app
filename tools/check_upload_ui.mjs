import assert from "node:assert/strict";
import path from "node:path";

export async function checkUploadUi({ admin, origin, evidenceRoot, report, checkOverflow }) {
  const original = await (await admin.request.get(origin + "/api/preferences")).json();
  const page = await admin.newPage(), errors = [];
  page.on("pageerror", error => errors.push(String(error)));
  const uploaded = [];
  try {
    for (const theme of ["light", "dark"]) {
      assert.equal((await admin.request.patch(origin + "/api/preferences", { data: { ui_theme: theme } })).status(), 200);
      for (const width of [320, 390, 760, 1024, 1440, 1920]) {
        await page.setViewportSize({ width, height: 1050 });
        await page.goto(origin + "/upload");
        await page.getByRole("heading", { name: "Upload", level: 1, exact: true }).waitFor();
        assert.equal(new URL(page.url()).pathname, "/upload");
        await page.waitForFunction(mode => document.documentElement.dataset.theme === mode, theme);
        await page.getByText("Drop screenshots or clips here", { exact: true }).waitFor();
        assert.equal(await page.getByRole("navigation", { name: "Settings areas" }).count(), 0);
        await checkOverflow(page, `upload/${width}/${theme}`);
        if (width === 390) {
          const filename = `upload-check-${theme}-${Date.now()}.png`;
          const before = (await (await admin.request.get(origin + "/api/media/inbox")).json()).media;
          await page.locator('input[type="file"]').setInputFiles({ name: filename, mimeType: "image/png",
            buffer: Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aO1sAAAAASUVORK5CYII=", "base64") });
          await page.locator(".form-success").getByText("1 uploaded.", { exact: true }).waitFor();
          const items = (await (await admin.request.get(origin + "/api/media/inbox")).json()).media;
          const item = items.find(item => !before.some(previous => previous.filename === item.filename));
          assert(item, "The selected file must be uploaded through the real endpoint");
          uploaded.push(item);
          const toast = page.locator(".task-toast").filter({ hasText: "Uploading 1 file" });
          const navigation = page.getByRole("navigation", { name: "Primary navigation" });
          assert(await toast.evaluate((element) => element.getBoundingClientRect().bottom) <=
            await navigation.evaluate(element => element.getBoundingClientRect().top), "Task toast stays above phone navigation");
          await toast.getByRole("button", { name: "Dismiss Uploading 1 file", exact: true }).click();
          const select = page.getByRole("button", { name: `Select screenshot: ${item.filename}`, exact: true });
          await select.focus(); await page.keyboard.press("Space");
          assert.equal(await select.getAttribute("aria-pressed"), "true");
          await page.getByRole("button", { name: "Delete selected", exact: true }).click();
          const dialog = page.getByRole("dialog", { name: "Delete 1 item?", exact: true });
          await dialog.waitFor();
          await page.keyboard.press("Escape"); await dialog.waitFor({ state: "detached" });
          await page.getByRole("button", { name: "Delete selected", exact: true }).click();
          await dialog.getByRole("button", { name: "Delete", exact: true }).click();
          await select.waitFor({ state: "detached" });
          const trash = page.getByRole("button", { name: /^Recently deleted/ });
          await trash.click();
          const row = page.locator(".trash-row").filter({ hasText: filename });
          await row.getByRole("button", { name: "Restore", exact: true }).click();
          await select.waitFor();
          await checkOverflow(page, `upload-restored/${theme}`);
        }
        if (width === 390 && theme === "dark" || width === 1440 && theme === "light")
          await page.screenshot({ path: path.join(evidenceRoot, `upload-page-${width}-${theme}.png`) });
        report.screens.push({ width, theme, screen: "/upload" });
      }
    }
    for (const legacy of ["/inbox", "/settings?section=upload"]) {
      await page.goto(origin + legacy);
      await page.waitForURL(origin + "/upload");
      await page.getByRole("heading", { name: "Upload", level: 1 }).waitFor();
    }
    for (const section of ["users", "oidc", "limits", "plugins", "admin"]) {
      await page.goto(origin + `/settings?section=${section}`);
      const adminLink = page.getByRole("link", { name: "Administration", exact: true, includeHidden: true });
      await page.waitForFunction(() => document.querySelector('[aria-label="Administration"]')?.classList.contains("active"));
      assert((await adminLink.getAttribute("class")).split(/\s+/).includes("active"));
      assert(!(await page.getByRole("link", { name: "Preferences", exact: true, includeHidden: true }).getAttribute("class")).split(/\s+/).includes("active"));
    }
    assert.deepEqual(errors, []);
    report.passed.push("12 standalone Upload light/dark responsive cases and preserved legacy links", "Real PNG uploads, keyboard selection, accessible delete dialog/Escape and trash restoration", "Task progress uses the personal palette and stays above phone navigation", "Administration sidebar highlight follows five core sections and the legacy alias");
  } finally {
    for (const item of uploaded) await admin.request.delete(origin + `/api/media/inbox/${item.kind}/${encodeURIComponent(item.filename)}`);
    await admin.request.patch(origin + "/api/preferences", { data: { ui_theme: original.ui_theme } });
    await page.close();
  }
}
