// Repro parametrizavel de "duplo envio" em app Expo Web: dispara N eventos
// (pointerdown/pointerup/click) DENTRO DE UM UNICO turno de JS e conta os POSTs.
//
// Por que nao usar Promise.all([botao.click(), botao.click(), botao.click()]):
// cada locator.click() faz round-trip de CDP; entre um e outro o React commita o
// render, o botao ja esta disabled e os cliques seguintes morrem no DOM. Medido:
// devolve 1 POST ate em tela SEM trava de reentrancia => PASS falso.
//
// Standalone: nao depende do harness do projeto (so do Playwright/Chromium que ja
// existem na maquina, no cache do npx e em ms-playwright).
//
// Uso:
//   node repro-mesmo-tick.mjs --url /agenda --botao "^adicionar à agenda" \
//     --post /api/me/agenda/ --campo "^Ex.: Ensaio do Louvor=QA mesmo tick" \
//     --campo "^Início:=2026-12-01T18:00:00-03:00" \
//     --controle-url /schedule-create --controle-botao "adicionar escala" \
//     --controle-post /api/schedules/ --controle-campo "^Culto de celebra=QA" \
//     --controle-campo "^Louvor=QA"
//
//   --base http://localhost:8081   (default)
//   --seed backend/apps/accounts/management/commands/seed_mvp.py  (credenciais)
//   --conta admin|membro|tesouraria|lider  (prefixo do e-mail no seed; default admin)
//   --view 1440x1024 | 390x844     (default 1440x1024)
//
// Exit codes: 0 = defeito reproduzido (alvo > 1 POST e controle <= 1)
//             2 = nao reproduzido   3 = preparo falhou (login/url/botao ausente)
// Nada chega ao banco: os POSTs casados por --post/--controle-post sao respondidos
// com route.fulfill (fica no cliente).
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

// ---------------------------------------------------------------- argv
function arg(nome, padrao) {
  const i = process.argv.indexOf(`--${nome}`);
  return i >= 0 && process.argv[i + 1] ? process.argv[i + 1] : padrao;
}
function argLista(nome) {
  const saida = [];
  process.argv.forEach((v, i) => { if (v === `--${nome}` && process.argv[i + 1]) saida.push(process.argv[i + 1]); });
  return saida;
}
const BASE = arg("base", "http://localhost:8081");
const SEED = arg("seed", "backend/apps/accounts/management/commands/seed_mvp.py");
const CONTA = arg("conta", "admin");
const [LARG, ALT] = arg("view", "1440x1024").split("x").map(Number);
const alvo = {
  rotulo: "ALVO", url: arg("url"), botao: arg("botao", "enviar"), post: arg("post"),
  campos: argLista("campo").map((c) => c.split(/=(.+)/).slice(0, 2)),
};
const controle = {
  rotulo: "CONTROLE", url: arg("controle-url"), botao: arg("controle-botao", ""), post: arg("controle-post", ""),
  campos: argLista("controle-campo").map((c) => c.split(/=(.+)/).slice(0, 2)),
};
if (!alvo.url) { console.error("faltou --url"); process.exit(3); }

// ------------------------------------------- Playwright/Chromium já instalados
function maiorVersao(lista) {
  return lista.sort((a, b) => {
    const pa = String(a.versao).split(".").map(Number); const pb = String(b.versao).split(".").map(Number);
    for (let i = 0; i < 3; i += 1) if ((pa[i] || 0) !== (pb[i] || 0)) return (pb[i] || 0) - (pa[i] || 0);
    return b.rev - a.rev;
  })[0];
}
function resolverPlaywright() {
  if (process.env.PW_ENTRY) return process.env.PW_ENTRY;
  const raizes = [
    path.join(os.homedir(), "AppData", "Local", "npm-cache", "_npx"),
    path.join(os.homedir(), ".npm", "_npx"),
  ].filter((r) => fs.existsSync(r));
  const achados = [];
  for (const raiz of raizes) {
    for (const hash of fs.readdirSync(raiz)) {
      const pkg = path.join(raiz, hash, "node_modules", "playwright", "package.json");
      if (!fs.existsSync(pkg)) continue;
      try { achados.push({ versao: JSON.parse(fs.readFileSync(pkg, "utf8")).version, rev: 0,
        entry: path.join(raiz, hash, "node_modules", "playwright", "index.mjs") }); } catch { /* ignora */ }
    }
  }
  if (!achados.length) throw new Error("playwright nao encontrado no cache do npx; rode `npx playwright --version` ou defina PW_ENTRY");
  return `file:///${maiorVersao(achados).entry.replace(/\\/g, "/")}`;
}
function resolverChrome() {
  if (process.env.PW_CHROME) return process.env.PW_CHROME;
  const raizes = [
    path.join(os.homedir(), "AppData", "Local", "ms-playwright"),
    path.join(os.homedir(), ".cache", "ms-playwright"),
  ].filter((r) => fs.existsSync(r));
  const candidatos = [];
  for (const raiz of raizes) {
    for (const pasta of fs.readdirSync(raiz)) {
      const m = /^chromium-(\d+)$/.exec(pasta);
      if (!m) continue;
      const exe = [path.join(raiz, pasta, "chrome-win64", "chrome.exe"), path.join(raiz, pasta, "chrome-linux", "chrome")]
        .find((p) => fs.existsSync(p));
      if (exe) candidatos.push({ versao: "0.0.0", rev: Number(m[1]), entry: exe });
    }
  }
  return candidatos.length ? maiorVersao(candidatos).entry : undefined;
}
const { chromium } = await import(resolverPlaywright());

// ------------------------------------------------ credenciais do seed (nunca literal)
function credencial(pref) {
  const texto = fs.readFileSync(SEED, "utf8");
  const re = /"([^"@\s]+@[^"\s]+)"[\s\S]{0,1200}?set_password\("([^"]+)"\)/g; // janela importa
  const mapa = {};
  for (const m of texto.matchAll(re)) if (!mapa[m[1]]) mapa[m[1]] = m[2];
  const email = Object.keys(mapa).find((e) => e.startsWith(pref));
  if (!email) throw new Error(`conta "${pref}" nao existe no seed (${Object.keys(mapa).join(", ")})`);
  return { email, password: mapa[email] };
}

// ------------------------------------------------------------------- helpers
async function digitar(page, seletorPlaceholder, valor) {
  const campo = page.getByPlaceholder(new RegExp(seletorPlaceholder, "i")).first(); // fill() NAO muda o estado do React
  await campo.click();
  await campo.fill("");
  await campo.pressSequentially(valor, { delay: 20 });
}
const tresNoMesmoTurno = (page, rotuloRegex) =>
  page.evaluate((alvo) => {
    const el = [...document.querySelectorAll('[role="button"], [role="link"]')]
      .find((e) => new RegExp(alvo, "i").test(e.innerText || e.getAttribute("aria-label") || ""));
    if (!el) return { achou: false, total: 0 };
    for (let i = 0; i < 3; i += 1) {                       // 3 eventos sem soltar o event loop
      el.dispatchEvent(new MouseEvent("pointerdown", { bubbles: true, cancelable: true }));
      el.dispatchEvent(new MouseEvent("pointerup", { bubbles: true, cancelable: true }));
      el.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true }));
    }
    return { achou: true, total: 3 };
  }, rotuloRegex);

async function medir(browser, caso, cred) {
  if (!caso.url) return { erro: "sem --controle-url (sem controle nesta rodada)", posts: 0, achou: false };
  const context = await browser.newContext({ viewport: { width: LARG, height: ALT }, locale: "pt-BR" });
  const page = await context.newPage();
  let posts = 0;
  if (caso.post) {
    await page.route(new RegExp(`${caso.post.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}/?(\\?.*)?$`), async (rota) => {
      if (rota.request().method() !== "POST") return rota.continue();
      posts += 1;
      await rota.fulfill({ status: 201, contentType: "application/json", body: JSON.stringify({ id: 900000 + posts, detail: "ok" }) });
    });
  }
  const erroConsole = [];
  page.on("pageerror", (e) => erroConsole.push(String(e.message || e)));
  await page.goto(`${BASE}/`, { waitUntil: "domcontentloaded", timeout: 45000 });
  await page.waitForTimeout(2500);
  const inputs = page.locator("input");
  if ((await inputs.count()) >= 2) { await inputs.nth(0).fill(cred.email); await inputs.nth(1).fill(cred.password); }
  await page.getByRole("button", { name: /entrar/i }).first().click({ timeout: 10000 });
  await page.waitForTimeout(3000);
  const logado = new URL(page.url()).pathname !== "/";
  await page.goto(`${BASE}${caso.url}`, { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(3000);
  for (const [campo, valor] of caso.campos) await digitar(page, campo, valor);
  const antes = posts;
  const r = await tresNoMesmoTurno(page, caso.botao);
  await page.waitForTimeout(3500);
  const texto = (await page.locator("body").innerText().catch(() => "")).slice(-220).replace(/\n/g, " | ");
  await context.close();
  return { logado, posts: posts - antes, achou: r.achou, erro: erroConsole.join(" ; "), urlFinal: caso.url, texto };
}

const browser = await chromium.launch({ executablePath: resolverChrome(), headless: true });
const cred = credencial(CONTA);
const cont = await medir(browser, controle, cred);
const res = await medir(browser, alvo, cred);
await browser.close();

console.log(`POSTs casados por --post (3 eventos no MESMO turno de JS), base=${BASE}, conta=${CONTA}`);
for (const [nome, r] of [[controle.rotulo, cont], [alvo.rotulo, res]]) {
  console.log(`  ${nome.padEnd(9)} url=${r.urlFinal || "-"} botao_encontrado=${r.achou} POSTs=${r.posts} login=${r.logado}${r.erro ? ` pageerror=${r.erro}` : ""}`);
  if (r.texto) console.log(`            tela: ${r.texto}`);
}
if (!res.achou || !res.logado) { console.log("PREPARO FALHOU (url, botao ou login)"); process.exit(3); }
if (res.posts > 1 && (cont.posts <= 1 || !controle.url)) { console.log("DEFEITO REPRODUZIDO"); process.exit(0); }
console.log(cont.posts > 1 ? "CONTROLE TAMBEM DUPLICOU: metodo suspeito, revise o estimulo" : "NAO REPRODUZIDO (1 POST)");
process.exit(2);
