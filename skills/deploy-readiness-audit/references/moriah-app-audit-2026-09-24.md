# moriah_app — auditoria de prontidão para produção (2026-09-24)

Snapshot do que foi apurado. **Reverifique antes de reusar** (Passo 1 e 2 do
SKILL.md): branch, contagem de testes e lacunas mudam a cada sessão de agente.

## Repo

- Raiz: `C:\Projetos TI\moriah_app` — monorepo `backend/` (Django 5.1.10 + DRF +
  Postgres) e `mobile/` (Expo/React Native, web na 8081).
- Remoto: `https://github.com/leohfurlan/moriah_app.git`
- Branch na auditoria: `codex/finance-contribution-ledger` (HEAD `407dff5`,
  18/09/2026 10:09), 15 modificados + 20 untracked **sem commit**.
- Host: `python` 3.14 com django 5.1.10 e pytest globais (a suíte roda no host,
  `config.settings_test` = SQLite em memória; não precisa de Postgres).

## As quatro linhas divergentes (o achado central)

| Linha | Commit / data | Tem | NÃO tem |
|---|---|---|---|
| `origin/master` | `4219d40`, 17/09 18:46 (16 commits, PRs #1–#5) | Fases 0–5: `Feedback.tsx`, `navigation.ts`, `+not-found.tsx`, notificações persistentes, paginação, ministérios, date pickers, `tools/qa/`, `docs/qa/fase-1..5` | `backend/apps/content`, `FinancialEntry`/conciliação, avisos de evento, `finance-management` |
| `codex/finance-contribution-ledger` | `407dff5`, 18/09 10:09 — base `40ebc25` (16/09 11:18) + 1 commit de 42 arquivos | Fase 6 conteúdo (`backend/apps/content`, `test_content_api.py`), financeiro, avisos de evento | todo o bloco acima (Fases 1–5), `tools/qa/` |
| `codex/moriah-navigation-admin` | `bf2af12`, 17/09 21:16, não mergeado | implementação **paralela** do mesmo `backend/apps/content`, com `tests/test_content.py` (138 linhas) que a linha atual não tem | — |
| working tree | não commitado | 9 rotas placeholder, `PeopleDirectoryScreen`, `Markdown.tsx`, `CONTEXT.md`, `docs/features/F-PS-01`, `docs/qa/` (evidências), o próprio plano do piloto | nenhum commit o contém |

`40ebc25` É ancestral de `origin/master` (`git merge-base --is-ancestor` = SIM) e
mesmo assim faltam 16 commits: o branch tem a fase mais nova sem as anteriores.

## Verdes medidos

- `python -m pytest -q` → **1 failed, 80 passed** (19 arquivos de teste).
- `npm run typecheck` no `mobile/` → passa.
- `manage.py makemigrations --check --dry-run` → `No changes detected`.
- `manage.py check --deploy` com `DJANGO_DEBUG=false` → só `security.W009` +
  avisos de `drf_spectacular`. Endurecimento de produção já no `settings.py`.
- Auditoria implementada: `apps/audit/signals.py` grava `AuditLog` em
  contribuição/membro/escala; `apps/content/views.py` grava publish/unpublish.
- Storage S3/R2 com URL assinada (`querystring_auth`, 900s) atrás de
  `USE_S3_STORAGE`; `scripts/backup_postgres.sh` + restore; CI no GitHub Actions
  (pytest + spectacular + `check` + typecheck); `app.json`/`eas.json` prontos.

## O vermelho (fixture podre, não regressão)

`backend/apps/events/tests/test_event_api.py:31` — evento criado em 20/09/2026;
`MyChurchEventsView.get_queryset` filtra `start_at__gte=timezone.now() -
timedelta(days=1)`; execução em 24/09 → lista vazia.
Conserto: `timezone.now() + timedelta(days=2)`.

## Lacunas do plano do piloto

Plano: `docs/architecture/plano-arquitetura-oracle-neon-piloto.md` (Oracle VPS +
Neon + R2/S3). Na auditoria, **0 de 10** entregáveis da §11 existiam:

`docker-compose.pilot.yml`; config Neon; config S3/R2; runbook deploy/rollback;
runbook backup/restore; health check; `.env.example` atualizado; testes de
regressão; evidências do 1º deploy/restore; relatório do piloto.

Lacunas verificadas no código:

- `Dockerfile`: `CMD ["python","manage.py","runserver","0.0.0.0:8000"]`; sem
  `gunicorn`/`uvicorn` no `requirements.txt`.
- `docker-compose.yml`: `migrate && seed_mvp && runserver` no boot (seed de
  demonstração rodaria a cada deploy); `5432:5432` exposta.
- Sem endpoint `/health/`; sem `SSLMODE`/`CONN_MAX_AGE` no `settings.py` (linha 80)
  nem no `.env.example`.
- CI roda `manage.py check` (não `--deploy`).
- `tools/qa/` ausente neste branch → o aceite `node tools/qa/run.mjs` não roda.

## PRD e escopo

- `PRD_Moriah_App_v1.md` §13 (Segurança e LGPD): com lastro = auditoria
  financeira/membros, restrição a dado financeiro individual (URL assinada),
  HTTPS no Django. Sem lastro = política de retenção de comprovantes,
  consentimento do membro, backup agendado com alerta, revisão de logs sensíveis.
- 9 telas placeholder (`ModulePlaceholderScreen`) para bands, setlists, repertoire,
  bible-school, classes, members, ministries, visitors, finance-management —
  contrariam o plano §7/§11 ("não criar apenas shells de navegação").
- F10 Projetos Sociais está fora do MVP (PRD §7.6); `docs/features/F-PS-01/` é
  spec draft.
- Higiene: `.codex-remote-attachments/` (2 diretórios) e `tmp/`
  (`uv-cache-debug`, `redeploy-phase6.override.yml`) não devem ser versionados —
  reportar, não remover.

## Ordem de trabalho proposta (e aceita como estrutura)

Etapa 0 consolidar: merge de `origin/master` no branch (conflitos esperados em
`mobile/app/_layout.tsx`, `ContentScreen.tsx`, `Screen.tsx`, `theme.ts`,
`services/api.ts`, `accounts/permissions.py`, `members/views.py`) → decidir qual
implementação de content fica e trazer os testes da que perder → corrigir o teste
de evento → commitar o working tree → push + PR com CI verde.
Etapa 1 adaptar: gunicorn + Dockerfile de produção → `docker-compose.pilot.yml` →
`/health/` + `check --deploy` no CI → `SSLMODE`/`CONN_MAX_AGE` + `.env.example` →
separar migrate/seed → runbooks + backup agendado com alerta.
Etapa 2 provisionar: VPS Oracle + Neon + R2/S3 + DNS/HTTPS → deploy controlado com
migração na branch certa do Neon → testar restore e rollback → publicar mobile
(EAS) com `EXPO_PUBLIC_API_URL` da API pública → relatório do piloto com evidências
(§8 do plano).
