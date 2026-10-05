// Use only a disposable host: installs reference themes and creates one temporary user.
import assert from "node:assert/strict";
import { createHash, randomBytes } from "node:crypto";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { createRequire } from "node:module";
import path from "node:path";

const [pluginsArgument, outputArgument, origin, cookieFile, packageArgument] =
  process.argv.slice(2);
assert.ok(
  packageArgument,
  "Usage: check_installed_theme_ui.mjs <plugins> <output> <host-url> <admin-cookies> <theme-packages>",
);
const output = path.resolve(outputArgument),
  packages = path.resolve(packageArgument);
await mkdir(output, { recursive: true });
const require = createRequire(
  path.join(path.resolve(pluginsArgument), "package.json"),
);
const { chromium } = require("playwright");
const browser = await chromium.launch({
  headless: true,
  args: ["--no-sandbox"],
});
const admin = await browser.newContext({
  viewport: { width: 1440, height: 1050 },
  colorScheme: "light",
});
await admin.addCookies(
  JSON.parse(await readFile(cookieFile, "utf8")).map(({ name, value }) => ({
    name,
    value,
    url: origin,
  })),
);
const page = await admin.newPage(),
  errors = [],
  disabled = [],
  users = [],
  installed = [];
page.on("pageerror", (error) => errors.push(String(error)));
const report = {
  status: "running",
  real_production_host: true,
  theme_artifact_id: process.env.THEME_ARTIFACT_ID ?? null,
  theme_source_head: process.env.THEME_SOURCE_HEAD ?? null,
  host_source_head: process.env.THEME_HOST_HEAD ?? null,
  packages: [],
  passed: [],
  captures: [],
  measurements: [],
};
async function http(context, method, route, data, expected = 200) {
  const response = await context.request.fetch(origin + "/api" + route, {
    method,
    ...(data === undefined ? {} : { data }),
  });
  assert.equal(
    response.status(),
    expected,
    `${method} ${route}: HTTP ${response.status()}`,
  );
  return expected === 204 ? null : response.json();
}
function checkpoint(message) {
  report.passed.push(message);
  console.log(message);
}
async function rootTheme(target) {
  const digest = report.packages.find((theme) => theme.id === target)?.sha256;
  await page.waitForFunction(
    (id) => document.documentElement.dataset.themePackage === id,
    target,
  );
  if (target !== "native")
    await page.waitForFunction(
      (expected) => document.documentElement.dataset.themeRevision === expected,
      digest,
    );
}
async function screen(name) {
  // Sidebar layout animates when crossing the phone breakpoint; measure its
  // settled state rather than a frame still carrying the desktop margin.
  await page.waitForFunction(
    () => document.documentElement.scrollWidth <= innerWidth + 1,
    undefined,
    { timeout: 5000 },
  );
  await page.waitForFunction(
    () =>
      document
        .getAnimations()
        .every(
          (animation) =>
            !Number.isFinite(animation.effect?.getComputedTiming().endTime) ||
            animation.playState !== "running",
        ),
    undefined,
    { timeout: 5000 },
  );
  const dimensions = await page.evaluate(() => {
    const probe = document.createElement("span");
    probe.style.cssText =
      "position:fixed;width:0;height:0;color:var(--ui-border-strong)";
    document.documentElement.append(probe);
    const thumb = getComputedStyle(probe).color;
    probe.style.color = "var(--ui-surface-2)";
    const track = getComputedStyle(probe).color;
    probe.style.color = "var(--ui-dim)";
    const hover = getComputedStyle(probe).color;
    probe.remove();
    return {
      width: innerWidth,
      scroll: document.documentElement.scrollWidth,
      sidebarScroll: document.querySelector(".nav-scroll")?.scrollWidth,
      sidebarClient: document.querySelector(".nav-scroll")?.clientWidth,
      scrollbar: getComputedStyle(document.documentElement).scrollbarColor,
      scrollbarThumb: getComputedStyle(
        document.documentElement,
        "::-webkit-scrollbar-thumb",
      ).backgroundColor,
      scrollbarTrack: getComputedStyle(
        document.documentElement,
        "::-webkit-scrollbar-track",
      ).backgroundColor,
      expectedScrollbar: `${thumb} ${track}`,
      expectedThumb: thumb,
      expectedTrack: track,
      expectedHover: hover,
    };
  });
  assert.ok(
    dimensions.scroll <= dimensions.width + 1,
    name + ": viewport overflow",
  );
  assert.ok(
    !dimensions.sidebarClient ||
      dimensions.sidebarScroll <= dimensions.sidebarClient + 1,
    name + ": sidebar overflow",
  );
  await page.screenshot({ path: path.join(output, name) });
  assert.ok(
    dimensions.width <= 760 || dimensions.sidebarClient > 0,
    name + ": measured sidebar missing",
  );
  report.captures.push(name);
  assert.equal(
    dimensions.scrollbar,
    dimensions.expectedScrollbar,
    name + ": scrollbar colors must follow the active theme tokens",
  );
  assert.equal(dimensions.scrollbarTrack, dimensions.expectedTrack);
  assert.ok(
    [dimensions.expectedThumb, dimensions.expectedHover].includes(
      dimensions.scrollbarThumb,
    ),
  );
  report.measurements.push({ name, ...dimensions });
}
const original = await http(admin, "GET", "/preferences");
try {
  assert.equal((await http(admin, "GET", "/auth/me")).is_admin, true);
  assert.deepEqual(await http(admin, "GET", "/themes/manage"), {
    default_theme: "native",
    themes: [],
  });
  for (const plugin of await http(admin, "GET", "/plugins")) {
    if (
      [
        "example.help-button",
        "example.ui-playground",
        "example.shortcut-playground",
      ].includes(plugin.plugin_id) &&
      plugin.enabled
    ) {
      await http(admin, "POST", `/plugins/${plugin.plugin_id}/disable`);
      disabled.push(plugin.plugin_id);
    }
  }
  await http(admin, "PATCH", "/preferences", {
    ui_theme: "light",
    ui_palette: "orange",
    ui_theme_package: "server",
    ui_welcome_completed: true,
  });
  await page.goto(origin + "/settings?area=administration&section=themes");
  await page.getByLabel("Server default", { exact: true }).waitFor();
  for (const [id, name] of [
    ["official.forest", "Forest"],
    ["example.purple-blocks", "Purple Blocks"],
  ]) {
    const filename = `${id}-1.0.0.utt`,
      file = path.join(packages, filename);
    const bytes = await readFile(file);
    await page.getByLabel("Theme package", { exact: true }).setInputFiles(file);
    const dialog = page.getByRole("dialog", {
      name: "Review theme",
      exact: true,
    });
    await dialog.getByRole("heading", { name, exact: true }).waitFor();
    if (id === "official.forest")
      await screen("theme-install-review-1440-light.png");
    await dialog
      .getByRole("button", { name: "Install theme", exact: true })
      .click();
    await dialog.waitFor({ state: "hidden" });
    installed.push(id);
    await page.getByRole("heading", { name, exact: true }).waitFor();
    const catalogue = await http(admin, "GET", "/themes/manage");
    const entry = catalogue.themes.find((theme) => theme.id === id);
    assert.equal(
      entry.digest,
      createHash("sha256").update(bytes).digest("hex"),
    );
    report.packages.push({ id, version: entry.version, sha256: entry.digest });
    const css = await admin.request.get(
      `${origin}/api/themes/assets/${id}/${entry.digest}/${entry.stylesheet}`,
    );
    assert.equal(css.status(), 200);
    assert.match(css.headers()["content-type"], /text\/css/);
    assert.match(await css.text(), /data-theme-package/);
  }
  await page
    .getByLabel("Server default", { exact: true })
    .selectOption("official.forest");
  await rootTheme("official.forest");
  assert.equal(
    (await http(admin, "GET", "/themes")).default_theme,
    "official.forest",
  );
  checkpoint(
    "Both exact CI themes install through metadata review; their digest CSS loads and Forest becomes the server default",
  );
  await screen("themes-manager-1440-light.png");
  await page.goto(origin + "/settings?area=preferences&section=appearance");
  await page
    .getByRole("combobox", { name: "Interface theme", exact: true })
    .selectOption("official.forest");
  await page.getByLabel("Theme", { exact: true }).selectOption("dark");
  await page.waitForFunction(
    () => document.documentElement.dataset.theme === "dark",
  );
  await rootTheme("official.forest");
  await page.waitForFunction(async () => {
    const preferences = await (await fetch("/api/preferences")).json();
    return (
      preferences.ui_theme === "dark" &&
      preferences.ui_theme_package === "official.forest"
    );
  });
  await page.reload();
  await page
    .getByRole("combobox", { name: "Interface theme", exact: true })
    .waitFor();
  assert.equal(
    (await http(admin, "GET", "/preferences")).ui_theme_package,
    "official.forest",
  );
  await page
    .getByRole("combobox", { name: "Save theme choices to", exact: true })
    .selectOption("device");
  await page
    .getByRole("combobox", { name: "Interface theme", exact: true })
    .selectOption("example.purple-blocks");
  await page.getByLabel("Theme", { exact: true }).selectOption("light");
  await page.waitForFunction(
    () => document.documentElement.dataset.theme === "light",
  );
  await rootTheme("example.purple-blocks");
  const account = await http(admin, "GET", "/preferences");
  assert.equal(account.ui_theme_package, "official.forest");
  assert.equal(account.ui_theme, "dark");
  const cookie = (await admin.cookies()).find(
    (item) => item.name === "uta-ui-preferences",
  );
  assert.ok(cookie);
  assert.deepEqual(
    [
      JSON.parse(decodeURIComponent(cookie.value)).scope,
      JSON.parse(decodeURIComponent(cookie.value)).themePackage,
    ],
    ["device", "example.purple-blocks"],
  );
  await page.reload();
  await rootTheme("example.purple-blocks");
  assert.equal(
    await page
      .getByRole("combobox", { name: "Save theme choices to", exact: true })
      .inputValue(),
    "device",
  );
  const squares = await page.evaluate(() => ({
    card: getComputedStyle(document.documentElement)
      .getPropertyValue("--ui-radius-card")
      .trim(),
    control: getComputedStyle(document.documentElement)
      .getPropertyValue("--ui-radius-control")
      .trim(),
    buttons: [
      ...document.querySelectorAll(".navigation button, .navigation a"),
    ].map((button) => getComputedStyle(button).borderRadius),
  }));
  assert.equal(squares.card, "0px");
  assert.equal(squares.control, "0px");
  assert.ok(
    squares.buttons.length > 0 &&
      squares.buttons.every((radius) => radius === "0px"),
  );
  checkpoint(
    "Account appearance survives reload; browser-only Purple Blocks and light mode persist without changing account choices, including square sidebar controls",
  );
  await screen("theme-purple-appearance-1440-light.png");
  for (const [width, mode, id] of [
    [320, "light", "example.purple-blocks"],
    [390, "dark", "official.forest"],
    [768, "dark", "example.purple-blocks"],
    [1440, "light", "official.forest"],
    [1920, "dark", "example.purple-blocks"],
  ]) {
    await page.setViewportSize({ width, height: width < 500 ? 800 : 1050 });
    await page
      .getByRole("combobox", { name: "Interface theme", exact: true })
      .selectOption(id);
    await page.getByLabel("Theme", { exact: true }).selectOption(mode);
    await rootTheme(id);
    await page.waitForFunction(
      (theme) => document.documentElement.dataset.theme === theme,
      mode,
    );
    await screen(`theme-appearance-${width}-${mode}.png`);
    await page.goto(origin + "/settings?area=administration&section=themes");
    await page.getByLabel("Server default", { exact: true }).waitFor();
    await screen(`theme-management-${width}-${mode}.png`);
    await page.goto(origin + "/settings?area=preferences&section=appearance");
    await page
      .getByRole("combobox", { name: "Interface theme", exact: true })
      .waitFor();
  }
  checkpoint(
    "Installed theme menus, previews and administrator controls fit phone, tablet and wide desktop viewports with themed scrollbars and no sidebar overflow",
  );
  const anonymous = await browser.newContext({
    viewport: { width: 390, height: 800 },
    colorScheme: "dark",
  });
  const signIn = await anonymous.newPage();
  for (const route of ["/login", "/login/oidcstart"]) {
    await signIn.goto(origin + route);
    await signIn.waitForFunction(
      () =>
        document.documentElement.dataset.themePackage === "official.forest" &&
        document.documentElement.dataset.themeRevision?.length === 64,
    );
    assert.equal(
      await signIn.evaluate(() =>
        getComputedStyle(document.documentElement)
          .getPropertyValue("--ui-bg")
          .trim(),
      ),
      "#111e17",
    );
    const name =
      route === "/login"
        ? "theme-sign-in-390-dark.png"
        : "theme-oidc-390-dark.png";
    await signIn.screenshot({ path: path.join(output, name) });
    report.captures.push(name);
  }
  await anonymous.close();
  checkpoint(
    "A fresh unauthenticated browser uses the server theme on sign-in and OIDC entry pages",
  );
  const username = "theme-review-" + randomBytes(6).toString("hex"),
    password = "Theme-" + randomBytes(12).toString("hex") + "9!";
  const user = await http(
    admin,
    "POST",
    "/auth/users",
    { username, email: username + "@example.invalid", password },
    201,
  );
  users.push(user.id);
  const ordinary = await browser.newContext({
    viewport: { width: 1440, height: 1050 },
    colorScheme: "light",
  });
  await ordinary.addCookies(
    (await admin.cookies()).filter(
      (item) => item.name === "uta-ui-preferences",
    ),
  );
  await http(ordinary, "POST", "/auth/login", {
    username_or_email: username,
    password,
  });
  await http(ordinary, "PATCH", "/preferences", { ui_welcome_completed: true });
  const personal = await ordinary.newPage();
  await personal.goto(origin + "/settings?area=preferences&section=appearance");
  await personal
    .getByRole("combobox", { name: "Save theme choices to", exact: true })
    .waitFor();
  assert.equal(
    await personal
      .getByRole("combobox", { name: "Save theme choices to", exact: true })
      .inputValue(),
    "device",
  );
  assert.equal(
    (await http(ordinary, "GET", "/preferences")).ui_theme_package,
    "server",
  );
  await personal
    .getByRole("combobox", { name: "Save theme choices to", exact: true })
    .selectOption("account");
  await personal
    .getByRole("combobox", { name: "Interface theme", exact: true })
    .selectOption("official.forest");
  await personal.waitForFunction(
    () => document.documentElement.dataset.themePackage === "official.forest",
  );
  const deniedFile = await readFile(
    path.join(packages, "official.forest-1.0.0.utt"),
  );
  assert.equal(
    (
      await ordinary.request.post(origin + "/api/themes/install", {
        multipart: {
          file: {
            name: "forest.utt",
            mimeType: "application/zip",
            buffer: deniedFile,
          },
        },
      })
    ).status(),
    403,
  );
  await http(ordinary, "GET", "/themes/manage", undefined, 403);
  await http(ordinary, "PUT", "/themes/default", { theme_id: "native" }, 403);
  await http(
    ordinary,
    "PATCH",
    "/themes/official.forest",
    { enabled: false },
    403,
  );
  await http(ordinary, "DELETE", "/themes/official.forest", undefined, 403);
  checkpoint(
    "Browser cosmetic choices carry no account preferences into a second user; ordinary users select themes but cannot install or manage server themes",
  );
  await page.goto(origin + "/settings?area=administration&section=themes");
  const forest = page.locator("article.theme-card").filter({
    has: page.getByRole("heading", { name: "Forest", exact: true }),
  });
  await forest.getByLabel("Enabled", { exact: true }).uncheck();
  await page.waitForFunction(
    async () =>
      (await (await fetch("/api/themes")).json()).default_theme === "native",
  );
  await personal.reload();
  await personal
    .getByText("This theme is unavailable in the current color mode.", {
      exact: false,
    })
    .waitFor();
  await personal.waitForFunction(
    () => document.documentElement.dataset.themePackage === "native",
  );
  assert.equal(
    (await http(ordinary, "GET", "/preferences")).ui_theme_package,
    "official.forest",
  );
  await forest.getByLabel("Enabled", { exact: true }).check();
  await personal.reload();
  await personal.waitForFunction(
    () =>
      document.documentElement.dataset.themePackage === "official.forest" &&
      document.documentElement.dataset.themeRevision?.length === 64,
  );
  checkpoint(
    "Disabling a server-default theme repairs the default and safely falls back for personal selections; re-enabling restores the retained personal choice",
  );
  await ordinary.close();
  await page.setViewportSize({ width: 1440, height: 1050 });
  const purple = page.locator("article.theme-card").filter({
    has: page.getByRole("heading", { name: "Purple Blocks", exact: true }),
  });
  await purple.getByRole("button", { name: "Remove", exact: true }).click();
  const confirmation = page.getByRole("dialog", {
    name: "Remove theme",
    exact: true,
  });
  await confirmation
    .getByRole("button", { name: "Remove theme", exact: true })
    .click();
  await purple.waitFor({ state: "hidden" });
  await rootTheme("native");
  assert.deepEqual(errors, []);
  checkpoint(
    "Removal confirmation clears installed styles without leaving the current browser on a missing CSS package",
  );
  report.status = "passed";
  await writeFile(
    path.join(output, "theme-ui-conformance.json"),
    JSON.stringify(report, null, 2) + "\n",
  );
} catch (error) {
  report.status = "failed";
  await page.screenshot({
    path: path.join(output, "theme-ui-private-failure.png"),
  });
  await writeFile(
    path.join(output, "theme-ui-conformance.json"),
    JSON.stringify(report, null, 2) + "\n",
  );
  throw error;
} finally {
  for (const id of users.reverse())
    await http(admin, "DELETE", `/auth/users/${id}`);
  const remaining = await http(admin, "GET", "/themes/manage");
  for (const id of installed.reverse())
    if (remaining.themes.some((theme) => theme.id === id))
      await http(admin, "DELETE", `/themes/${id}`, undefined, 204);
  await http(admin, "PATCH", "/preferences", original);
  for (const id of disabled) await http(admin, "POST", `/plugins/${id}/enable`);
  await browser.close();
}
