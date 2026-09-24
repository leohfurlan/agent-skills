# Verificação de aceite: como foi feito no Moriah (16/09/2026)

Caso concreto que originou o Passo 9 (verificador por fase) e as armadilhas de
assertiva de fonte. App Expo/React Native Web (`mobile/`) + Django (`backend/`),
plano com critérios de aceite escritos (`docs/plano-*.md` §6).

## Estrutura que ficou no repo

```
tools/qa/run.mjs            fase1 | fase2 | todas ; exit 0 passa, 1 falha, 2 fase inválida, 3 app fora do ar
tools/qa/lib/pw.mjs         resolve Playwright do cache do npx + chromium de %LOCALAPPDATA%
tools/qa/lib/harness.mjs    sessão instrumentada: console, pageerror, HTTP>=400, dialogs, escritas (POST/PUT/PATCH)
tools/qa/lib/accounts.mjs   credenciais extraídas do seed em runtime (nunca literais no script)
tools/qa/lib/report.mjs     acumulador PASS/FAIL/AVISO -> resultados.json + resumo.md + shots/
tools/qa/checks/faseN.mjs   um check por critério do plano, com o texto do critério no nome
tools/qa/scripts/           diagnósticos pontuais (linha do tempo do toast, etc.)
docs/qa/evidencias/<fase>-<carimbo>/   saída por execução (no .gitignore)
docs/qa/fase-N-*.md         relatório versionado: tabela critério -> check -> resultado
```

31 checks (18 na fase 1, 13 na fase 2), todos derivados dos critérios escritos —
nenhum "conferi no olho". Códigos de saída separados para "app fora do ar" (3) e
"check falhou" (1).

## O que cada check mediu (padrões reaproveitáveis)

| Critério | Como foi provocado, não deduzido |
|---|---|
| erro visível em vez de Alert | preencher senha errada, esperar texto + `getByRole("alert")`; contar `dialogs` do harness (deve ser 0) |
| membro não cria escala | conta de membro abre `/schedule-create` na mão; ler `[data-testid="toast"]` e conferir a rota final; contar POSTs de escala (0) |
| clique duplo não duplica | 3 cliques no mesmo tick (`Promise.all`), contar `POST /api/schedules/` == 1 |
| HTML do Django não vaza | `page.route("**/api/me/statement/**", fulfill 500 text/html)` com HTML de erro real; assertiva de ausência (`traceback`, `server error`) + presença de mensagem amigável |
| 404 em português | `goto` de rota inexistente; ausência do "Unmatched Route" do expo-router |
| URL sem parâmetro não chama API | `goto /song/1` sem `scheduleId`; `page.on("request")` filtrado por `/undefined/` == 0 |
| dado inventado não aparece | assertiva negativa com o rótulo **completo** ("Continuar na Escola Bíblica"), não fragmento |
| capacidade respeitada | medir os **dois lados**: conta sem permissão não vê o item, conta com permissão vê **e chega na rota** |
| aba ativa | `getComputedStyle(el).backgroundColor` das abas: exatamente uma com fundo próprio, e é a da rota |

## Episódio: 4 FAILs que eram do checker

O verificador ad-hoc (29 assertivas sobre a fonte) acusou 4 falhas. Nenhuma era
defeito de código — todas vinham de busca ingênua de substring:

| Assertiva | Por que falhou |
|---|---|
| rotulos decorativos fora do menu | os rótulos ("Visitantes", "Setlists", "Palavras") aparecem no **docstring** que explica a remoção |
| HomeScreen sem KPI inventada | "248", "12.450", "87%", "7 de 12" aparecem no **docstring** que documenta o que saiu |
| Screen sem arrays duplicados | `styles.sidebarGroups` é chave de `StyleSheet` legítima; só a **declaração** `const sidebarGroups` precisava sumir |
| HTML de erro nunca chega à UI | a detecção real é regex (`/text\/html/i`, `/<(!doctype|html)/i`), então o literal `text/html` não existe no arquivo |

Correção aplicada no checker: função `codigo()` que remove `/* */` e linhas `//`/`*`,
assertiva sobre declaração (`const x`) e assertiva por regex para padrões.
Re-rodado: 29/29. O relato ao usuário declarou o episódio.

## Frescor da evidência

```python
fontes = [navigation.ts, Feedback.tsx, Screen.tsx, HomeScreen.tsx, _layout.tsx, permissions.py]
mais_nova = max(f.stat().st_mtime for f in fontes)
evidencia = sorted(base.glob("fase1-*"))[-1] / "resultados.json"
assert evidencia.stat().st_mtime >= mais_nova   # evidência cobre a última edição
```

Sem isso, um relatório verde de uma execução anterior passa como se cobrisse o
código atual. O harness do Hermes, aliás, avisa "verification stale/unverified"
mesmo quando o código não mudou: a resposta é rodar de novo e mostrar a saída
nova, nunca discutir com o aviso.

## Classes de defeito que só apareceram com check ao vivo

- **Toast em `useState` de provider morre na navegação**: `toast(...)` seguido de
  `router.replace(...)` perde a mensagem na remontagem. Correção: estado em
  escopo de módulo + host assinando. Diagnóstico: `console.warn` no setter (roda
  e nada aparece na tela) + linha do tempo lendo `[data-testid]` a cada 500 ms.
- **`Alert.alert` é no-op no web**: permissão negada sem aviso, e `onPress` do
  Alert nunca executa (navegação perdida). Ver armadilha nº 2 do SKILL.md.
- **`undefined` no path**: rota dinâmica sem parâmetro monta
  `/me/schedules/undefined/` e devolve 404 enganoso; guarda explícita na tela.
