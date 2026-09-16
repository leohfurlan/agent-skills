---
name: expo-web-qa
description: QA exploratório automatizado de apps Expo/React Native rodando na web (localhost:8081) com Playwright — varredura de rotas × papéis × viewports, fluxos de escrita com captura de rede, screenshots e comparação por texto contra um mockup/design (Pen.dev .pen ou similar). Use quando precisar descobrir o que está implementado num app Expo Web, achar telas quebradas (403 silencioso, rota inexistente, HTML de erro do backend dentro da UI) ou produzir relatório de paridade app × mockup com evidência real.
---

# QA de app Expo Web com Playwright

Objetivo: produzir evidência verificável (rede, texto renderizado, screenshot) sobre um app Expo/React Native Web, sem depender de olhar a tela e sem instalar nada além do que já existe na máquina.

## Quando usar

- "O que está implementado / o que falta / o que está quebrado" em um app Expo Web.
- Comparar app × mockup (`.pen` do Pen.dev, Figma export, protótipo) tela a tela.
- Caçar fluxos que falham silenciosamente (botão que não faz nada, erro engolido, permissão negada sem aviso).

## Pré-requisitos e reconhecimento (passo 0)

```bash
# Expo web no ar + porta real (o log do dev server diz a porta)
curl -s -o /dev/null -w "HTTP %{http_code}\n" http://localhost:8081/
# API usada pelo app: NÃO presuma localhost — leia a env/base do cliente
grep -n "API_URL\|EXPO_PUBLIC" mobile/src/services/api.ts
# backend de verdade pode estar em Docker (IP da LAN, ex.: http://192.168.x.x:8000)
docker ps --format "{{.Names}} | {{.Ports}}"
```

Descubra também **como o layout muda**: `Platform.OS === "web" && width >= 900` é o padrão comum para "modo desktop" (sidebar) vs mobile (tab bar). Isso define os dois viewports de teste (ex.: 1440x1024 e 390x844).

## Passo 1 — Playwright sem instalar nada

Os browsers já costumam existir em `~/AppData/Local/ms-playwright` e o pacote `playwright` no cache do npx (`~/.npm-cache/_npx/<hash>/node_modules/playwright`).

```bash
ls "C:/Users/<user>/AppData/Local/ms-playwright"            # chromium-XXXX, chromium_headless_shell-XXXX
find "C:/Users/<user>/AppData/Local/npm-cache/_npx" -maxdepth 3 -name playwright -type d
python -c "import json;print(json.load(open(r'.../playwright/package.json'))['version'])"
```

Armadilhas confirmadas:
- `NODE_PATH` **não funciona** para ESM. Importe por URL absoluta:
  ```js
  const { chromium } = await import('file:///C:/Users/<user>/AppData/Local/npm-cache/_npx/<hash>/node_modules/playwright/index.mjs');
  ```
- `mklink /J node_modules/playwright <destino>` falha com caminho relativo no MSYS; e `rm -rf` é bloqueado — use `find dir -delete` / `rm -f`.
- A revisão de chromium do cache precisa casar com a versão do pacote. Se não casar, passe o executável:
  ```js
  chromium.launch({ executablePath: 'C:/Users/<user>/AppData/Local/ms-playwright/chromium-1228/chrome-win64/chrome.exe', headless: true })
  ```
- Escolha a **maior** versão de playwright disponível (1.63 funcionou com chromium-1228; 1.64 pedia revision inexistente).

## Passo 2 — Credenciais sem literal no script

Nunca copie senha/telefone do output de ferramenta (no Windows/Hermes sequências de dígitos vêm mascaradas). Extraia do próprio seed:

```js
const seed = fs.readFileSync('backend/apps/<app>/management/commands/seed_mvp.py', 'utf8');
const creds = {};
for (const m of seed.matchAll(/"([^"@\s]+@[^"\s]+)"[\s\S]{0,1200}?set_password\("([^"]+)"\)/g)) if (!creds[m[1]]) creds[m[1]] = m[2];
```

A janela do regex (`{0,1200}`) importa: o e-mail do admin costuma estar bem acima do `set_password`.

## Passo 3 — Login programático

```js
await page.goto(BASE + '/'); await page.waitForTimeout(2500);
await page.locator('input').nth(0).fill(email);
await page.locator('input').nth(1).fill(creds[email]);
await page.getByRole('button', { name: 'Entrar' }).first().click();
await page.waitForTimeout(2500);
```

Se a tela de login já vem preenchida com o usuário demo, dá para só clicar em Entrar (útil para a primeira sessão).

## Passo 4 — Varredura (rota × papel × viewport)

Para cada papel (membro, admin, tesouraria, líder — muitos apps derivam coisas de papel), novo `browser.newContext({ viewport })` (contexto novo = sessão limpa) e, por rota:

- `page.on('console')` + `page.on('pageerror')` → guarde só `error`/`warning`;
- `page.on('response', r => r.status() >= 400 && ...)` → status + url;
- `await page.locator('body').innerText()` → **o texto renderizado é a evidência principal** (mais confiável que screenshot para relatório e para diff);
- screenshot por rota em `output/qa/shots/<viewport>-<papel>-<rota>.png`.

Um template pronto está em `templates/qa-sweep.mjs` — copie e ajuste as rotas.

Sinais de que a varredura achou ouro:
- rota com 80–100 bytes de texto → tela de "Unmatched Route" do Expo (não existe `+not-found.tsx`);
- resposta 4xx com corpo HTML do Django → erro do backend renderizado dentro do app (vaza stack trace);
- mesmo texto em rotas diferentes → item de menu apontando para a tela errada;
- `document.querySelectorAll('input').length === 0` numa tela com campo de busca desenhado → campo decorativo.

## Passo 5 — Fluxos de escrita (o que realmente importa)

Instrumentação que funcionou (e a que engana):

```js
const net = [];
page.on('request',  r => { if (r.method() !== 'GET') net.push({ url: r.url(), m: r.method(), post: (r.postData() || '').slice(0,200) }); });
page.on('response', r => { if (r.request().method() !== 'GET') { const e = net.find(x => x.url === r.url() && !x.s); if (e) e.s = r.status(); } });
page.on('dialog',   async d => { dialogs.push({ type: d.type(), msg: d.message() }); await d.dismiss(); });
```

- **Limpe `net` imediatamente antes do clique** e leia depois; registre request e response separadamente (casar só por `status >= 400` perde os 201 e faz você concluir que o clique não funcionou).
- Prefira locators por papel: `page.getByRole('button', { name: 'Enviar' })` ou `page.locator('[role="button"]').filter({ hasText: /^Enviar$/ })`. `getByText('...').first()` frequentemente acerta o **título da página** em vez do botão, e você conclui "o botão não funciona" quando o clique nem chegou nele.
- Antes de concluir que um botão não responde, liste os candidatos: `page.locator('[role="button"]').evaluateAll(els => els.map(e => ({txt:e.innerText.slice(0,40), disabled:e.getAttribute('aria-disabled'), pe:getComputedStyle(e).pointerEvents})))`.

### Armadilha nº 1 (a que mais custa tempo)

`locator.fill('texto')` **não atualiza o estado do React** em `TextInput` do React Native Web: o valor aparece no DOM, mas o `useState` continua vazio, o guard `if (!title.trim())` dispara e nada é enviado.

```js
await campo.click();
await campo.pressSequentially('Ensaio QA', { delay: 25 });   // ✅ funciona
// await campo.fill('Ensaio QA');                             // ❌ estado React não muda
```

Confirme o estado depois de digitar: `page.locator('input').evaluateAll(els => els.map(e => ({ph:e.placeholder, v:e.value})))` — se o valor sumir no próximo render, o React não recebeu.

### Armadilha nº 2 — `Alert.alert` é no-op no web

`react-native-web/dist/exports/Alert/index.js` é um stub vazio (`static alert() {}`). Resultado: **todo** erro/sucesso/validação do app desaparece no desktop, e navegação colocada em `onPress` de botão de Alert (`[{text:'OK', onPress: () => router.replace('/x')}]`) **nunca executa**. Diagnostique assim:

```bash
grep -rn "Alert.alert(" mobile/src | sed -n '1,40p'          # mapa de pontos de falha silenciosa
cat mobile/node_modules/react-native-web/dist/exports/Alert/index.js
```

Ao escrever o relatório, trate isso como um defeito de classe (não "não vi a mensagem"): o comportamento **difere entre web e nativo**, e por isso a demo no desktop engana.

### Armadilha nº 3 — não deixe lixo no banco

Fluxos de escrita criam dados reais. Anote IDs/títulos usados nos testes e apague no final, identificando por marcador próprio (título/observação/attachment com nome do arquivo de teste):

```bash
docker exec <container-backend> python manage.py shell -c "
from apps.events.models import Event
print(Event.objects.filter(name__in=['QA teste hermes']).delete())"
```

Confirme que os dados de seed permaneceram (conte os registros antes e depois).

## Passo 6 — Comparar com o mockup sem depender de visão

Se `vision_analyze` estiver indisponível (chave inválida é erro comum), compare **texto**, que é mais acionável:

1. Extraia os textos literais do mockup. `.pen` (Pen.dev/Pencil) é JSON: `doc['children']` → frames (`type: "frame"`), e nós `type: "text"` com `content`.
2. Normalize os dois lados e faça diff de presença:
   ```python
   def norm(s):  # sem acento, sem caixa, sem espaço duplo
       s = unicodedata.normalize("NFKD", s or "")
       s = "".join(c for c in s if not unicodedata.combining(c))
       return re.sub(r"\s+", " ", s).strip().lower()
   faltando = [t for t in textos_mockup if norm(t) not in norm(texto_renderizado_app)]
   ```
3. Reporte `presentes/total` por tela — é um proxy honesto de paridade (diga isso no relatório) e expõe divergência de **dados** (mockup "Igreja X" vs seed "Igreja Y") que a comparação visual esconderia.
4. Para telas que exigem navegação (ex.: detalhe aberto por clique), capture o texto **depois** de navegar de verdade dentro do app — uma URL direta pode cair em outro estado (link sem parâmetro obrigatório, por exemplo).

## Passo 7 — Higiene do relatório

- Todo achado com `arquivo:linha` ou resultado de execução (status HTTP, texto, caminho de screenshot). Sem "parece que".
- Separe: **implementado e funcionando** (com a evidência da execução) / **implementado e quebrado** (com repro numerada) / **pendente** (tela a tela, com % de cobertura).
- Fixture de dados: confirme contagem no banco após a limpeza e diga o que foi removido.
- Nunca afirme "não encontrado" a partir de busca em histórico: o app rodando é a fonte de verdade.