---
name: expo-web-qa
related_skills: [dogfood]
description: QA exploratório automatizado de apps Expo/React Native rodando na web (localhost:8081) com Playwright — varredura de rotas × papéis × viewports, fluxos de escrita com captura de rede, screenshots e comparação por texto contra um mockup/design (Pen.dev .pen ou similar). Use quando precisar descobrir o que está implementado num app Expo Web, achar telas quebradas (403 silencioso, rota inexistente, HTML de erro do backend dentro da UI) ou produzir relatório de paridade app × mockup com evidência real.
---

# QA de app Expo Web com Playwright

Objetivo: produzir evidência verificável (rede, texto renderizado, screenshot) sobre um app Expo/React Native Web, sem depender de olhar a tela e sem instalar nada além do que já existe na máquina.

## Quando usar

- "O que está implementado / o que falta / o que está quebrado" em um app Expo Web.
- Comparar app × mockup (`.pen` do Pen.dev, Figma export, protótipo) tela a tela.
- Caçar fluxos que falham silenciosamente (botão que não faz nada, erro engolido, permissão negada sem aviso).

## Pré-requisitos e reconhecimento (passo 0)

**Descubra a base da API separadamente da base do app** — quase sempre são hosts/portas diferentes, e `API_URL` no cliente pode apontar para o IP da LAN (não `localhost`):

```bash
grep -n "API_URL\|EXPO_PUBLIC" mobile/src/services/api.ts
curl -s -o /dev/null -w "app=%{http_code}\n" http://localhost:8081
curl -s -o /dev/null -w "api=%{http_code}\n" http://localhost:8000/api/schema/
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
- `mklink /J node_modules/playwright <destino>` falha com caminho relativo no MSYS.
- **Limpeza**: `rm -rf` — e `find <dir> -exec rm -rf {} +` — são **negados** neste ambiente, e a negativa **aborta a linha inteira**, inclusive a parte inofensiva que vinha depois. `rm -rf tmp/node_modules && node script.mjs` faz você concluir "o script não rodou" quando na verdade nada rodou. Nunca encadeie limpeza com comando produtivo: rode o produtivo sozinho, e a limpeza em chamada separada com `rm -f` de caminhos explícitos. Se a limpeza é cosmética (`__pycache__`, `node_modules`) e for negada, **siga em frente e diga que não limpou** — não repita nem reformule o comando negado.
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
4. Antes de comparar, **delegue os inventários em paralelo** (mockup e backend): cada subagente lê a fonte pesada e grava um `.md` em `output/`, devolvendo só um resumo curto. Um `.pen` com 49 telas vira 800 KB de markdown — não traga isso para o seu contexto.
5. Para telas que exigem navegação (ex.: detalhe aberto por clique), capture o texto **depois** de navegar de verdade dentro do app — uma URL direta pode cair em outro estado (link sem parâmetro obrigatório, por exemplo).
   ⚠️ Se a captura por URL direta caiu em erro/estado diferente, **a contagem dessa tela vira lixo** (0 presentes) e contamina o agregado. Recapture por navegação real e recalcule antes de publicar o número — foi exatamente assim que uma cobertura de 41,5 % foi publicada como 37,3 %.
6. **Paridade de design system (tokens)** rende mais que opinião visual — é o item que separa "faltam telas" de "o visual está errado". Extraia a tabela de tokens do mockup (`doc['variables']` / doc de tokens) e compare os hex com o `theme.ts` do app **nos dois sentidos** (o que falta e o que o app acrescenta):
   ```python
   tokens = re.findall(r"^\| `([a-zA-Z]+)` \| (color|string) \| `([^`]+)` \|", open("mockup-tokens.md").read(), re.M)
   cores = [(n, v) for n, t, v in tokens if t == "color"]
   presentes = [n for n, v in cores if v.upper() in open("mobile/src/theme.ts").read().upper()]
   print(len(presentes), "/", len(cores), "ausentes:", [n for n, _ in cores if n not in presentes])
   ```
   Caso real: 14/15 cores idênticas (só `blueSoft` ausente), fonte declarada (`Inter`) nunca aplicada, app com 9 tons extras — conclusão que muda o relatório ("o gargalo é cobertura de telas e veracidade dos dados, não linguagem visual"). Sem essa checagem, o documento sugere redesenhar o que já está alinhado.

## Passo 7 — Higiene do relatório

- Todo achado com `arquivo:linha` ou resultado de execução (status HTTP, texto, caminho de screenshot). Sem "parece que".
- Separe: **implementado e funcionando** (com a evidência da execução) / **implementado e quebrado** (com repro numerada) / **pendente** (tela a tela, com % de cobertura).
- Fixture de dados: confirme contagem no banco após a limpeza e diga o que foi removido.
- Nunca afirme "não encontrado" a partir de busca em histórico: o app rodando é a fonte de verdade.

## Passo 8 — Verifique o relatório ANTES de entregar (obrigatório)

Todo número que você escreveu saiu de uma contagem sua, provavelmente em um comando de terminal lido de raspão. Antes de entregar, **re-derive cada afirmação quantitativa da fonte e compare com o texto do documento** — em um caso real, 4 de ~10 números estavam errados, incluindo a manchete de cobertura.

Receita: escreva um script temporário (prefixo `hermes-verify-` em `%TEMP%`), com pares `check(nome, condição, detalhe)` acumulando PASS/FAIL e `sys.exit(1)` se houver falha; um esqueleto pronto está em `templates/verificar-afirmacoes.py`. Depois:

1. Rode-o, **corrija o documento** para bater com o recalculado e rode de novo até passar.
2. Preserve o script como evidência no diretório de saída (`output/.../verificar-relatorio.py`) e apague a cópia do temp.
3. Diga explicitamente ao usuário **quais números você corrigiu** — relatório com auto-correção declarada vale mais que relatório "limpo" e silencioso.
4. Rótulo honesto: se a suíte de testes do projeto rodou, é "suíte verde"; o resto é **verificação ad-hoc**, não suíte.

Quando o que você audita são docs de plano/baseline/paridade que citam `arquivo:linha` (não só números do relatório), acrescente a **auditoria de citações**: esqueleto e armadilhas (cerca de código com número ímpar de cercas, contexto de proposta, citação obsoleta mas dentro dos limites, ORM em vez de grep) em `harness-atos-sdd` — `templates/verificar-citacoes-docs.py` e `references/adhoc-doc-verification.md`. Num caso real ela pegou 3 erros de conteúdo num conjunto de 6 docs, incluindo duas seções que contradiziam o próprio errata.

O que re-derivar (e as armadilhas de contagem que já produziram erro):

- **Contagens de tela/rota/tela**: conte por extensão de arquivo, não por `find | grep` de cabeça. "15 arquivos de rota" era 13 (`globs` duplicando padrões); declare se `_layout` entra na conta.
- **Chamadas de função / ocorrências de padrão**: `re.findall(r'Alert\.alert\(')` em todos os arquivos → 14, não 21. Sempre a contagem do parser, nunca a de memória.
- **Linhas de código**: `wc -l` conta quebras de linha; `sum(1 for _ in open(f))` conta uma linha a mais por arquivo. Fixe a convenção no script (`read().count("\n")`) para os dois lados baterem.
- **Percentuais de paridade**: recalcule com a mesma função de normalização usada na análise e com as capturas corretas (ver Passo 6.5). Arredonde e afirme o par `presentes/total`, não só o percentual.
- **Endpoints/N: derive do artefato vivo** (`GET /api/schema/` e conte pares método+path), não do resumo que você escreveu antes.
- **Suíte de testes**: rode-a de verdade e cite a linha final (`67 passed`). Se o container não tem pytest, rode no host (`cd backend && python -m pytest -q`) — o "não tem pytest" é do container, não um defeito do projeto.
- **Estado do banco após limpeza**: consultar o ORM e checar um marcador próprio (`LIMPO` vs `QA-ARTIFACT`), comparando com a contagem de seed.
- **Integridade do markdown**: cercas de código balanceadas, tabelas com número de colunas consistente, ausência de marcadores de truncamento (`[truncated]`, `!!`) — lixo de edição passa fácil.
- **Espelhamento de skill/arquivo**: SHA-256 das duas cópias (instalada e repositório) iguais.
- **Frescor da evidência**: compare o *mtime* do artefato (`resultados.json`) com o do arquivo de código de mtime mais alto entre os fontes tocados. Existir evidência não é o mesmo que ela cobrir a última edição — é a diferença entre "rodei" e "rodei depois da última mudança". Vale como check automático no verificador.
- **Assertiva de fonte (grep) mente por comentário e por chave de estilo**: `"248" not in fonte` falha porque o próprio docstring cita o valor removido; `"sidebarGroups" not in fonte` falha porque a chave de `StyleSheet` tem esse nome. Nas duas vezes o bug era do **verificador**, não do código. Regras: assertiva de invariante roda sobre o código **sem comentários** (remova `/* */` e linhas iniciando com `//` ou `*`) e mira **declarações** (`const sidebarGroups`), nunca qualquer ocorrência; padrão em regex de detecção (`/text\/html/i` não contém o literal `text/html`) exige assertiva por regex, não por substring.
- **FAIL de verificador ad-hoc é hipótese, não veredito**: antes de "corrigir o código", vá à fonte (`grep -n` do trecho, leitura da linha). Só então decida se é defeito do código ou do checker. Um verificador ajustado até ficar verde sem investigação é teatro — e o relato honesto ("4 FAILs eram falsos positivos do checker; corrigido e re-rodado") vale mais que um 29/29 silencioso.

Se alguma checagem depende de serviço indisponível (API fora, schema inacessível), registre como **aviso** com o motivo — nunca como passa.

### Quando o harness avisa "verification stale / unverified"

O aviso costuma vir acompanhado de uma saída **antiga** (a última que ele capturou, não a última que você rodou). Não discuta com o aviso nem assuma que o trabalho regrediu: **rode de novo e mostre a saída nova**.

```bash
cp output/<area>/verificar-relatorio.py "$TEMP/hermes-verify-<assunto>.py"      # cópia temporária com o prefixo exigido
python "$TEMP/hermes-verify-<assunto>.py" > "$TEMP/hermes-verify-saida.txt" 2>&1; echo "exit=$?"
grep -E '^=== (PASS|FAIL)|^RESULTADO' "$TEMP/hermes-verify-saida.txt"
```

Depois, em **comando separado** (ver a armadilha de `rm -rf` no Passo 1):

```bash
rm -f "$TEMP/hermes-verify-<assunto>.py" "$TEMP/hermes-verify-saida.txt"
```

- Não reescreva o verificador para a nova rodada: ele **é** o artefato versionado no repo — a cópia temporária existe só para satisfazer o protocolo do harness.
- O aviso também dispara quando quem editou foi OUTRO escritor (subagente da própria sessão, agente paralelo no mesmo working tree). Nesse caso verifique a superfície que mudou — `npx tsc --noEmit` para o app, `python -m pytest -q` para o backend — e diga no relatório qual evidência cobre qual superfície, em vez de re-rodar a mesma suíte e chamar isso de cobertura do que o outro mexeu.
- Trabalho não commitado num repo com escritor paralelo pode ser varrido por `git stash`/`checkout` dele: ofereça o commit de blindagem ao usuário (detalhes em `windows-agent-file-editing` §7).
- Reporte **exit code + nº de PASS/FAIL + o rótulo honesto**: "verificação ad-hoc direcionada; a única suíte-verde é a do projeto (`67 passed`)".
- Se o workspace não tem comando canônico de teste (documento/skill/script), diga isso explicitamente em vez de alegar "tudo verificado".

### Se você criou ou atualizou uma skill nesta sessão

Espelhe a pasta **inteira** para o repositório pessoal (`C:\Projetos TI\agent-skills\skills\<nome>`) e valide com SHA-256 de **todos** os arquivos, não só do `SKILL.md`: a curadoria pode enriquecer a cópia instalada depois que você copiou, e foi assim que `references/` + um template novo ficaram faltando no repo (o `SKILL.md` já divergia). Cheque também se o recurso citado no corpo existe de fato (`templates/x.py`, `references/y.md`) — o mirror só está correto quando os dois lados têm o mesmo conjunto de arquivos.

O caso completo (quais números estavam errados, por que a captura por URL direta invalidou um agregado, e onde a suíte de testes realmente roda) está em `references/verificacao-do-relatorio.md`.

## Passo 9 — De QA exploratório a verificação de aceite (critério do plano)

Quando o plano já traz critérios de aceite ("membro não cria escala", "clique duplo não duplica"), o trabalho deixa de ser varredura e vira **verificação por fase**: um check por critério, evidência por execução, código de saída utilizável em CI.

Formato que funcionou (harness dentro do repo, ver `templates/harness-qa-fase.mjs`):

```
tools/qa/run.mjs            runner: fase1 | fase2 | todas; exit 0 passa, 1 falha, 2 fase inválida, 3 app fora do ar
tools/qa/lib/pw.mjs         resolve Playwright/Chromium já existentes (cache do npx)
tools/qa/lib/harness.mjs    sessão instrumentada (console, pageerror, HTTP>=400, dialogs, escritas) + login + digitar/esperarPor
tools/qa/lib/accounts.mjs   credenciais lidas do seed em runtime
tools/qa/lib/report.mjs     acumulador PASS/FAIL/AVISO -> resultados.json + resumo.md
tools/qa/checks/faseN.mjs   checks nomeados pelo critério do plano
docs/qa/evidencias/<fase>-<carimbo>/   resultados.json, resumo.md, shots/*.png   (gitignore)
docs/qa/fase-N-*.md         relatório versionado (tabela critério -> check -> resultado)
```

Regras que evitam check vazio:

- **Nome do check = critério do plano**, sem paráfrase: é o que permite ao leitor mapear plano → evidência.
- **Force a situação**, não a presença de código: `page.route(...).fulfill({ status: 500, contentType: "text/html", body: "<html>...Server Error..." })` prova de forma determinística que HTML de erro não chega à UI (melhor que caçar um 500 real).
- **Contagens de escrita**, não impressão: "não duplica" = número de `POST` capturados, com `page.on('request')`; some-se a isso nenhuma escrita partindo da conta errada.
- **Cheque os dois lados da capacidade**: que a conta sem permissão NÃO vê o item e que a com permissão VÊ e chega na rota. Um menu que esconde tudo passa em check mal escrito.
- Códigos de saída distintos para "app fora do ar" (3) e "check falhou" (1) — senão o CI culpa o código quando o problema é ambiente.

### Armadilhas novas (todas custaram uma rodada)

1. **Toast/aviso global que "não aparece".** Se o app guarda o toast em `useState` do provider e a mesma ação faz `toast(...)` + `router.replace(...)`, a mensagem morre junto com a remontagem da árvore na navegação. Sintoma: nenhum `[data-testid="toast"]` na página, mas o texto aparece no `screenshot` daquele instante. Diagnóstico decisivo: um `console.warn` dentro do setter — se ele roda e o toast não fica, é remontagem, não render. Correção no app: **estado do toast em escopo de módulo** (store + assinantes), com o host apenas assinando. Script de linha do tempo (poll de 500 ms lendo `[data-testid]` + `[role="alert"]`) resolve em uma execução.
2. **`testID` vira `data-testid` no RN Web** e é o seletor mais estável para toasts/banners — mas leia **dentro da janela de vida** (auto-dispensa típica de 6 s): `esperarPor` pelo seletor, nunca `sleep` fixo longo.
5. **Texto da tela é a evidência principal**, inclusive para validar PT-BR: compare com
normalização de acento (`NFD` + remoção de diacríticos) porque metade das strings do app vem sem acento
e a outra metade com.
6. **Check de "clique repetido não duplica" com `Promise.all([botao.click(), botao.click(), botao.click()])` dá PASS falso.**
Cada `locator.click()` faz round-trip de CDP e só executa quando o Playwright resolve a ação; entre um
clique e o seguinte o React commita o render, o `Button` já está `disabled` (o `loading` desabilita) e o
2º/3º clique morrem no DOM. Medido em tela com trava por `ref`: 1 POST — e **também 1 POST na tela sem
trava nenhuma**, ou seja o check "cobria" reentrância que não existia. O estímulo que separa os casos
precisa caber num **único turno de JS**:

```js
await page.evaluate((alvo) => {
  const el = [...document.querySelectorAll('[role="button"]')].find((e) => new RegExp(alvo, "i").test(e.innerText || ""));
  if (!el) return { achou: false };
  for (let i = 0; i < 3; i += 1) {                 // 3 eventos sem soltar o event loop
    el.dispatchEvent(new MouseEvent("pointerdown", { bubbles: true, cancelable: true }));
    el.dispatchEvent(new MouseEvent("pointerup", { bubbles: true, cancelable: true }));
    el.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true }));
  }
  return { achou: true };
}, "adicionar à agenda");
```

`pointerdown`+`pointerup` são obrigatórios: o `Pressable` do RN Web responde ao responder system e um
`click()` solitário não aciona `onPress`. Script pronto: `scripts/repro-mesmo-tick.mjs`.
7. **Sempre rode um CONTROLE na mesma rodada.** O mesmo estímulo numa tela sabidamente protegida
(trava por `ref`): controle = 1 POST e alvo = N POSTs é o que prova que a diferença é a trava ausente,
não o método. Sem controle, "capturei 3 POSTs" não distingue defeito de artefato do estímulo — e o
inverso é pior: "capturei 1 POST" pode significar estímulo fraco em vez de código correto (foi
exatamente o que aconteceu com o item 6 acima).
8. **Provar fluxo de escrita sem sujar o banco**: `page.route(regex, ...)` respondendo os POSTs com
`route.fulfill({ status: 201, contentType: "application/json", body: JSON.stringify({...}) })` e
`route.continue()` nos GETs. A evidência (quantos POSTs saíram) vem do contador do próprio handler e
**nada chega ao backend** — dispensa a limpeza do Passo 5/Armadilha nº 3 e permite repetir a repro à
vontade. Prefira isso a criar dados reais e apagar depois.
Números medidos, o caso da corrida que NÃO reproduziu e o porquê estão em
`references/prova-de-defeito-por-execucao.md`.

9. **Check que ESCREVE tem que criar a própria fixture, não mexer na demo.** Um
   check que publica/cancela a escala que o seed criou passa na 1ª rodada e falha
   na 2ª (o estado que ele pressupunha já mudou). Escreva o check para criar o
   próprio registro marcado (ex.: `"Escala QA Fase 4"`), operar só sobre ele e
   terminar cancelando — nunca dependa de um registro de seed com status
   específico (`published`/`draft`) para poder começar.
10. **Rode o check ANTES de a tela existir.** Com a UI ainda em construção
    (`/schedule-admin` devolvendo "Página não encontrada"), a execução vale como
    smoke test do encanamento: login por papel, gravação de
    `resultados.json`/`resumo.md`, import do check no runner. Placar do tipo
    `PASS 2 | FAIL 8`, com todos os FAILs na rota ausente, é o resultado
    esperado — e vira a linha de base para comparar quando a UI chegar (foi o
    caso real: a tela foi delegada em paralelo e o check já estava pronto).
11. **A tela pode não publicar `label` acessível.** No RN Web os rótulos costumam
    ser `<Text>` solto, então `getByLabel` volta vazio e o check "não preencheu
    nada". Use cascata tolerante — papel acessível → `getByPlaceholder` → texto
    visível → posição do input — e registre NA SAÍDA qual estratégia pegou
    (`nome=placeholder|label|null`), senão o FAIL não é diagnosticável. Cadência
    e snippets em `references/check-de-fase-em-ui-em-construcao.md`.
12. **Verificador ad-hoc de API: horário único por execução.** Se ele cria
    escalas/eventos para provar conflito de agenda, timestamp fixo faz a rodada
    seguinte cair na MESMA janela (a janela assumida é de 2 h) e o vermelho é do
    verificador, não do produto. Sorteie um horário distante
    (`now + 180d + random(0..8760)h`).
13. **Helper que chama `${BASE}/api/...` recebe o HTML do Expo com status 200.**
    `BASE` é o app (:8081), não a API (:8000). O check lê "lista vazia", todos os
    ids vêm `null` e você vai caçar defeito na tela. Declare
    `const API_BASE = process.env.QA_API || "http://localhost:8000"` no topo e use
    só ele nos helpers de API — `BASE` fica para `page.goto()`.
14. **O app guarda access E refresh no mesmo armazenamento.** Iterar as chaves do
    `localStorage` na ordem natural pega o refresh → 401 em tudo. Filtre por
    `/access/i` e exclua `/refresh/i`, validando o formato (JWT = 3 partes, > 40
    chars) antes de aceitar.
15. **"Está escrito na tela" é falso positivo quando o texto já estava lá.** A
    lista de candidatos já mostra o nome do membro antes de qualquer clique:
    prove o resultado na FONTE (`GET` da equipe/lookup) e deixe o texto da tela
    para provar apresentação. Idem para o registro de escrita: feche o status no
    evento de `response` (não com `req.response()` dentro do handler de request) e
    leia o ledger com `esperarPor`, nunca uma vez só.
16. **Toast de 6 s × clique que espera o botão reabilitar.** Num check de cliques
    rápidos, comece a ler o toast ANTES dos cliques
    (`const p = textoDoToast(page); await Promise.all([...]); const t = await p;`) —
    senão a confirmação lê `""` e parece que a ação não avisou nada.
17. **Rodada repetida cria registros homônimos e execução paralela colide.**
    Busque por nome pegando o **maior id** (a rodada anterior deixa um registro
    com o mesmo nome) e limpe por prefixo antes de rodar, incluindo o evento
    criado junto. Duas suítes rodando no mesmo banco de demonstração produzem
    `status=conflict`/recusa que não é regressão: re-rode a fase isolada antes de
    acusar o produto.
18. **Quando o contrato do produto muda, o check antigo é parte da mudança**
    (não regressão). Atualize-o com comentário do porquê, **migre a assertiva
    perdida** para o check da fase nova (na fonte certa), re-rode a fase antiga e
    diga no relatório qual contrato mudou. Aqui não vale "ajustei até ficar verde".

19. **O app pode estar configurado para uma origem que depende de proxy externo.**
    No moriah_app, `mobile/.env` traz `EXPO_PUBLIC_API_URL=/backend`: app e API na
    mesma origem, o que só funciona com o container do túnel (ngrok) no ar. Sem
    ele, toda chamada do app cai no **dev server do Expo**, que responde
    `index.html` com HTTP 200 — o cliente vê 2xx não-JSON, lança o erro de
    servidor e a tela mostra "Erro no servidor". Sintoma no aceite: a fase 1
    falha no login e o log do backend **não registra nenhuma requisição**
    (`docker logs <backend>` só mostra o que você mesmo pediu por curl).
    Diagnóstico em um comando:
    `curl -s -o /dev/null -w "%{http_code} %{content_type}" -X POST http://localhost:8081/backend/auth/login/`
    → `200 text/html` confirma o desvio. Correção: subir o túnel, ou apontar
    `EXPO_PUBLIC_API_URL` para a API real (ex.: `http://<ip-lan>:8000/api`) e
    reiniciar o Expo — **env do processo não sobrescreve o `.env`** no Expo dev
    (nem `EXPO_NO_DOTENV=1` resolveu no caso real), então edite o arquivo e
    restaure depois. Antes de culpar o merge/código, confirme CORS e host:
    `curl -i -X OPTIONS http://localhost:8000/api/auth/login/ -H "Origin: http://localhost:8081" -H "Access-Control-Request-Method: POST"`.

Detalhes, snippets e o caso real (Fase 4 do moriah_app: base da API, token,
ledger de escritas, prova pela equipe, contrato estático telas × check) estão em
`references/aceite-escritas-e-contrato.md`.

## Arquivos de apoio

| Arquivo | Uso |
|---|---|
| `templates/qa-sweep.mjs` | Varredura de rotas × papéis × viewports: copie, ajuste `ROUTES`/`ACCOUNTS` e rode. |
| `templates/harness-qa-fase.mjs` | Verificador de aceite por fase (sessão instrumentada + acumulador + runner com exit codes + evidência em `docs/qa/evidencias/`). |
| `templates/verificar-afirmacoes.py` | Esqueleto de verificação do relatório (re-deriva contagens, percentuais, schema, suíte, banco, hashes). |
| `templates/verificar-contrato-ui.py` | Verificador ESTÁTICO do contrato tela × check de aceite: lê os fontes e afirma rota, guarda, rótulos e payload que o check procura (inclui `sem_comentarios`, sem o qual o comentário que documenta a armadilha derruba a assertiva). Roda em ~1 s, sem rede/banco. |
| `references/verificacao-do-relatorio.md` | Registro do que deu errado e as armadilhas de contagem. |
| `references/verificacao-de-aceite.md` | Caso concreto de verificador por fase (critério → check), frescor da evidência e o episódio dos FAILs que eram do checker. |
| `references/prova-de-defeito-por-execucao.md` | Provar defeito por execução: controle obrigatório, interceptação de POST, casos de PASS falso e a corrida que não reproduziu (com o mecanismo que a absorvia). |
| `references/check-de-fase-em-ui-em-construcao.md` | Escrever check de fase antes de a tela existir: fixture própria, cascata tolerante de seletor (RN Web sem `label`), API como fonte de verdade, verificador ad-hoc de contrato HTTP e o placar-linha-de-base. |
| `references/aceite-escritas-e-contrato.md` | Base da API ≠ base do app, escolha do token access, ledger de escritas (status pelo evento de response + leitura esperando), provar pela fonte em vez de pelo texto, toast lido em paralelo, registro mais recente por id, colisão entre execuções paralelas e o contrato estático telas × check. |
| `scripts/repro-mesmo-tick.mjs` | Repro parametrizável de duplo envio: N eventos no mesmo turno de JS num botão, contando POSTs, com controle opcional e exit codes. |

⚠ `templates/qa-sweep.mjs` e `templates/harness-qa-fase.mjs` são citados acima mas **não existem nesta
instalação** (confira `linked_files` ao carregar a skill). Os templates que existem hoje são
`templates/verificar-afirmacoes.py` e `templates/verificar-contrato-ui.py`. O harness real e funcional
está em `tools/qa/` do projeto que os originou (moriah_app): `lib/pw.mjs` (resolve Playwright/Chromium
do cache do npx), `lib/harness.mjs` (sessão instrumentada + `login`/`digitar`/`texto`/`esperarPor`),
`lib/accounts.mjs` (credenciais lidas do seed em runtime), `lib/report.mjs` (`check(nome, ok, detalhe)`),
`checks/faseN.mjs` e `run.mjs` (runner com exit codes). Use-os como fonte ao recriar os templates —
não invente um harness novo.

Skill irmã: `dogfood` cobre o mesmo objetivo (QA exploratório → evidência → relatório) usando as ferramentas de browser interativas; use este aqui quando precisar de varredura em lote, captura de rede fim-a-fim e diff automático contra mockup.