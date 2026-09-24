---
name: deploy-readiness-audit
description: Auditar se um repositório está REALMENTE pronto para produção — qual revisão seria implantada (forense de branches divergentes), o que está verde medido agora (testes, typecheck, migrações, check --deploy), quais costuras de deploy existem (runtime, compose, /health/, SSL do banco, seed no boot, segredos, storage, backup, runbooks) e o que falta confrontando o PRD/plano do próprio projeto entregável por entregável. Usar quando o usuário pede "o que falta para colocar online", "está pronto para produção?", revisão pré-deploy, ou conferir código contra PRD/planos.
metadata:
  hermes:
    tags: [deploy, producao, auditoria, git, django, expo, prd]
    related_skills: [code-review, requesting-code-review, windows-agent-file-editing, github-pr-workflow]
---

# Auditoria de prontidão para produção

Pergunta típica: *"qual o estado atual do código e, conferindo com o PRD e os
planos, o que precisa ser feito para colocá-lo online?"* A resposta não é
opinião: é uma lista fechada de lacunas, cada uma com o comando que a prova.

Duas armadilhas dominam esta classe de tarefa:

1. **Relatório de status antigo do projeto mente por omissão.** Ele descreve o
   repo de semanas atrás. Nunca repita um achado dele sem reverificar — num caso
   real ele afirmava "auditoria exigida pelo PRD não está implementada" e a
   auditoria estava implementada (signals gravando `AuditLog`).
2. **"Existe uma revisão para implantar" é uma suposição, não um fato.** Antes de
   discutir infra, prove QUAL revisão o deploy publicaria.

Não é code review de diff (`requesting-code-review`), nem retrospectiva (`retro`):
o objeto aqui é o repositório inteiro contra os planos do produto.

## Passo 1 — Qual revisão seria implantada? (bloqueador de tudo)

Na raiz do repo (`cd` primeiro — ver §6 de `windows-agent-file-editing`):

```bash
git rev-parse --abbrev-ref HEAD
git status --porcelain
git log -1 --format='%h %ci %s' HEAD
git log --oneline HEAD..origin/master        # o que este branch NÃO tem
git log --oneline origin/master..HEAD        # o que só este branch tem
git diff --stat HEAD origin/master
git diff --diff-filter=A --name-only HEAD origin/master   # só existe em origin/master
git diff --diff-filter=D --name-only HEAD origin/master   # só existe em HEAD
git log --all --oneline -- <caminho>         # onde o arquivo nasceu
git cat-file -e <rev>:<caminho> && echo SIM || echo NAO   # presença por revisão
```

Detalhes de leitura e receitas em `references/git-divergence-forensics.md`.

Sinais de alarme que aparecem de verdade:

- **trabalho só no working tree** (dezenas de modificados + untracked): não é
  reproduzível nem auditável — nenhum commit o contém;
- **branch baseado num master velho**: `git merge-base --is-ancestor <base> origin/master`
  diz SIM, e ainda assim faltam N commits. O branch tem a feature nova e NÃO tem
  as fases anteriores (sem `+not-found`, sem componentes de feedback, sem o
  harness de QA). "Tem a Fase 6" ≠ "tem as Fases 1–5";
- **duas implementações do mesmo domínio em branches diferentes**: ache com
  `git log --all -- <caminho do domínio>`; cada linha pode ter seu próprio
  arquivo de teste. Decidir qual fica ANTES de mergear, e trazer os testes da que
  perder.

Antes de propor merge, liste os arquivos que vão conflitar:
`git diff --name-only HEAD origin/master` filtrando as telas/`_layout.tsx`/
`permissions.py`/`api.ts` que ambos os lados tocaram.

## Passo 2 — O que está verde, medido AGORA

```bash
cd backend && python -m pytest -q 2>&1 | grep -E "passed|failed" | tail -3
cd mobile  && npm run typecheck
cd backend && python manage.py makemigrations --check --dry-run
DJANGO_DEBUG=false DJANGO_SECRET_KEY=<valor-de-teste> python manage.py check --deploy
```

Leitura correta dos resultados:

- pegue a **linha de resumo** do pytest (`1 failed, 80 passed`), não o `tail` cru;
- `makemigrations --check --dry-run` → `No changes detected` = nenhuma migração
  pendente (diga isso, é um verde que vale);
- `check --deploy` com `DEBUG=false` retornando **só** `security.W009`
  (SECRET_KEY) significa que o endurecimento de produção já está no settings —
  HSTS, cookies secure, `SECURE_SSL_REDIRECT`, `nosniff`, `X_FRAME_OPTIONS`,
  `SECURE_PROXY_SSL_HEADER`. Reporte isso explicitamente; é exatamente o tipo de
  item que o relatório antigo dá como faltante.

## Passo 3 — Teste vermelho: regressão ou fixture podre?

Cheque a hipótese barata primeiro: **fixture com data fixa que a lógica filtra
por `>= now - N`**. Caso real: teste criava evento em `20/09/2026`, view filtrava
`start_at__gte=timezone.now() - timedelta(days=1)`, execução em `24/09` → lista
vazia, `assert [] == ['Culto de celebração']`. Verde no dia em que foi escrito,
apodreceu sozinho.

- `grep -n "20[0-9][0-9]-" <arquivo de teste>` antes de culpar o código;
- conserto: `timezone.now() + timedelta(days=2)` no lugar do literal;
- reporte como **"fixture podre, não regressão"** — muda a prioridade do achado e
  evita caçar fantasma no código.

## Passo 4 — Costuras de deploy (o que o código precisa ter)

Cada linha é um grep com **controle positivo** (passo 6):

| Alvo | O que caracteriza lacuna |
|---|---|
| runtime | `gunicorn`/`uvicorn` ausente do requirements; `CMD ["python","manage.py","runserver",...]` no Dockerfile |
| compose | só o de dev; `5432:5432` exposta; sem arquivo `.pilot`/`.prod` |
| boot do container | `migrate && seed_mvp && runserver` — o seed de demonstração roda a cada deploy e viola a DoD "não apresentar dados fictícios como reais" |
| health | nenhum `/health/` (planos de piloto quase sempre exigem) |
| banco gerenciado (Neon/RDS) | `SSLMODE` e `CONN_MAX_AGE` ausentes em `settings.py` e `.env.example` |
| segredos | `.env.example` com `DJANGO_SECRET_KEY=change-me`, sem bloco de produção |
| storage | disco efêmero do container para uploads → exigir S3/R2 + URL assinada |
| backup | script existe? agendado? com alerta? restauração testada? |
| runbooks | deploy/rollback e backup/restore em `docs/` |
| CI | `manage.py check` sem `--deploy` não prova nada de produção |

## Passo 5 — Confrontar com o plano do PRÓPRIO projeto

Abra a seção de **entregáveis** e a de **critérios de aceite** do plano (ex.:
`## 11. Entregáveis esperados`, `## 8. Critérios de aceite`, `## 13. Definition of
Done`) e marque **item por item**: existe / não existe / parcial — com o comando
ou `arquivo:linha` que prova. Isso transforma "acho que falta" em lista fechada,
que é o que o usuário quer ler.

- Liste também os requisitos de segurança/LGPD do PRD (ex.: `## 13. Requisitos de
  Segurança e LGPD`) separando **o que tem lastro** (auditoria, URLs assinadas,
  HTTPS no Django) do **que não tem** (retenção de comprovantes, consentimento,
  backup agendado).
- Confronte o **escopo**: telas placeholder para domínios fora do MVP contradizem
  planos que dizem "não criar apenas shells de navegação" / "itens sem
  implementação devem ser ocultados ou exibidos como 'Em breve'". Reporte como
  decisão de produto, não como bug.

## Passo 6 — Provar AUSÊNCIA com controle positivo

Busca que falha em silêncio vira "não existe" no seu relatório. Ao afirmar
ausência (`sem /health/`, `sem gunicorn`):

- inclua no MESMO comando uma busca por algo que você **sabe** existir (controle
  positivo). Se o controle não casar, a busca está quebrada — não o alvo;
- se `search_files` voltar 0 resultados num caminho que você sabe existir, repita
  com caminho **relativo à raiz do repo** antes de concluir ausência
  (`windows-agent-file-editing` §6);
- presença por revisão: `git cat-file -e <rev>:<caminho> && echo SIM || echo NAO`.

## Formato do relatório (preferência do usuário)

- PT-BR, **texto puro para terminal**, sem tabelas markdown pesadas.
- Estrutura que funcionou: (1) o que está verde, com números medidos; (2) o
  vermelho e a causa raiz; (3) **BLOQUEADOR principal**; (4) checklist do plano
  existente/ausente; (5) requisitos de segurança/LGPD; (6) escopo; (7) o que fazer
  em ordem numerada — Etapa 0 consolidar → Etapa 1 adaptar → Etapa 2 provisionar.
- Comece cada achado pelo comando ou `arquivo:linha` que o prova.
- Feche com o próximo passo concreto **e pergunte** se é para começar. Auditoria
  não autoriza mexer no repo: nada de merge, commit ou remoção por conta própria.
- Lixo untracked (`tmp/`, diretórios de anexos de outro agente): **reporte, não
  remova** — o gate de consentimento nega `rm -rf` e a negativa derruba a linha
  inteira (`windows-agent-file-editing` §5).

## Pitfalls

1. Repetir número de relatório antigo sem reverificar — sempre rode e confira.
2. Concluir que um branch está completo porque tem a feature mais nova: confira as
   fases anteriores arquivo por arquivo.
3. Tratar `--diff-filter=D` sem checar a direção: `D` = existe no primeiro commit
   e não no segundo. Quase levou a "origin/master deletou o app de conteúdo",
   quando o certo era "o branch adicionou e nunca mergeou".
4. Chamar fixture apodrecida de regressão de código (ou o inverso).
5. Confundir "0 resultados de busca" com ausência comprovada.
6. Propor merge sem listar os arquivos que vão conflitar.
7. **Ensaiar a stack de piloto no MESMO projeto do compose de dev.** O arquivo de
   CI do piloto costuma adicionar um `db` descartável (`postgres:16` + `tmpfs`)
   para o ensaio; se o nome de projeto for o mesmo do dev, esse serviço colide com
   o container `db` do dev (volume nomeado, dados reais) e o `up -d db` o recria —
   troca-se banco com dados por banco vazio. Ensaiar sempre com projeto próprio e
   porta própria: `docker compose -p moriah-piloto -f docker-compose.pilot.yml -f
   docker-compose.ci.yml --env-file .env.pilot up -d --build`, com
   `PILOT_PORT=8090` (a 8000 é do dev). Antes de subir, `docker ps` para ver o que
   já está publicado no host.

## Arquivos de apoio

- `references/git-divergence-forensics.md` — receitas de git para descobrir o que
  cada revisão contém, com o significado exato de cada filtro.
- `references/moriah-app-audit-2026-09-24.md` — achados da auditoria do moriah_app
  (4 linhas divergentes, lacunas do piloto Oracle+Neon) e como reverificar.
