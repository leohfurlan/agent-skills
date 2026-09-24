# Aceite por fase: escrita, base da API e contrato estático

Registro da rodada de aceite da Fase 4 (moriah_app, gestão de escalas). Cada item
abaixo custou pelo menos uma execução vermelha — e em todos eles o primeiro
suspeito ("a tela está quebrada") estava errado.

## 1. A API não vive no BASE do app

`BASE` é o servidor do **app** (Expo Web, :8081). Helper de check que monta
`${BASE}/api/...` recebe o `index.html` do Expo com **status 200** — o check lê
"lista vazia" e você vai caçar defeito no produto. Sintoma exato: `tipo=str`,
`itens=<bytes do html>`, e todos os ids vindo `null` de uma vez.

```js
// no topo do check
const API_BASE = process.env.QA_API || "http://localhost:8000";   // API != app
// e nas chamadas diretas:
await page.request.get(`${API_BASE}/api/schedules/`, { headers: cabecalhoAutenticacao(token) });
```

`BASE` continua sendo o certo para `page.goto()` (navegar o app). Antes de
escrever qualquer helper, confirme com `curl -s -o /dev/null -w "%{http_code}"`
nos dois hosts e com `grep -rn "EXPO_PUBLIC_API_URL" mobile/src`.

## 2. O app guarda DOIS tokens no mesmo armazenamento

`AsyncStorage` no web é `window.localStorage` puro. Com chaves cruas
(`moriah_access_token`, `moriah_refresh_token`), iterar `Object.keys` na ordem
natural pega o **refresh** e a API responde 401 em tudo — mais um "os helpers não
funcionam" que não é do produto.

```js
const chaves = Object.keys(window.localStorage);
const candidatas = chaves.filter((c) => /access/i.test(c))
  .concat(chaves.filter((c) => !/access/i.test(c) && !/refresh/i.test(c)));
// valida o formato antes de aceitar: JWT = 3 partes separadas por "." e > 40 chars
```

## 3. Status da escrita: feche pelo evento de resposta, e LEIA esperando

Dois defeitos empilhados, ambos aparecem como "o clique não chegou na API" com o
registro já criado no banco:

```js
// ❌ dentro do handler de request: por corrida resolvia null e o status ficava nulo
req.response().then((r) => { if (r) registro.status = r.status(); });

// ✅ o evento de response fecha o registro (mesma URL, status ainda nulo)
page.on("response", (resposta) => {
  if (resposta.request().method() === "GET") return;
  const escrita = estado.escritas.find((i) => i.status === null && i.url === resposta.url());
  if (escrita) escrita.status = resposta.status();
});
```

E no check, nunca leia o ledger uma vez só — o evento propaga de forma assíncrona:

```js
const escreveu = await esperarPor(async () =>
  sessao.escritas.some((i) => i.metodo === "POST" && /\/assignments\/?$/.test(i.url) && i.status === 201),
  { timeout: 5000 });
```

Diagnóstico que separa harness de produto: rodar a MESMA sequência num script
avulso com `page.on("response")` próprio e imprimir `sessao.escritas` no fim. Se
ali vem `status: 201`, o harness está certo e a leitura do check é que era cedo.

## 4. Prove pela fonte, não pelo texto que já estava na tela

`esperarPor(async () => contem(await texto(page), "Maria Silva"))` era **falso
positivo garantido**: a lista de candidatos já mostra esse nome antes de qualquer
clique. Prova de que um integrante entrou na equipe = a equipe na fonte:

```js
const entrouNaEquipe = await esperarPor(async () => {
  const detalhe = await detalheDaApi(page, criadaId);
  return (detalhe?.team || []).some((i) => contem(i.member_name, INTEGRANTE_QA));
}, { timeout: 12000 });
```

Regra geral: texto na tela serve para provar *apresentação*; para provar
*estado*, leia a API (ou o status de escrita do item 3). Use os dois quando o
critério fala das duas coisas.

## 5. Toast lido em paralelo com cliques rápidos

Toast típico morre em 6 s. Num check de "3 cliques no mesmo tick", o 2º/3º
`click()` esperam o botão voltar a ficar habilitado — quando `Promise.all`
resolve, o toast já sumiu e a confirmação lê `""`:

```js
const confirmacaoPromessa = textoDoToast(page, { timeout: 12000 });   // ANTES
await Promise.all([botao.click(), botao.click(), botao.click()]);
const confirmacao = await confirmacaoPromessa;
```

Para confirmar que o toast existe mesmo (1 clique), um script de 20 linhas que
poll a `[data-testid="toast"]` a cada 200 ms e imprime o texto + o tempo resolve
em uma execução: `toast em 235ms: "Rascunho criado ..."`.

## 6. Nome repetido entre rodadas: pegue o mais recente

O check cria `"Escala QA Fase 4"` toda vez. Buscar por nome e pegar o primeiro
acha a rodada anterior (rascunho vazio) e os passos seguintes operam no registro
errado:

```js
const iguais = linhas.filter((l) => l.name === nome).sort((a, b) => b.id - a.id);
return iguais[0] || null;
```

Combine com limpeza por prefixo antes de cada rodada (`app.objects.filter(name__istartswith=...)`),
cobrindo TAMBÉM o evento criado junto (a escala nasce com evento; apagar só a
escala deixa 14 eventos órfãos no `/api/me/events/`).

## 7. Duas execuções em paralelo colidem no banco da demonstração

Rodar `node tools/qa/run.mjs todas` enquanto outro agente roda a suíte dele no
mesmo banco produz vermelho que não é regressão: dois processos escalam a mesma
pessoa no mesmo horário (a segunda entra como `status=conflict`) e o membro não
consegue confirmar. Sintoma de colisão: falha em check que passou minutos antes +
`status=conflict`/`rejeitado` inesperado.

Protocolo: limpar, rodar **uma fase por vez**, e ao ver vermelho suspeito re-rodar
isolado antes de acusar o produto. Cheque processos concorrentes
(`ps -W | grep node`) quando o resultado oscilar.

## 8. Contrato estático telas × check (quando o app pode estar fora do ar)

Complemento barato ao Playwright: ler os arquivos alterados e afirmar que a
interface oferece rota, rótulo e payload que o check procura, e que o check fala
com a API e não com o app. Rodou 22 checagens em ~1 s:

```python
def sem_comentarios(fonte):        # assertiva vale para código, não para a prosa
    sem_bloco = re.sub(r"/\*.*?\*/", "", fonte, flags=re.S)
    return "\n".join(l for l in sem_bloco.splitlines() if not l.strip().startswith("//"))

confere("guarda cobre o prefixo /schedule-admin", "PREFIXOS_DE_GESTAO" in layout)
confere("criacao envia ministry_id e nasce rascunho", "ministry_id: ministryId" in criar and 'submit("draft")' in criar)
confere("check usa a API (:8000) e nao o BASE do app",
        "API_BASE" in check and "${BASE}/api/" not in sem_comentarios(check))
```

Sem `sem_comentarios` o próprio texto que explica a armadilha derruba a assertiva
(o comentário citava `${BASE}/api/...`) — mesma classe do "assertiva de fonte
mente por comentário" do SKILL.md. Falha do checker, não do código.

## 9. Quando o contrato do produto muda, o check antigo é parte da mudança

A Fase 4 tornou a criação **draft-first** (nasce rascunho, destino = tela da
escala). Isso quebrou dois checks da Fase 1, que esperavam publicar direto e cair
na agenda — não era regressão, era expectativa vencida.

Como tratar (e como relatar):

1. Atualize o check antigo com comentário dizendo **por que** mudou
   (`// Fase 4: o formulário nasce como RASCUNHO ... por isso o botão mudou de nome`).
2. Não perca cobertura: a assertiva que saiu de um check vai para o outro, na
   fonte certa. "O evento entra na agenda" migrou para o check 3 da fase 4, agora
   contra `GET /api/me/events/`.
3. Diga no relatório qual contrato mudou e qual check acompanhou — check ajustado
   até ficar verde, sem investigação, é teatro.
4. Rode a fase antiga de novo: 18 PASS / 0 FAIL é o que legitima a mudança.
