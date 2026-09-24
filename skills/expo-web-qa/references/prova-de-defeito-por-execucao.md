# Provar defeito por execução (e o que passa por prova sem ser)

Registro de uma revisão real (App Moriah, Expo Web + Django) em que a diferença entre
"o harness deu PASS" e "o defeito existe" foi a **forma do estímulo** e a presença de
um **controle**.

## 1. O caso: "clique repetido não duplica"

O check de aceite da fase usava `Promise.all([botao.click(), botao.click(), botao.click()])`
e reportava, com razão aparente, que a trava de reentrância funcionava.

Medição desta sessão, com dois estímulos diferentes na MESMA tela (3 cliques):

| Estímulo | Tela com trava por `ref` | Tela só com guarda de `state` |
|---|---|---|
| `Promise.all` de 3 `locator.click()` | 1 POST | **1 POST** (falso PASS) |
| 3× `pointerdown`+`pointerup`+`click` num `page.evaluate` | 1 POST | **3 POSTs** |

Por que o primeiro engana: cada `locator.click()` é uma ação do Playwright com
round-trip de CDP. Entre um clique e o próximo o React commita o render, o `Button`
já entrou em `disabled` (o projeto desabilita com `loading`) e os cliques restantes
morrem no DOM — o mesmo comportamento que um usuário humano teria. Só o disparo
síncrono dentro de um turno de JS reproduz a janela real de reentrância.

Lição operacional: um check de "não duplica" que não consegue FALHAR numa tela sem
trava não é evidência de nada. Antes de escrever "coberto", pergunte se o estímulo do
check distingue o código protegido do desprotegido.

## 2. Controle obrigatório

O controle é o que separa defect de artefato do estímulo: mesma rodada, mesmo
estímulo, numa tela sabidamente protegida (`submittingRef` + `submitting`). Controle
1 POST e alvo 3 POSTs ⇒ a variável é a trava ausente. Sem controle, "capturei 3
POSTs" não vale como prova.

`scripts/repro-mesmo-tick.mjs` implementa isso: `--url/--botao/--post` para o alvo e
`--controle-url/--controle-botao/--controle-post` para o controle, com exit code 0
quando o defeito reproduz e 2 quando não.

## 3. Reproduzir escrita sem sujar o banco

Interceptar o POST e responder no cliente:

```js
await page.route(/\/api\/me\/agenda\/?(\?.*)?$/, async (rota) => {
  if (rota.request().method() !== "POST") return rota.continue();   // GET passa
  posts += 1;
  await rota.fulfill({ status: 201, contentType: "application/json",
                       body: JSON.stringify({ id: 900000 + posts, ... }) });
});
```

A evidência é a **contagem** de requisições (o defeito é "quantos POSTs saíram"), então
nada precisa chegar ao backend: dispensa criar dados e apagar depois (Passo 5/Armadilha
nº 3) e permite repetir a rodada quantas vezes quiser. Bônus: respostas fabricadas no
`route` permitem forçar cenários determinísticos (500 HTML do Django, 4xx de permissão).

Para medir outra coisa que não escrita (ex.: estado da UI diante de falha), o mesmo
`page.route` + `fulfill({ status: 500 })` prova o comportamento sem depender de achar
um erro real.

## 4. Quando a corrida NÃO reproduz: ache o mecanismo que a absorve

Hipótese testada: um `GET /api/me/` anônimo lento, respondido 401 DEPOIS do login,
zeraria o perfil em memória e jogaria o usuário de volta à tela de login
(`useAuth.ts:53-56` → `home.tsx:19-22`).

Resultado medido: `anonimos=2 comToken=2 | url final=/home`, perfil intacto. O
estímulo chegou — e foi **absorvido** por outro caminho do próprio código:
`api.ts:128-135` manda todo 401 de endpoint não-auth para `refreshAccessToken()` e,
havendo refresh válido, **repete a chamada já com o token atual**; o retry devolve o
perfil correto e sobrescreve o dano. Sem essa explicação, o relatório diria apenas
"não reproduzi", que é indistinguível de "meu estímulo foi fraco".

Regra: hipótese não reproduzida entra no relatório com o mecanismo mitigador citado
(arquivo:linha) e com a severidade rebaixada. O que continua sem cobertura (duas
requisições autenticadas concorrentes de identidades diferentes, sem caminho de UI
alcançável) é declarado como hipótese, não como defeito.

## 5. Contexto desta revisão (formato de entrega)

Pedido do usuário, resumido: revisar a implementação das fases 0–2 na working tree
contra o commit base e uma lista de docs de plano/decisão, **sem alterar arquivos**
(nada de stage/commit/deploy), entregando por item: severidade, `arquivo:linha`,
cenário de reprodução, impacto, requisito relacionado, confirmado × hipotético e
correção objetiva; e no fim: confirmados, não reproduzidos, já cobertos por testes,
validações ainda necessárias e conclusão sobre prontidão para commit.

Como a proibição de escrita valia também para scripts de repro, os três scripts foram
criados no temp do SO (`%TEMP%\hermes-review-repro*.mjs`), reusando `tools/qa/lib/*.mjs`
do projeto por URL absoluta (`file:///...`, porque `NODE_PATH` não vale em ESM) — e
rodados a partir da raiz do repo, porque `accounts.mjs` lê o seed por caminho relativo.
