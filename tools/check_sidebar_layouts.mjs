// Run against a disposable production host; uses real installed contributions.
import assert from "node:assert/strict";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { createRequire } from "node:module";
import path from "node:path";

const [pluginsRoot, outputArgument, origin, cookiesFile] =
  process.argv.slice(2);
assert.ok(
  cookiesFile,
  "Usage: check_sidebar_layouts.mjs <plugins> <output> <host-url> <admin-cookies>",
);
const require = createRequire(path.resolve(pluginsRoot, "package.json"));
const { chromium, webkit } = require("playwright");
const output = path.resolve(outputArgument);
await mkdir(output, { recursive: true });
const report = {
  status: "running",
  host_source_head: process.env.SIDEBAR_HOST_HEAD ?? null,
  limitation:
    "Long account and brand labels are browser-only layout stress fixtures; authentication and plugin navigation use the real host.",
  measurements: [],
  captures: [],
};
const cookies = JSON.parse(await readFile(cookiesFile, "utf8")).map(
  ({ name, value }) => ({ name, value, url: origin }),
);
const admin = await chromium.launch({ headless: true, args: ["--no-sandbox"] });
const adminContext = await admin.newContext();
await adminContext.addCookies(cookies);
const disabledDemos = [];
try {
  const installed = await (
    await adminContext.request.get(origin + "/api/plugins")
  ).json();
  for (const item of installed) {
    if (
      item.enabled &&
      [
        "example.help-button",
        "example.ui-playground",
        "example.shortcut-playground",
      ].includes(item.plugin_id)
    ) {
      const response = await adminContext.request.post(
        `${origin}/api/plugins/${item.plugin_id}/disable`,
      );
      assert.equal(response.status(), 200);
      disabledDemos.push(item.plugin_id);
    }
  }
  report.layout_demo_overlays_disabled = disabledDemos;
  for (const browserType of [chromium, webkit]) {
    const browser = await browserType.launch({
      headless: true,
      ...(browserType === chromium ? { args: ["--no-sandbox"] } : {}),
    });
    try {
      for (const [mode, width, height, sidebarWidth] of [
        ["pinned", 1440, 900, 200],
        ["pinned", 1440, 900, 232],
        ["pinned", 1920, 1050, 440],
        ["rail", 1024, 600, 200],
        ["rail", 768, 600, 232],
        ["overlay", 1440, 900, 200],
        ["overlay", 768, 600, 200],
        ["pinned", 1024, 350, 200],
        ["overlay", 320, 600, 232],
        ["overlay", 390, 600, 232],
        ["overlay", 256, 320, 232],
        ["overlay", 200, 280, 232],
      ]) {
        const context = await browser.newContext({
          viewport: { width, height },
          hasTouch: width <= 760,
        });
        await context.addCookies(cookies);
        await context.addInitScript(
          ({ mode, sidebarWidth }) => {
            localStorage.setItem("sidebarMode", mode);
            localStorage.setItem("sidebarWidth", String(sidebarWidth));
          },
          { mode, sidebarWidth },
        );
        const page = await context.newPage(),
          errors = [];
        page.on("pageerror", (error) => errors.push(String(error)));
        try {
          await page.goto(origin + "/statistics");
          await page
            .getByRole("heading", { name: "Statistics", exact: true, level: 1 })
            .waitFor();
          if (mode === "overlay" || width <= 760)
            await page
              .getByRole("button", { name: "Open menu", exact: true })
              .click();
          else if (mode === "rail")
            await page
              .getByRole("button", { name: "Expand navigation", exact: true })
              .click();
          const pane = page.locator("#app-navigation");
          await pane.waitFor({ state: "visible" });
          for (const label of ["Games", "Media"]) {
            const button = pane.getByRole("button", {
              name: label,
              exact: true,
            });
            if ((await button.getAttribute("aria-expanded")) !== "true")
              await button.click();
          }
          await page.evaluate(() => {
            for (const folder of document.querySelectorAll(
              "#app-navigation details",
            ))
              folder.open = true;
            document.querySelector(".account-label strong").textContent =
              "UnbrokenAccountLabelForSidebarOverflowReview";
            document.querySelector(".brand-name").textContent =
              "AReallyLongCustomApplicationBrand";
          });
          await page.evaluate(() =>
            Promise.all(
              document
                .getAnimations()
                .filter((a) => a.effect?.getTiming().iterations !== Infinity)
                .map((a) => a.finished.catch(() => {})),
            ),
          );
          const measurement = await pane.evaluate((element) => ({
            sidebar: {
              width: element.clientWidth,
              scroll: element.scrollWidth,
              x: getComputedStyle(element).overflowX,
            },
            containers: [
              ...element.querySelectorAll(
                ".nav-body,.nav-scroll,.nav-footer,.nav-brand",
              ),
            ].map((node) => ({
              class: node.className,
              width: node.clientWidth,
              scroll: node.scrollWidth,
              height: node.clientHeight,
              scrollHeight: node.scrollHeight,
              x: getComputedStyle(node).overflowX,
              y: getComputedStyle(node).overflowY,
            })),
          }));
          const label = `${browserType.name()}/${mode}/${width}x${height}/${sidebarWidth}`;
          report.measurements.push({ case: label, ...measurement });
          assert.ok(
            measurement.sidebar.scroll <= measurement.sidebar.width + 1,
            `${label}: sidebar overflow ${JSON.stringify(measurement)}`,
          );
          for (const node of measurement.containers)
            assert.ok(
              node.scroll <= node.width + 1,
              `${label}: ${node.class} horizontal overflow ${JSON.stringify(node)}`,
            );
          for (const control of [
            pane.getByRole("link", { name: "All games", exact: true }),
            pane.getByRole("link", { name: "Preferences", exact: true }),
            pane.getByRole("link", { name: "Your account", exact: true }),
          ]) {
            await control.scrollIntoViewIfNeeded();
            await control.hover({ timeout: 5000 });
            const bounds = await control.boundingBox(),
              edge = await pane.boundingBox();
            assert.ok(
              bounds.y >= edge.y &&
                bounds.y + bounds.height <= edge.y + edge.height + 1,
              `${label}: ${await control.getAttribute("aria-label")} can be scrolled into the menu`,
            );
          }
          if (
            browserType === webkit &&
            [320, 1440].includes(width) &&
            mode === "overlay"
          ) {
            const filename = `sidebar-${mode}-${width}-webkit.png`;
            await page.screenshot({ path: path.join(output, filename) });
            report.captures.push(filename);
          }
          assert.deepEqual(errors, []);
          console.log(label + " passes");
        } catch (error) {
          await page.screenshot({
            path: path.join(
              output,
              `sidebar-private-failure-${browserType.name()}-${mode}-${width}-${height}.png`,
            ),
          });
          throw error;
        } finally {
          await context.close();
        }
      }
    } finally {
      await browser.close();
    }
  }
  report.status = "passed";
} catch (error) {
  report.status = "failed";
  throw error;
} finally {
  for (const id of disabledDemos) {
    assert.equal(
      (
        await adminContext.request.post(`${origin}/api/plugins/${id}/enable`)
      ).status(),
      200,
    );
  }
  await admin.close();
  await writeFile(
    path.join(output, "sidebar-conformance.json"),
    JSON.stringify(report, null, 2) + "\n",
  );
}
