# Forense de divergência de branches

Objetivo: responder, com prova, **o que exatamente seria implantado** — e o que
ficaria de fora. Tudo roda da raiz do repo (comece o comando com `cd <raiz>`).

## O conjunto de comandos

```bash
git rev-parse --abbrev-ref HEAD
git status --porcelain | wc -l                 # quanto trabalho vive só no disco
git log -1 --format='%h %ci %s' HEAD           # data do topo do branch atual
git log -1 --format='%h %ci %s' origin/master  # data do topo do master
git branch -a -vv                              # quem está atrás de quem

git log --oneline HEAD..origin/master          # commits que o branch NÃO tem
git log --oneline origin/master..HEAD          # commits exclusivos do branch
git diff --stat HEAD origin/master             # tamanho do buraco (arquivos/linhas)

git diff --diff-filter=A --name-only HEAD origin/master   # só existe em origin/master
git diff --diff-filter=D --name-only HEAD origin/master   # só existe em HEAD

git merge-base --is-ancestor <base> origin/master && echo SIM || echo NAO
git log --all --oneline -- <caminho/do/dominio>           # onde o arquivo nasceu
git cat-file -e <rev>:<caminho> && echo SIM || echo NAO    # presença por revisão
git show <rev>:<caminho> | head -40                        # conteúdo naquela revisão
```

## Como ler cada resultado

**`--diff-filter=A` / `--diff-filter=D`** comparam `HEAD` (primeiro argumento) com
`origin/master` (segundo). As letras descrevem o segundo em relação ao primeiro:

- `A` (added) → arquivo existe **em origin/master e não em HEAD**;
- `D` (deleted) → arquivo existe **em HEAD e não em origin/master**.

Pitfall real: ler `D` como "origin/master deletou isso". O correto, no caso do
moriah_app, era "o branch adicionou e nunca mergeou". Sempre confirme com
`git cat-file -e origin/master:<caminho>` antes de escrever a conclusão.

**`git merge-base --is-ancestor <base> origin/master` = SIM** não significa que o
branch está atualizado. Significa apenas que a base é ancestral. O branch pode ser
`base + 1 commit` e ainda assim estar N commits atrás:

```
40ebc25 (16/09 11:18) ──┬─ 16 commits ─────────────► 4219d40 origin/master (17/09 18:46)
                        └─ 407dff5 (18/09 10:09) ← branch atual
```

Leitura: o branch tem 1 commit que o master não tem, e **não tem 16** que o master
tem. O commit do branch é mais NOVO em data e mais VELHO em conteúdo. Não conclua
"está à frente" por data.

**`git log --all -- <caminho>`** é o detector de implementações paralelas. Se dois
hashes não relacionados aparecem para o mesmo arquivo, existem duas
implementações do mesmo domínio em branches diferentes. Compare-as
(`git diff --stat <A> <B> -- <dir do domínio>`) — uma pode ter testes que a outra
não tem.

**`git status --porcelain`** com dezenas de linhas `??` e ` M`: nada disso está em
commit algum. Consequência a declarar no relatório: não é reproduzível, não é
auditável, e um `git stash`/`checkout` de outro agente pode varre-lo.

## Arquivos-chave que denunciam base velha

Compare a presença por revisão de itens que as fases anteriores entregam. No caso
real, o branch "com a Fase 6" não tinha nenhum destes (todos existiam em
origin/master):

- `mobile/app/+not-found.tsx`
- `mobile/src/navigation.ts`
- `mobile/src/components/Feedback.tsx`
- `tools/qa/` (harness de aceite)
- `docs/qa/fase-*.md`

Comando de varredura rápida:

```bash
for f in mobile/app/+not-found.tsx mobile/src/navigation.ts tools/qa/run.mjs; do
  printf '%-45s ' "$f"
  git cat-file -e origin/master:"$f" 2>/dev/null && echo "origin/master SIM" || echo "origin/master NAO"
done
```

## Listar conflitos antes de propor merge

```bash
git diff --name-only HEAD origin/master | grep -E "(_layout|theme|api|permissions|Screen|ContentScreen)"
```

Ambos os lados de uma divergência costumam tocar exatamente: `_layout.tsx`,
`theme.ts`, `services/api.ts`, `accounts/permissions.py`, a tela do domínio em
disputa. Cite-os nominalmente na ordem de trabalho — merge sem essa lista é
surpresa garantida.
