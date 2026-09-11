---
name: silvia-agent
description: Diagnosticar e destravar sessões do SilvIA (agente CLI de desenvolvimento SDD local-first e governado) — comandos, gates de aprovação, configuração de providers, leitura do event log e verificação de credenciais. Usar quando o usuário mencionar "silvia", sessões em waiting-for-action, erros invalid-plan/plan-required, ou o orquestrador que parece nunca responder.
---

# SilvIA (agente SDD local)

SilvIA é um agente de desenvolvimento **governado**: nada de agente roda até existir um plano *aprovado*. Isso é design, não bug. A maioria dos pedidos "o silvia não faz nada" se resume a descobrir qual gate está fechado.

## Onde as coisas ficam (Windows)

- Projeto: `<repo>/.silvia/config.toml` — providers (ex.: `[providers.astra]` com endpoint/model/`credential_ref = "env:NAME"`).
- Home global: `C:\Users\<user>\AppData\Roaming\SilvIA` (config) e `...\AppData\Local\SilvIA\data` (SQLite + worktrees isolados em `data\worktrees\<session-id>\`).
- `silvia doctor` mostra os caminhos resolvidos + providers parseados, **sem chamar o provider** (bom primeiro sinal; provider "ok" no doctor não significa chave válida).

## Roteiro de diagnóstico

1. `silvia doctor` — versão, providers lidos, SQLite/FTS5.
2. `silvia session list` — IDs, name, state, checkout. Estados comuns: `created`, `waiting-for-action`.
3. `silvia status <SESSION-ID>` — **vários comandos exigem o UUID completo**; ID truncado dá `ambiguous-session` ou `not-found`. Campos `agent=[]`, `attempt=[]`, `plan=[]` = o orquestrador nunca executou de verdade.
4. Linha do tempo real via event log: `silvia events <id> --json` é enorme; filtre com `scripts/parse_events.py`:
   `silvia events <id> --json | python <dir-da-skill>/scripts/parse_events.py`
5. Checar credencial `env:NAME` dos dois lugares: no shell atual (`[ -n "$NAME" ]`) **e** nos escopos Windows:
   `powershell -NoProfile -Command "[Environment]::GetEnvironmentVariable('NAME','User')"` (e `'Machine'`).
6. Reproduzir o erro vivo do provedor: `silvia session propose --session <id>` → `invalid-plan: Orchestrator did not return a valid task graph` tinha 3 causas distintas (todas corrigidas no código em set/2026 — ver abaixo "Classes de falha invalid-plan").

## Resolução de credenciais (importante)

- `credential_ref = "env:NAME"` NÃO exige variável de ambiente: `_local_env_value` em `silvia/providers.py` faz fallback para o `.env` **ao lado do pacote** (checkout editable: `astra-orchestrator\silvia\.env`). Antes de setar `setx`, verifique esse arquivo.
- AppData\Local\SilvIA e Roaming\SilvIA NÃO têm .env (pista falsa comum).
- Provar resolução sem vazar segredo: `python -c "from silvia.providers import credential; from silvia.security import Redactor; print(len(credential('env:BAI_API_KEY', Redactor())))"` (35 = OK).

## Classes de falha invalid-plan (corrigidas no código do astra-orchestrator)

- **JSON embrulhado**: glm-5.3-flash devolve ` ```json ... ``` ` ou prosa+JSON → `json.loads` seco estourava. Fix: `parse_json_value()` em `silvia/core.py` (plain/fenced/extração balanceada), usado em plan() e na revisão de ferramentas.
- **Truncamento por reasoning**: modelos de raciocínio gastam ~3,5k tokens só de pensamento → com `max_output_tokens = 4096` a resposta morre em `finish_reason: length` (`provider-incomplete`). Fix: 16384 no `.silvia/config.toml` do horebio.
- **Drift de formato do modelo**: `owned_paths`/`verification` vindo como string, limites como string. Fix: coerção em `WorkItem.__post_init__` (e erro de validação agora nomeia o item/campo faltante: "Work item 'X' is missing: owned_paths").
- Contrato de posse: TODO item precisa de `owned_paths` não-vazio e disjoint entre itens — até item de inspeção deve possuir um arquivo de relatório; verification deve ser lista de argv-arrays, não shell strings. O prompt de planning foi reforçado com isso.

## Ferramentas auxiliares

- Reproduzir resposta crua do provedor fora do CLI: `Application(home=..., project=...)` → `app.agents._planning_context(sid)` + mesmo system prompt de `plan()` + `build_provider(route, app.store.redactor).invoke(...)` → `parse_json_value` → inspecionar items. Chamada real ~45-60s (timeout ≥300).
- `import asyncio` faltando em providers.py fazia retry de HTTP 429 crashar com NameError — corrigido.
- Suite de verificação: `cd /c/Projetos TI/astra-orchestrator && py -3.14 -m pytest tests -q` (~59 testes, ~16s).

## O gate de fluxo (a resposta para "não roda")

```
silvia session propose --session <id>   # plano via LLM (precisa provider OK)
  — ou —
silvia session plan <file.json> --session <id>   # task graph manual, funciona offline
silvia approve <id>                     # aprovar a proposta exata pendente
silvia run <id>                         # só depois disso: plan-required = gate esperado
```

- `silvia run` sem plano aprovado responde `plan-required: No approved work plan exists.` — não é falha.
- `silvia approvals <id>` vazio (`[]`) = nenhuma proposta pendente; o `session propose` anterior provavelmente falhou antes de criar proposta.

## Armadilhas

- **Mensagens de chat não disparam nada**: o que se digita na TUI vira `session.message_queued` no event log e fica parado se não há plano/provedor. O usuário pode achar que "ele ignora" — mostre a fila via eventos.
- `/to-specs` etc. escritos na conversa são só texto. O subsistema de skills é separado: `silvia skills sources` (fontes precisam de registro explícito via `silvia skills register name path`), `silvia skills list <source>`, `silvia skills run`.
- `setx` só vale para **processos novos** — depois de setar a chave, reiniciar o terminal/processo do SilvIA.
- Conferir o nome do modelo contra `GET <endpoint>/models` (com a chave) antes de culpar a ferramenta: `invalid-plan` também cobre modelo inexistente.
- Comandos ambíguos sem ID (`silvia status`, `silvia agents`) exigem sessão; prefira sempre UUID completo.

## Subcomandos úteis

`init, session {new,list,show,resume,archive,revise,plan,propose,reconcile}, run, status, inspect, resume, pause, cancel, complete, events, gates, agents, approvals, new, sessions, approve, deny, report, export, verify, memory {remember,recall,export,retention,forget,promote}, skills {register,sources,list,show,validate,run}, tui [id] [--theme hermes|dark], watch, doctor, storage, config {paths,example}, artifact`.

`silvia config example` imprime um config.toml de referência (keyring para credenciais remotas: `credential_ref = "keyring:provider-name"`).

## Contexto do usuário (horebio)

O projeto `C:\Projetos TI\horebio` usa harness Atos SDD (skill `harness-atos-sdd` cobre os docs/harness; esta skill cobre a **ferramenta** SilvIA). Provider configurado: `astra` → `https://api.b.ai/v1`, adapter openai-compatible, `credential_ref = env:BAI_API_KEY`. Fonte de skills registrada: `C:\Projetos TI\agent-skills`.
