#!/usr/bin/env node
// Skeleton de VERIFICADOR DE ACEITE por fase (QA exploratorio -> criterio do plano).
//
// Rode a partir da raiz do repo:  node tools/qa/run.mjs fase1
// Um arquivo unico de propósito: quando cada check já é um critério escrito, você
// não precisa de framework — precisa de evidência reprodutível e código de saída.
//
// Estrutura que escala melhor (usada num repo real):
//   tools/qa/run.mjs           runner (este arquivo, na versão final)
//   tools/qa/lib/pw.mjs        resolve Playwright/Chromium sem instalar nada
//   tools/qa/lib/harness.mjs   sessão instrumentada + login + digitar/esperarPor
//   tools/qa/lib/accounts.mjs  credenciais extraídas do seed (nunca literais)
//   tools/qa/lib/report.mjs    acumulador PASS/FAIL + resultados.json + resumo.md
//   tools/qa/checks/faseN.mjs  um arquivo por fase, checks nomeados pelo critério
//   docs/qa/evidencias/<fase>-<carimbo>/  resultados.json, resumo.md, shots/*.png
import fs from "node:fs";
import path from "node:path";

const BASE = process.env.QA_BASE || "http://localhost:8081";
const VIEWPORT_DESKTOP = { width: 1440, height: 1024 };
const VIEWPORT_MOBILE = { width: 390, height: 844 };

async function carregarChromium() {
  const cache = path.join(process.env.LOCALAPPDATA || process.env.HOME || "", "ms-playwright");
  const viaNpx = [
    path.join(process.env.APPDATA || "", "npm-cache", "_npx"),
    path.join(process.env.HOME || "", ".npm", "_npx"),
  ].filter((dir) => dir && fs.existsSync(dir));
  const candidatos = viaNpx.flatMap((dir) =>
    fs.readdirSync(dir).map((hash) => path.join(dir, hash, "node_modules", "playwright", "index.mjs")),
  ).filter((arquivo) => fs.existsSync(arquivo));
  if (!candidatos.length) throw new Error("playwright nao encontrado (npx cache); instale ou defina PW_ENTRY");
  // ESM não respeita NODE_PATH: importe por URL absoluta.
  const { chromium } = await import(`file://${candidatos[0].replace(/\\/g, "/")}`);
  const revisoes = fs.existsSync(cache)
    ? fs.readdirSync(cache).filter((nome) => nome.startsWith("chromium-")).sort().pop()
    : null;
  const executavel = revisoes ? path.join(cache, revisoes, "chrome-win64", "chrome.exe") : undefined;
  return chromium.launch({ headless: true, ...(executavel && fs.existsSync(executavel) ? { executablePath: executavel } : {}) });
}

/** Sessão instrumentada: console, pageerror, HTTP >= 400, dialogs e escritas. */
async function novaSessao(browser, { viewport = VIEWPORT_DESKTOP, mobile = false } = {}) {
  const context = await browser.newContext({ viewport, mobile, hasTouch: mobile, locale: "pt-BR" });
  const page = await context.newPage();
  const estado = { page, context, console: [], pageerrors: [], http: [], dialogs: [], escritas: [], limpar: () => {} };
  page.on("console", (msg) => {
    if (["error", "warning"].includes(msg.type())) estado.console.push({ tipo: msg.type(), texto: msg.text() });
  });
  page.on("pageerror", (erro) => estado.pageerrors.push(String(erro.message || erro)));
  page.on("dialog", async (dialog) => {
    estado.dialogs.push({ tipo: dialog.type(), msg: dialog.message() });
    await dialog.dismiss().catch(() => {});
  });
  page.on("response", (resposta) => {
    if (resposta.status() >= 400) estado.http.push({ status: resposta.status(), url: resposta.url() });
  });
  page.on("request", (requisicao) => {
    if (requisicao.method() === "GET") return;
    const registro = { metodo: requisicao.method(), url: requisicao.url(), corpo: (requisicao.postData() || "").slice(0, 300), status: null };
    estado.escritas.push(registro);
    requisicao.response().then((r) => { if (r) registro.status = r.status(); }).catch(() => {});
  });
  estado.limpar = () => {
    for (const chave of ["console", "pageerrors", "http", "dialogs", "escritas"]) estado[chave].length = 0;
  };
  return estado;
}

/** `fill()` NÃO atualiza o estado do React no RN Web: digite de verdade. */
async function digitar(locator, valor) {
  await locator.click();
  await locator.fill("");
  await locator.pressSequentially(valor, { delay: 20 });
}

async function esperarPor(fn, { timeout = 8000, intervalo = 250 } = {}) {
  const limite = Date.now() + timeout;
  for (;;) {
    if (await fn().catch(() => false)) return true;
    if (Date.now() > limite) return false;
    await new Promise((r) => setTimeout(r, intervalo));
  }
}

const texto = async (page, limite = 6000) => (await page.locator("body").innerText().catch(() => "")).slice(0, limite);
const normalizar = (valor) => String(valor || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
const contem = (onde, trecho) => normalizar(onde).includes(normalizar(trecho));
const caminho = (url) => { try { return new URL(url).pathname; } catch { return ""; } };

class Verificacao {
  constructor(nome, dir) {
    this.nome = nome;
    this.dir = dir || path.join("output", "qa", `${nome}-${Date.now()}`);
    this.shots = path.join(this.dir, "shots");
    fs.mkdirSync(this.shots, { recursive: true });
    this.itens = [];
    this.comecou = new Date();
  }
  check(nome, ok, detalhe = "") {
    const item = { nome, resultado: ok ? "PASS" : "FAIL", detalhe: String(detalhe ?? "") };
    this.itens.push(item);
    console.log(`[${ok ? "PASS " : "FAIL "}] ${nome}${item.detalhe ? ` — ${item.detalhe}` : ""}`);
    return ok;
  }
  aviso(nome, detalhe = "") { this.itens.push({ nome, resultado: "AVISO", detalhe }); console.log(`[AVISO] ${nome} — ${detalhe}`); }
  get passes() { return this.itens.filter((i) => i.resultado === "PASS"); }
  get falhas() { return this.itens.filter((i) => i.resultado === "FAIL"); }
  async screenshot(page, nome) {
    const arquivo = path.join(this.shots, `${nome.replace(/[^\w.-]+/g, "_")}.png`);
    await page.screenshot({ path: arquivo, fullPage: false }).catch(() => {});
    return arquivo;
  }
  salvar(meta = {}) {
    const dados = { nome: this.nome, inicio: this.comecou.toISOString(), base_url: meta.base, itens: this.itens, meta };
    fs.writeFileSync(path.join(this.dir, "resultados.json"), `${JSON.stringify(dados, null, 2)}\n`, "utf8");
    const md = [
      `# Verificacao ${this.nome}`, "",
      `- Base URL: ${meta.base || "-"}`,
      `- PASS: ${this.passes.length} | FAIL: ${this.falhas.length}`, "",
      "| Resultado | Check | Detalhe |", "|---|---|---|",
      ...this.itens.map((i) => `| ${i.resultado} | ${i.nome} | ${i.detalhe.replace(/\n/g, " ")} |`), "",
    ].join("\n");
    fs.writeFileSync(path.join(this.dir, "resumo.md"), md, "utf8");
    return this.dir;
  }
}

// ---------------------------------------------------------------------------
// Uma fase = uma função. Nomeie cada check com o critério do plano (verbatim).
async function fase1(browser, dir) {
  const v = new Verificacao("fase-1", dir);

  // 1. Aviso visível em vez de Alert nativo (Alert.alert é no-op no RN Web).
  {
    const sessao = await novaSessao(browser);
    await sessao.page.goto(`${BASE}/`, { waitUntil: "domcontentloaded" });
    await sessao.page.waitForTimeout(2500);
    const inputs = sessao.page.locator("input");
    await digitar(inputs.nth(0), "conta.inexistente@exemplo.com");
    await digitar(inputs.nth(1), "senha-errada-de-proposito");
    await sessao.page.getByRole("button", { name: /entrar/i }).first().click();
    const mostrou = await esperarPor(async () => contem(await texto(sessao.page), "senha incorretos") || (await sessao.page.getByRole("alert").count()) > 0);
    v.check("1. Login inválido mostra erro visível na tela", mostrou, mostrou ? "mensagem exibida" : "nada apareceu");
    v.check("1b. Nenhum dialog nativo disparado", sessao.dialogs.length === 0, `${sessao.dialogs.length} dialog(s)`);
    await v.screenshot(sessao.page, "1-login-invalido");
    await sessao.context.close();
  }

  // 2. Erro de backend em HTML nunca chega na UI (rota forçada, determinístico).
  {
    const sessao = await novaSessao(browser);
    await sessao.page.route("**/api/**", (rota) =>
      rota.fulfill({ status: 500, contentType: "text/html", body: "<html><body><h1>Server Error (500)</h1></body></html>" }),
    );
    await sessao.page.goto(`${BASE}/home`, { waitUntil: "domcontentloaded" });
    await sessao.page.waitForTimeout(3000);
    const conteudo = await texto(sessao.page);
    const vazou = contem(conteudo, "server error") || contem(conteudo, "traceback");
    v.check("2. HTML de erro do backend não aparece para o usuário", !vazou, vazou ? "HTML vazou para a tela" : "tela sem HTML");
    await v.screenshot(sessao.page, "2-erro-500");
    await sessao.context.close();
  }

  // 3. Escrita duplicada: capture POSTs, não o "parece que enviou".
  {
    const sessao = await novaSessao(browser);
    await sessao.page.goto(`${BASE}/home`, { waitUntil: "domcontentloaded" });
    await sessao.page.waitForTimeout(2000);
    if (sessao.console.length) v.aviso("console com avisos", sessao.console.map((c) => c.texto).slice(0, 3).join(" / "));
    const posts = sessao.escritas.filter((item) => item.metodo === "POST");
    v.check("3. Nenhuma escrita involuntária ao abrir a tela", posts.length === 0, `${posts.length} POST(s)`);
    await sessao.context.close();
  }
  return v;
}

const FASES = { fase1 };

async function principal() {
  const alvo = (process.argv[2] || "fase1").toLowerCase();
  const pedidas = alvo === "todas" ? Object.keys(FASES) : [alvo];
  if (!pedidas.every((nome) => FASES[nome])) {
    console.error(`fase desconhecida. Use: ${Object.keys(FASES).join(", ")}, todas`);
    process.exit(2);
  }
  try {
    await fetch(BASE, { signal: AbortSignal.timeout(8000) });
  } catch {
    console.error(`app não respondeu em ${BASE} (QA_BASE para apontar noutro host)`);
    process.exit(3);
  }
  const browser = await carregarChromium();
  let falhas = 0;
  for (const nome of pedidas) {
    const dir = path.join("docs", "qa", "evidencias", `${nome}-${new Date().toISOString().replace(/[:.]/g, "").slice(0, 15)}`);
    const verificacao = await FASES[nome](browser, dir);
    console.log(`evidência: ${verificacao.salvar({ base: BASE, comando: `node tools/qa/run.mjs ${alvo}` })}`);
    falhas += verificacao.falhas.length;
  }
  await browser.close();
  console.log(`=== ${falhas === 0 ? "TUDO PASSOU" : `${falhas} FALHA(S)`} ===`);
  process.exit(falhas === 0 ? 0 : 1);
}

principal().catch((erro) => { console.error(erro); process.exit(1); });
