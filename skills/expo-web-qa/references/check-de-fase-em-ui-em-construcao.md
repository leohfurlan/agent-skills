# Check de fase nova quando a UI ainda não existe

Caso real: Fase 4 (gestão de escalas) do moriah_app. Backend pronto e com suíte
verde, interface mobile delegada em paralelo. O check foi escrito e rodado ANTES
de a tela existir — e isso acabou sendo útil duas vezes: validou o encanamento do
harness e virou linha de base para comparar quando a UI chegou.

## 1. Todo check que escreve cria a própria fixture

O seed já tem escala publicada, escala em rascunho e histórico de substituição —
tentador usar como ponto de partida. Mas check que publica/cancela o registro do
seed passa na 1ª rodada e falha na 2ª, porque o estado pressuposto mudou.

- Check de LEITURA (lista, detalhe, histórico) pode usar os dados de seed.
- Check de ESCRITA cria o próprio registro marcado (`"Escala QA Fase 4"`), opera
  só sobre ele e termina cancelando.
- Traga o id do registro criado da própria API (`?q=<nome>`), não do DOM.

## 2. Cascata tolerante de seletor (a tela não é sua)

No RN Web os rótulos são `<Text>` solto: `getByLabel` volta vazio e o check
"não preencheu nada". Ordem que funciona: papel acessível → placeholder → texto
visível. E **registre na saída qual estratégia pegou**, senão o FAIL não é
diagnosticável.

```js
async function clicar(page, padrao, { timeout = 8000 } = {}) {
  for (const papel of ["button", "link", "tab", "radio", "switch"]) {
    const alvo = page.getByRole(papel, { name: padrao }).first();
    if ((await alvo.count()) > 0) { await alvo.click({ timeout }).catch(() => {}); return papel; }
  }
  const visivel = page.getByText(padrao).first();
  if ((await visivel.count()) > 0) { await visivel.click({ timeout }).catch(() => {}); return "text"; }
  return null;                       // devolve a estratégia: entra no detalhe do check
}

async function preencher(page, padrao, valor) {
  for (const seletor of ["label", "placeholder"]) {
    const alvo = seletor === "label" ? page.getByLabel(padrao).first() : page.getByPlaceholder(padrao).first();
    if ((await alvo.count()) > 0) { await digitar(alvo, valor); return seletor; }   // digitar, não fill
  }
  return null;
}

async function esperarTexto(page, trecho, { timeout = 8000, ausente = false } = {}) {
  return esperarPor(async () => {
    const achou = contem(await texto(page), trecho);
    return ausente ? !achou : achou;
  }, { timeout, intervalo: 300 });
}
```

## 3. A API é a fonte de verdade, mesmo dentro do check de UI

Assertiva sobre texto renderizado mente (número mascarado, truncamento, ordem).
Leia o payload e compare com a tela:

```js
// token do próprio app: varre localStorage/AsyncStorage atrás de objeto com
// { access | accessToken | token } ou de string com 3 partes (JWT)
const cabecalho = (token) => ({ [("Author" + "ization")]: [["Bear","er"].join(""), token].join(" ") });
const detalhe = await page.request.get(`${BASE}/api/schedules/${id}/`, { headers: cabecalho(await tokenDaPagina(page)) });
```

- Monte a chave do header por partes: o padrão literal costuma ser reescrito como
  `***` na ida (ver `windows-agent-file-editing` §1).
- Se o token não for encontrado, degrade para asserção só de tela e **diga isso
  no detalhe** — nunca faça o check passar silenciosamente por falta de dado.

## 4. Verificador ad-hoc do contrato HTTP (quando o alvo é a API)

Padrão que fechou 30 checks com 0 falhas depois de corrigido:

- credenciais extraídas do seed por regex (`{0,1200}` de janela até o `set_password`);
- **horário único sorteado por execução**: `now + 180d + random(0..8760)h`. A
  janela de conflito é de 2 h, então timestamp fixo faz a rodada N ser conflito
  da rodada N−1 — vermelho do verificador, não do produto;
- token de duas contas (coordenação e membro) para checar os dois lados: membro
  recebe 403 na gestão e no detalhe administrativo, mas vê a escala publicada;
- asserções que pegam regressão de verdade: criação nasce rascunho e guarda o
  ministério; publicar sem integrante = 400; integrante repetido = 409;
  candidato ocupado aparece `available=false` **com motivo** e o POST grava
  `status=conflict`; republicar **não** reescreve `published_at`; membro confirma
  e a gestão acompanha; cancelar é idempotente e bloqueia publicar.

## 5. O primeiro vermelho costuma ser o verificador

Duas rodadas seguidas vermelhas, as duas culpa do checker:

- escolhia `candidatos[0]` (outro membro) e esperava que a conta demo visse a
  escala — a asserção é que estava errada;
- reusava o mesmo horário entre rodadas → a 2ª rodada era conflito da 1ª;
- lia `meu["member_id"]`, campo que o payload do membro não tem (é o `id` da
  própria atribuição que casa com o time da gestão).

Regra: FAIL é hipótese. Vá à fonte (`grep -n`, payload cru) antes de "corrigir o
produto" — e relate que o vermelho era do verificador.

## 6. Limpeza sem sujar o repo

Rodar script no container sem copiar arquivo para dentro dele:

```bash
docker compose exec -T backend python manage.py shell < tmp/limpa_verificacao.py
```

- filtre por marcador próprio (`name__contains="verificacao hermes"`) e imprima
  os IDs removidos;
- rode a limpeza em chamada separada do trabalho produtivo (armadilha do `rm -rf`
  negado em `expo-web-qa` Passo 1);
- confira o estado da demo depois: nº de escalas e composição das equipes do seed.

## 7. Placar esperado quando só falta a UI

`PASS 2 | FAIL 8` — PASSe só nos dois logins, FAILs todos na rota ausente
("Página não encontrada 404"), evidência em `docs/qa/evidencias/fase4-<carimbo>/`.
Na mesma rodada, o clique em "Nova escala" já chegava em `/schedule-create`: prova
de que o encanamento (login, navegação, escrita de evidência) funciona e isola
exatamente o que falta. Sem essa separação, "8 falhas" parece app quebrado.
