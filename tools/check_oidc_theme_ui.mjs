// Real OIDC authorization/code/JWT exchange against a disposable local identity provider.
// No host API responses are mocked. Run only against a disposable server with no configured OIDC provider.
import assert from "node:assert/strict";
import { createServer, request as httpRequest } from "node:http";
import { generateKeyPairSync, randomUUID, sign } from "node:crypto";
import { readFile, mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const [pluginsRoot, evidenceRoot, backendUrl] = process.argv.slice(2);
assert(pluginsRoot && evidenceRoot && backendUrl && process.env.UI_REVIEW_USERNAME && process.env.UI_REVIEW_PASSWORD);
const { chromium } = createRequire(path.resolve(pluginsRoot, "package.json"))("playwright");
const frontend = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../src/frontend/dist");
const frontendServer = createServer(async (incoming, outgoing) => {
  if (/^\/(api\/|pwa\/|manifest\.webmanifest|service-worker\.js)/.test(incoming.url)) {
    const upstream = httpRequest(new URL(incoming.url, backendUrl), { method: incoming.method, headers: incoming.headers }, response => {
      outgoing.writeHead(response.statusCode, response.headers); response.pipe(outgoing);
    });
    upstream.on("error", () => { outgoing.writeHead(503); outgoing.end(); }); incoming.pipe(upstream); return;
  }
  const relative = decodeURIComponent(new URL(incoming.url, "http://localhost").pathname).slice(1);
  const file = path.resolve(frontend, relative.startsWith("assets/") ? relative : "index.html");
  if (!file.startsWith(frontend + path.sep)) { outgoing.writeHead(403); outgoing.end(); return; }
  try { outgoing.setHeader("Content-Type", ({ ".js": "text/javascript", ".css": "text/css", ".html": "text/html" })[path.extname(file)] || "application/octet-stream"); outgoing.end(await readFile(file)); }
  catch { outgoing.writeHead(404); outgoing.end(); }
});
await new Promise(resolve => frontendServer.listen(0, "127.0.0.1", resolve));
const origin = `http://127.0.0.1:${frontendServer.address().port}`;
const { privateKey, publicKey } = generateKeyPairSync("rsa", { modulusLength: 2048 });
const publicJwk = { ...publicKey.export({ format: "jwk" }), kid: "review-key", alg: "RS256", use: "sig" };
const authorizations = new Map(), codes = new Map();
let identity;
const idp = createServer(async (incoming, outgoing) => {
  const url = new URL(incoming.url, issuer);
  function json(value) { outgoing.setHeader("Content-Type", "application/json"); outgoing.end(JSON.stringify(value)); }
  if (url.pathname === "/.well-known/openid-configuration") return json({ issuer, authorization_endpoint: issuer + "/authorize", token_endpoint: issuer + "/token", userinfo_endpoint: issuer + "/userinfo", jwks_uri: issuer + "/jwks", response_types_supported: ["code"], subject_types_supported: ["public"], id_token_signing_alg_values_supported: ["RS256"], token_endpoint_auth_methods_supported: ["client_secret_basic"] });
  if (url.pathname === "/jwks") return json({ keys: [publicJwk] });
  if (url.pathname === "/authorize") {
    assert.equal(url.searchParams.get("client_id"), "ui-theme-review");
    const state = url.searchParams.get("state");
    const redirect = url.searchParams.get("redirect_uri");
    assert(redirect.startsWith(origin + "/api/auth/oidc/callback/"));
    assert(state && url.searchParams.get("nonce"));
    authorizations.set(state, { redirect, nonce: url.searchParams.get("nonce") });
    outgoing.setHeader("Content-Type", "text/html");
    return outgoing.end(`<form method="post" action="/confirm"><input type="hidden" name="state" value="${state}"><button>Sign in to the review account</button></form>`);
  }
  if (url.pathname === "/confirm" && incoming.method === "POST") {
    let body = ""; for await (const chunk of incoming) body += chunk;
    const state = new URLSearchParams(body).get("state"), request = authorizations.get(state);
    assert(request); authorizations.delete(state);
    const code = randomUUID(); codes.set(code, request);
    const callback = new URL(request.redirect); callback.searchParams.set("code", code); callback.searchParams.set("state", state);
    outgoing.writeHead(303, { Location: callback.href }); return outgoing.end();
  }
  if (url.pathname === "/token" && incoming.method === "POST") {
    assert.equal(incoming.headers.authorization, "Basic " + Buffer.from("ui-theme-review:temporary-review-secret").toString("base64"));
    let body = ""; for await (const chunk of incoming) body += chunk;
    const params = new URLSearchParams(body), request = codes.get(params.get("code"));
    assert(request); codes.delete(params.get("code")); assert.equal(params.get("redirect_uri"), request.redirect);
    const now = Math.floor(Date.now() / 1000);
    const header = Buffer.from(JSON.stringify({ alg: "RS256", kid: "review-key", typ: "JWT" })).toString("base64url");
    const payload = Buffer.from(JSON.stringify({ ...identity, iss: issuer, aud: "ui-theme-review", iat: now, exp: now + 300, nonce: request.nonce })).toString("base64url");
    const token = header + "." + payload;
    return json({ access_token: "temporary-review-access", token_type: "Bearer", expires_in: 300, id_token: token + "." + sign("RSA-SHA256", Buffer.from(token), privateKey).toString("base64url") });
  }
  if (url.pathname === "/userinfo") return json(identity);
  outgoing.writeHead(404); outgoing.end();
});
await new Promise(resolve => idp.listen(0, "127.0.0.1", resolve));
const issuer = `http://127.0.0.1:${idp.address().port}`;
const browser = await chromium.launch({ headless: true, args: ["--no-sandbox"] });
const admin = await browser.newContext();
let original;
const members = new Map();
const report = { status: "running", cases: [], passed: [], screenshots: [] }, errors = [];
const custom = {
  light: { background: "#f2f1f8", surface: "#ffffff", surface_alt: "#e9e7f4", text: "#222534", muted: "#525568", accent: "#4b4fa8", success: "#216e3e", warning: "#855000", error: "#b42318", info: "#265a8b", purple: "#6951a2" },
  dark: { background: "#1b1725", surface: "#282232", surface_alt: "#352e42", text: "#f0ebf9", muted: "#bdb1ce", accent: "#b9a2ef", success: "#96d5a9", warning: "#f2c87a", error: "#ffa6a0", info: "#a2c8ef", purple: "#c6b5f1" },
};
async function json(response, expected = 200) { assert.equal(response.status(), expected, await response.text()); return response.json(); }
async function appearance(page, palette, mode) {
  await page.waitForFunction(({ palette, mode }) => document.documentElement.dataset.palette === palette && document.documentElement.dataset.theme === mode, { palette, mode });
  const values = await page.evaluate(() => ({ background: getComputedStyle(document.body).backgroundColor, color: getComputedStyle(document.documentElement).getPropertyValue("--ui-bg").trim(), width: innerWidth, content: document.documentElement.scrollWidth }));
  assert(values.content <= values.width + 1);
  assert.equal(await page.locator('meta[name="theme-color"]').getAttribute("content"), values.color);
  return values;
}
try {
  await mkdir(evidenceRoot, { recursive: true });
  await json(await admin.request.post(origin + "/api/auth/login", { data: { username_or_email: process.env.UI_REVIEW_USERNAME, password: process.env.UI_REVIEW_PASSWORD } }));
  original = await json(await admin.request.get(origin + "/api/settings/deployment"));
  assert.equal(original.oidc.named_providers.length, 0, "Use a disposable server without configured OIDC providers; saved secrets must remain untouched.");
  assert.equal(original.oidc.client_secret_configured, false);
  const name = `ui-oidc-${Date.now()}`;
  for (const slug of ["palette", "branded", "hidden"]) {
    const username = name + "-" + slug;
    const member = await json(await admin.request.post(origin + "/api/auth/users", { data: { username, email: username + "@example.invalid", password: process.env.UI_REVIEW_PASSWORD, is_admin: false } }), 201);
    members.set(slug, { id: member.id, username });
  }
  const providers = [
    { name: "Palette sign-in", slug: "palette", button_colour: "", autostart_enabled: true, show_on_login: true },
    { name: "Branded sign-in", slug: "branded", button_colour: "#7557e8", autostart_enabled: false, show_on_login: true },
    { name: "Hidden entry", slug: "hidden", button_colour: "", autostart_enabled: true, show_on_login: false },
  ].map(provider => ({ ...provider, issuer_url: issuer, client_id: "ui-theme-review", client_secret: "temporary-review-secret", enabled: true, button_text: provider.name }));
  await json(await admin.request.put(origin + "/api/settings/deployment", { data: { oidc_enabled: true, oidc_default_login_method: "sso", oidc_providers_json: JSON.stringify(providers) } }));
  for (const width of [390, 1440]) for (const palette of ["orange", "green", "custom"]) for (const mode of ["light", "dark"]) {
    console.log(`OIDC review: ${width}px ${palette} ${mode}`);
    const member = members.get(palette === "green" ? "hidden" : palette === "custom" ? "branded" : "palette");
    identity = { sub: member.username, email: member.username + "@example.invalid", email_verified: true, preferred_username: member.username, groups: [] };
    const context = await browser.newContext({ viewport: { width, height: 900 }, colorScheme: mode });
    const page = await context.newPage(); page.on("pageerror", error => errors.push(String(error)));
    try {
      await json(await context.request.post(origin + "/api/auth/login", { data: { username_or_email: member.username, password: process.env.UI_REVIEW_PASSWORD } }));
      await json(await context.request.patch(origin + "/api/preferences", { data: { ui_theme: mode, ui_palette: palette, ui_custom_palette: custom, ui_welcome_completed: true } }));
      await page.goto(origin + "/settings?section=appearance");
      await page.getByLabel("Palette", { exact: true }).waitFor(); await appearance(page, palette, mode);
      await json(await context.request.post(origin + "/api/auth/logout"));
      await page.goto(origin + "/login");
      await page.getByRole("button", { name: "Palette sign-in", exact: true }).waitFor();
      const colors = await appearance(page, palette, mode);
      assert.equal(await page.getByRole("button", { name: "Palette sign-in", exact: true }).evaluate(element => getComputedStyle(element).backgroundColor), await page.getByRole("button", { name: "Palette sign-in", exact: true }).evaluate(element => { const probe = document.createElement("span"); probe.style.color = getComputedStyle(document.documentElement).getPropertyValue("--ui-accent"); document.body.append(probe); const value = getComputedStyle(probe).color; probe.remove(); return value; }));
      assert.equal(await page.getByRole("button", { name: "Branded sign-in", exact: true }).evaluate(element => getComputedStyle(element).color), "rgb(255, 255, 255)");
      assert.equal(await page.getByRole("button", { name: "Hidden entry", exact: true }).count(), 0);
      await page.goto(origin + "/login/local"); await page.getByLabel("Username or email", { exact: true }).waitFor();
      assert.equal((await appearance(page, palette, mode)).background, colors.background);
      await page.goto(origin + "/api/auth/oidc/callback/palette?state=invalid&code=invalid");
      await page.getByText("SSO authentication failed. Please try again.", { exact: true }).waitFor();
      assert.equal((await appearance(page, palette, mode)).background, colors.background);
      await page.goto(origin + "/login/missing");
      await page.getByText("SSO is not configured yet.", { exact: true }).waitFor(); await appearance(page, palette, mode);
      await page.goto(origin + "/login?return_to=%2Fstatistics");
      if (palette === "custom") {
        const shot = `oidc-login-${width}-${mode}.png`; await page.getByRole("button", { name: "Palette sign-in", exact: true }).waitFor();
        await page.screenshot({ path: path.join(evidenceRoot, shot) }); report.screenshots.push(shot);
      }
      if (palette === "green") await page.goto(origin + "/login/hidden?return_to=%2Fstatistics");
      else await page.getByRole("button", { name: palette === "custom" ? "Branded sign-in" : "Palette sign-in", exact: true }).click();
      await page.getByRole("button", { name: "Sign in to the review account", exact: true }).click();
      await page.waitForURL(origin + "/statistics");
      assert.equal((await json(await context.request.get(origin + "/api/auth/me"))).id, member.id);
      await appearance(page, palette, mode);
      assert.equal((await context.request.get(origin + "/api/settings/deployment")).status(), 403);
      report.cases.push({ width, palette, mode, callback: "verified RS256", personal_preferences: "preserved" });
    } catch (error) {
      console.error(JSON.stringify({ width, palette, mode, surface: page.url().startsWith(origin) ? "host" : page.url().startsWith(issuer) ? "identity-provider" : "other", path: new URL(page.url()).pathname, headings: await page.locator("h1,h2,[role=alert]").allTextContents(), errors }));
      throw error;
    } finally { await context.close(); }
  }
  assert.deepEqual(errors, []);
  report.status = "passed";
  report.passed = ["12 real width/palette/mode OIDC flows", "Named and hidden autostart, themed manual buttons, branded manual button with autostart disabled", "Local sign-in fallback and invalid-state callback errors retain device colors", "Verified nonce/state/RS256 identity exchange, authenticated return path and member authorization", "Account preferences override the cosmetic device cache after sign-in"];
  await writeFile(path.join(evidenceRoot, "oidc-theme-conformance.json"), JSON.stringify(report, null, 2) + "\n");
  console.log(JSON.stringify({ status: report.status, cases: report.cases.length, passed: report.passed }, null, 2));
} finally {
  if (original && members.size) {
    await json(await admin.request.put(origin + "/api/settings/deployment", { data: { oidc_enabled: original.oidc.enabled, oidc_default_login_method: original.oidc.default_login_method, oidc_providers_json: "[]" } }));
    for (const member of members.values()) await json(await admin.request.delete(origin + "/api/auth/users/" + member.id));
  }
  await browser.close(); await new Promise(resolve => frontendServer.close(resolve)); await new Promise(resolve => idp.close(resolve));
}
