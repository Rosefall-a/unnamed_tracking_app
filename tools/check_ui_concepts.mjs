// Checks design proposals only. This does not establish application/v1.1 acceptance.
import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { mkdir, writeFile } from "node:fs/promises";
import { fileURLToPath, pathToFileURL } from "node:url";
import path from "node:path";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const [pluginsRoot, evidenceRoot = path.join(root, ".validation/ui-concepts")] = process.argv.slice(2);
if (!pluginsRoot) throw new Error("Usage: node tools/check_ui_concepts.mjs /path/to/plugins [evidence-directory]");
const { chromium } = createRequire(path.resolve(pluginsRoot, "package.json"))("playwright");
const browser = await chromium.launch({ headless: true, args: ["--no-sandbox"] });
const page = await browser.newPage();
const errors = [];
page.on("pageerror", (error) => errors.push(String(error)));
try {
  await page.goto(pathToFileURL(path.join(root, "wiki/docs/assets/ui-redevelopment/concepts.html")).href);
  const frame = page.frames().find((item) => item !== page.mainFrame());
  await frame.waitForSelector("#uta-concepts .product");
  await mkdir(evidenceRoot, { recursive: true });
  const screens = ["home", "nav", "mobileHome", "mobileNav", "settings", "preferences", "account", "admin", "library", "plugin"];
  let cases = 0;
  const violations = [];
  for (const design of ["Archive", "Pocket", "Studio"]) {
    await frame.evaluate((selected) => {
      document.querySelectorAll("#uta-concepts>[data-variant]").forEach((element) => {
        element.hidden = element.dataset.variant !== selected;
      });
    }, design);
    const demo = frame.locator(`[data-design="${design}"]`);
    for (const width of [320, 390, 430, 768, 1024, 1440, 1920, 2560]) {
      await page.setViewportSize({ width, height: 1200 });
      for (const theme of ["light", "dark"]) {
        await demo.locator('[data-control="theme"]').selectOption(theme);
        for (const screen of screens) {
          await demo.locator('[data-control="screen"]').selectOption(screen);
          const overflows = await demo.evaluate((element) => {
            const product = element.querySelector(".product");
            const bounds = product.getBoundingClientRect();
            return [...product.querySelectorAll("button,input,select,h1,h2,h3,p,table")]
              .filter((item) => item.getClientRects().length)
              .filter((item) => {
                const box = item.getBoundingClientRect();
                return box.left < bounds.left - 1 || box.right > bounds.right + 1;
              })
              .map((item) => item.textContent.trim().slice(0, 90));
          });
          if (overflows.length) violations.push({ design, width, theme, screen, overflows });
          cases++;
        }
      }
    }
    await page.setViewportSize({ width: 1440, height: 1300 });
    const capture = async (screen, theme, suffix) => {
      await demo.locator('[data-control="theme"]').selectOption(theme);
      await demo.locator('[data-control="screen"]').selectOption(screen);
      await demo.locator(".product").screenshot({ path: path.join(evidenceRoot, `${design.toLowerCase()}-${suffix}.png`) });
    };
    await capture("home", "dark", "desktop");
    await capture("settings", "dark", "settings");
    await capture("admin", "dark", "administration");
    await capture("plugin", "dark", "plugin");
    await capture("mobileHome", "light", "mobile");
    await capture("mobileNav", "light", "mobile-navigation");
    await demo.locator('[data-control="role"]').selectOption("member");
    assert.equal(await demo.locator('.product [data-page="admin"]').count(), 0);
    await demo.locator('[data-control="screen"]').selectOption("settings");
    assert.equal(await demo.locator('.product [data-page="admin"]').count(), 0);
    await demo.locator('[data-control="screen"]').selectOption("plugin");
    await demo.locator('button[data-action="widget"]').click();
    await demo.locator('.product [data-page="home"]:visible').first().click();
    assert.match(await demo.locator("main").innerText(), /8h 24m/);
    await demo.locator('[data-control="screen"]').selectOption("library");
    await demo.locator('[data-filter="Backlog"]').click();
    assert.match(await demo.locator("main").innerText(), /Outer Wilds/);
    assert.doesNotMatch(await demo.locator("main").innerText(), /Disco Elysium/);
    await demo.locator('[data-control="screen"]').selectOption("account");
    await demo.locator('form button[type="submit"]').click();
    assert.match(await demo.locator(".toast").innerText(), /preview only/);
    await demo.locator('[data-control="role"]').selectOption("admin");
  }
  const result = { cases, violations, errors };
  await writeFile(path.join(evidenceRoot, "concept-checks.json"), JSON.stringify(result, null, 2) + "\n");
  console.log(JSON.stringify(result, null, 2));
  assert.deepEqual(errors, []);
  assert.deepEqual(violations, []);
} finally {
  await browser.close();
}
