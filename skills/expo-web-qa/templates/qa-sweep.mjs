// Template de varredura: rotas x papéis x viewports num app Expo Web.
// Rode com:  PW_ENTRY=<...>/playwright/index.mjs  PW_CHROME=<...>/chrome.exe  node qa-sweep.mjs
// Ajuste: BASE, OUT, SEED, ROUTES, ACCOUNTS.

const PW = process.env.PW_ENTRY;                       // file:///C:/.../node_modules/playwright/index.mjs
const { chromium } = await import(PW);
import fs from 'fs';

const BASE = 'http://localhost:8081';
const OUT = 'output/qa';
const SEED = 'backend/apps/accounts/management/commands/seed_mvp.py';
fs.mkdirSync(OUT + '/shots', { recursive: true });

// credenciais extraídas do seed (nunca literais no script)
const seedTxt = fs.readFileSync(SEED, 'utf8');
const creds = {};
for (const m of seedTxt.matchAll(/"([^"@\s]+@[^"\s]+)"[\s\S]{0,1200}?set_password\("([^"]+)"\)/g)) if (!creds[m[1]]) creds[m[1]] = m[2];
const emailOf = (prefixo) => Object.keys(creds).find((e) => e.startsWith(prefixo));

const ACCOUNTS = [
  ['membro', emailOf('membro')],
  ['admin', emailOf('admin')],
  ['tesouraria', emailOf('tesouraria')],
  ['lider', emailOf('lider')],
];
const ROUTES = ['home', 'profile', 'statement', 'contribution', 'agenda', 'schedules', 'schedule/1', 'song/1', 'notifications', 'schedule-create', 'rota-inexistente'];
const VIEWPORTS = [
  ['desktop', { width: 1440, height: 1024 }],
  ['mobile', { width: 390, height: 844, isMobile: true, hasTouch: true }],
];

const report = [];
const browser = await chromium.launch({ executablePath: process.env.PW_CHROME || undefined, headless: true });

async function login(page, email) {
  await page.goto(BASE + '/', { waitUntil: 'load' });
  await page.waitForTimeout(2500);
  const inputs = page.locator('input');
  await inputs.nth(0).fill(email);            // .fill() serve para o LOGIN (estado inicial da tela)
  await inputs.nth(1).fill(creds[email]);
  await page.getByRole('button', { name: 'Entrar' }).first().click();
  await page.waitForTimeout(2500);
}

for (const [vpName, vp] of VIEWPORTS) {
  for (const [roleName, email] of ACCOUNTS) {
    if (!email) continue;
    if (vpName === 'mobile' && roleName !== 'membro') continue;   // economize: mobile só no papel principal
    const ctx = await browser.newContext({ viewport: vp, deviceScaleFactor: 1 });
    const page = await ctx.newPage();
    const consoleIssues = [], httpErrors = [], dialogs = [];
    page.on('console', (m) => { if (m.type() === 'error' || m.type() === 'warning') consoleIssues.push(m.type() + ': ' + m.text().slice(0, 200)); });
    page.on('pageerror', (e) => consoleIssues.push('pageerror: ' + String(e).slice(0, 200)));
    page.on('dialog', async (d) => { dialogs.push({ type: d.type(), msg: d.message() }); await d.dismiss(); });
    page.on('response', (r) => { if (r.status() >= 400) httpErrors.push({ status: r.status(), url: r.url(), method: r.request().method() }); });

    const entry = { viewport: vpName, account: roleName, dialogs, consoleIssues, httpErrors, screens: [] };
    try {
      await login(page, email);
      entry.login = page.url();
      for (const route of ROUTES) {
        const before = httpErrors.length;
        await page.goto(`${BASE}/${route}`, { waitUntil: 'load' });
        await page.waitForTimeout(1800);
        const shot = `${OUT}/shots/${vpName}-${roleName}-${route.replace(/\//g, '_')}.png`;
        await page.screenshot({ path: shot, fullPage: true }).catch(() => {});
        entry.screens.push({
          route, url: page.url(), shot,
          text: (await page.locator('body').innerText()).slice(0, 4000),
          scrollH: await page.evaluate(() => document.documentElement.scrollHeight),
          httpErrors: httpErrors.slice(before),
        });
      }
    } catch (err) {
      entry.erro = String(err).slice(0, 400);
    }
    report.push(entry);
    fs.writeFileSync(`${OUT}/qa-sweep.json`, JSON.stringify(report, null, 1));
    await ctx.close();
    console.log('ok', vpName, roleName);
  }
}
await browser.close();
console.log('relatório:', `${OUT}/qa-sweep.json`, '| telas:', report.reduce((n, r) => n + r.screens.length, 0));
