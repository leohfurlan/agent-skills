---
name: windows-agent-file-editing
description: Editar arquivos e digitar literais em sessões de agente no Windows (git-bash) sem corromper conteúdo — armadilhas de CRLF, output de ferramenta mascarado (dígitos/senhas viram asteriscos), prefixos de paginação do read_file vazando para o disco e backticks sofrendo command substitution em mensagens de commit. Usar ao editar código em C:\..., gravar testes/configs com literais sensíveis, commitar com git via bash, resolver caminho relativo depois de um `cd` no terminal, ou trabalhar em repositório que outro agente está editando ao mesmo tempo.
---

# Edição de arquivos sob armadilhas de exibição (Windows + agente)

Quatro modos de falha reais desta classe, todos silenciosos: o arquivo fica
"escrito", a sintaxe passa, e o conteúdo está errado. A defesa comum é sempre
a mesma: **verificar por propriedade mensurável (comprimento, contagem), nunca
pelo que a tela mostra**. As seções 1–5 são desse tipo; as 6–7 são armadilhas de
ESTADO da sessão (cwd do terminal, outro agente no mesmo repositório) que fazem
você concluir o errado sobre o arquivo, não sobre o conteúdo dele.

## 1. Output de ferramenta mascara dígitos e segredos

Sequências de dígitos (telefones, cartões) e senhas em resultado de
terminal/read_file/patch aparecem mascaradas na EXIBIÇÃO (`+551****4321`,
`***`), mesmo com o disco correto — e, ao contrário, literais que você digitou
olhando a exibição mascarada entram NO DISCO errados.

- NUNCA copiar literal com dígitos/segredo do output de tool para arquivo ou
  comando. Construir programaticamente: `cel = "+551" + "198765" + "4321"`.
- Verificar por métrica, não por leitura: `len(linha)`, `linha.count('*')`,
  `re.findall(r'"\+55[0-9*]+"', l)` com comprimentos. `grep`/`cat` na tela não
  provam nada nessas linhas.
- Sintoma clássico: asserção de teste `assert x == y` falha com os dois lados
  IDÊNTICOS impressos (um é máscara, o outro literal).
- Vale também para `docker run -e PASSWORD=***`: a senha literalizou `***` e o
  auth falhou com erro críptico. Depois: `ALTER USER ... PASSWORD` via socket
  local (trust) para reconsertar sem redigitar.
- **O mascaramento também dispara no caminho de IDA.** Escrever o esquema de
  autorização colado a uma interpolação de token (o padrão de um header HTTP, numa
  linha só) faz o redator gravar `***` NO ARQUIVO — e o `patch` que iria corrigir
  também recebe `***` na string nova, virando patch no-op silencioso (sem diff).
  Saídas: (a) montar o valor por partes, sem a palavra colada à interpolação —
  `const esquema = ["Bear","er"].join(""); return { Authorization: [esquema, token].join(" ") };`
  — (b) ou gravar a linha por script (`write_file` de um `.py` que faz o
  `re.subn`, depois rodá-lo), fora da sua mensagem.
- Ao ESCREVER esta regra (ou qualquer doc/código que a cite), não digite o exemplo
  com a chave literal do header: monte a chave por partes
  (`const chave = "Author" + "ization"; return { [chave]: esquema + " " + token };`)
  ou escreva a linha por script. O exemplo literal é justamente o que mais se
  corrompe na ida.
- **Não roteie conteúdo de arquivo por output de tool.** Reconstruir um arquivo a
  partir do que uma ferramenta IMPRIMIU (ex.: os dois lados de um conflito lidos
  com `git show :2:<path>` / `:3:<path>` e depois concatenados num script) passa
  pelo redator no caminho de ida: um literal de header/token vira `***` DENTRO do
  arquivo e o Python estoura `SyntaxError: unterminated string literal` só quando
  você roda a suíte. Saídas: use redirecionamento do lado do git
  (`git show <ref>:<path> > <path>`) ou capture dentro do próprio script
  (`subprocess.run([...], capture_output=True)`); depois faça a varredura de
  detecção — `grep -rl '\*\*\*'` nos arquivos versionados (excluindo
  `node_modules`) e `ast.parse`/`tsc` — porque a máscara também pode entrar em
  outra linha sem quebrar a sintaxe.
- **Exibição mascarada ≠ disco corrompido.** Um `grep` de volta pode mostrar
  `***` numa linha que está CORRETA no disco (e `node --check`/`ast.parse` passa).
  Não conserte por leitura: rode o checador de sintaxe e use o resultado como
  veredito — foi o que separou arquivo quebrado de apenas mascarado.
- **Veredito = booleano montado por partes.** Evidência de 24/09/2026 no
  moriah_app: as linhas `export <VAR>="${POSTGRES_...:-...}"` de dois scripts
  apareceram ELIDIDAS (`${POST...iah}`) em `write_file`, `cat` e `grep` — e
  estavam íntegras no disco. O veredito veio de montar o alvo em pedaços e
  perguntar ao Python:

  ```python
  alvo = "${POSTGRES_" + "PASSWORD:-" + "moriah}"
  print(alvo in open(p, encoding="utf-8").read())     # True nos 3 arquivos
  ```

  os pedaços separados na mensagem não disparam o redator, e o booleano impresso
  (True/False) não tem o que mascarar. Só reescreva o arquivo se der `False`.
- **O eco do `write_file`/`patch` ecoa a SUA mensagem, não o disco.** Concluir
  corrupção a partir do corpo ecoado é o erro que fecha o ciclo: a elipse está na
  exibição, o disco tem o literal. Fonte de verdade é o teste booleano acima.

## 2. CRLF quebra patch e replace

Arquivos no repo podem ser CRLF; `patch`/`str.replace` com `\n` puro não
casam (ou casam torto e corrompem blocos vizinhos).

Padrão seguro em `execute_code`:

```python
raw = open(p, encoding="utf-8", newline="").read()
src = raw.replace("\r\n", "\n")
assert old in src, f"NAO CASOU: {old[:70]!r}"   # sempre asserir o match
src = src.replace(old, new)
open(p, "w", encoding="utf-8", newline="").write(src.replace("\n", "\r\n"))
import ast; ast.parse(src)                        # sempre re-parsear
```

- Múltiplos patches sequenciais na MESMA região via ferramenta `patch` se
  corrompem entre si (um come o cabeçalho do próximo). Para N edições na mesma
  área, um script com asserts > N patches encadeados.
- **Patch que dá certo pode apagar a linha seguinte.** Caso real: `old_string`
  terminando em `}) {\n` e `new_string` terminando em `}) {` — o `patch` reportou
  sucesso e a linha `const groups = ...` logo abaixo desapareceu (o CRLF de
  fechamento foi consumido junto). A única pista está no diff devolvido: ele
  mostra um `-` que você não pediu. **Leia o diff de todo patch** e, se aparecer
  remoção não pretendida, releia a região antes de seguir — a continuação do
  trabalho (tsc, teste) foi quem acusou o estrago, duas chamadas depois.
- Se o `patch` responde `Found N matches` para um `old_string` que você julgava
  único, o matcher está quebrando o texto em pedaços. Reduza a âncora para UMA
  linha inequívoca (evite blocos multi-linha com trechos repetidos) e confirme
  pelo diff; não use `replace_all` para "resolver" a ambiguidade.
- Regra de bolso depois de editar bloco: reler a região (ou rodar o checador de
  sintaxe) na MESMA rodada, não só no fim do lote.
- Se um patch falha, NÃO repetir com o mesmo texto: reler a região exata antes.

## 3. read_file devolve `NNN|` — nunca regravar a partir dele

O conteúdo do `read_file` vem prefixado com número de linha (`128|    assert`).
Copiar esse texto para `write_file`/`open().write()` grava os prefixos no disco
e trunca/intercala linhas. Se já aconteceu, recuperar in-place:

```python
import re
limpo = re.sub(r"(?m)^\d+\|", "", open(p, encoding="utf-8").read())
import ast; ast.parse(limpo)
```

Para reescrever um arquivo inteiro, usar `write_file` com conteúdo autoral, ou
transformações programáticas sobre o texto cru (`newline=""`), nunca sobre a
renderização paginada.

## 3.1 Leitura grande volta resumida — releia em blocos antes de editar

Leitura de arquivo grande (a partir de ~20k caracteres) pode voltar só com o
cabeçalho (`read C:\...\Screen.tsx from line 1 (23,583 chars)`), **sem as
linhas**. O modo de falha é silencioso e caro: você acha que leu, e depois
patcha "de memória" — ou conclui que o arquivo está vazio.

- Se você não está vendo o conteúdo, releia em blocos (`limit`/`offset`, ~100
  linhas por chamada) até ter o texto exato das regiões que vai tocar. Ler em
  blocos é barato; patchar no escuro, não.
- Nunca reescrever um arquivo a partir de um resumo de leitura: se a região não
  está visível, releia-a antes.
- Alternativa robusta para N edições no mesmo arquivo: script com
  `assert src.count(velho) == 1` por trecho (ver §2). O assert substitui a
  conferência visual e falha alto em vez de corromper em silêncio.
- Vale também para o inverso: `write_file` de um arquivo longo pode gravar só
  parte do que você imaginou ter enviado — confirme por propriedade mensurável
  (`grep -c` da âncora final, contagem de linhas), não por leitura de tela.
- Para **citar `arquivo:linha`** ou ler um arquivo inteiro com número de linha sem
  paginar, use `search_files(output_mode="content")` com um padrão que case linhas
  de verdade (ex.: `[A-Za-z_]+`) e `limit` alto: ele devolve o conteúdo com os
  números. Com o padrão `.*` a mesma chamada volta só como contagem
  (`-> 103 matches`), sem as linhas — e uma rodada com vários resultados de forma
  idêntica pode elidir todos (dedup). Se voltar sem conteúdo, repita a chamada
  sozinha ou varie o padrão; nunca patch/edite a partir do que você acha que leu.

## 3.2 Assertiva de fonte mente por comentário e por chave de estilo

Verificar invariante de código com `if "248" not in fonte` (ou `"sidebarGroups"
not in fonte`) dá falso positivo/negativo: o valor removido é citado no próprio
docstring que documenta a remoção, e `styles.sidebarGroups` é chave legítima de
`StyleSheet`. Antes de acusar o código, **leia a linha**:

```bash
grep -n "248\|sidebarGroups" mobile/src/screens/HomeScreen.tsx mobile/src/components/Screen.tsx
```

Regras que resolvem: rodar a assertiva sobre o **código sem comentários**
(remover `/* */` e linhas iniciando com `//` ou `*`), mirar **declarações**
(`const sidebarGroups`) em vez de qualquer ocorrência, e usar regex quando o
padrão é regex (`/text\/html/i` não contém o literal `text/html`). Caso real:
4 de 29 assertivas falharam e todas as quatro eram defeito do verificador.

## 4. Backticks em `git commit -m "..."` viram command substitution

`git commit -m "... fixture \`vinculo_de\` ..."` executa `vinculo_de` como
comando (`command not found`) e APAGA o trecho da mensagem no commit. Aspas
duplas não protegem backticks.

- Mensagens de commit com termos técnicos: sem backticks, ou aspas simples no
  shell.
- Padrão recomendado para mensagens multi-linha (comprovado em 10+ commits):
  escrever o texto via `write_file` em `.git/COMMIT_MSG_N.txt` (dentro de .git
  = nunca versionado), `git commit -F .git/COMMIT_MSG_N.txt`, depois `rm`.
  Elimina aspas, backticks e `$` de uma vez — o shell nunca vê a mensagem.
- Após commitar, auditar: `git log --format=%B -1` e conferir se o texto
  sobreviveu. Corrigir com `git commit --amend -m '...'` (aspas simples).
- O mesmo vale para `$`, `\` e `!` em comandos bash com aspas duplas.
- **`python -c "..."` com regex/escape aninhado não sobrevive ao bash.** Um
  `python -c` que precisava de `\\u`, `\\"` e `\\n` juntos morreu com
  `SyntaxError: unterminated string literal` — o shell come uma camada de barras,
  o Python come outra, e o que sobra não fecha aspa. Sintoma idêntico ao das
  linhas acima: falha de PARSING parecendo bug do seu código. Regra: para
  qualquer transformação com `\`, aspas e regex juntos, `write_file` de um `.py`
  e rodar o arquivo (`python script.py args`) — nunca `-c`. Bônus: o script fica
  re-executável quando o mesmo recorte precisa rodar em outro arquivo.
- **Caminho Windows entre aspas duplas no bash**: `stat -c '%y' "C:\Projetos TI\x"`
  faz a barra invertida antes da aspa de fechamento ESCAPAR a aspa e o shell morre
  com `unexpected EOF while looking for matching `"` — a linha inteira não roda,
  inclusive a parte produtiva. Use caminho MSYS (`/c/Projetos TI/moriah_app`) ou
  aspas simples. O sintoma é o mesmo de §5: falha de parsing parecendo falha do
  comando.

## 5. Comando destrutivo negado aborta a LINHA INTEIRA (não só o trecho perigoso)

`rm -rf <dir>` e `find <dir> -exec rm -rf {} +` são negados pelo gate de
consentimento deste ambiente. Duas consequências que enganam:

- A negativa derruba o comando **inteiro**, não apenas o trecho destrutivo.
  `rm -rf tmp/node_modules && node tmp/qa.mjs` → o script produtivo **nunca
  executou**, e a leitura apressada da saída ("sem output", "exit −1") leva à
  conclusão errada de que o script falhou.
- `find <dir> -delete`, usado como alternativa "mais leve", também pode ser
  negado quando aponta para árvores grandes (`__pycache__`, `node_modules`).

Regras práticas:

- Nunca encadear limpeza com trabalho produtivo. Rode o produtivo sozinho e
  primeiro; a limpeza, se necessária, em chamada separada e com `rm -f` sobre
  **caminhos explícitos**.
- Limpeza cosmética (`__pycache__`, caches) que for negada: **não é bloqueio do
  trabalho**. Siga, e diga ao usuário que não limpou — nunca repita nem
  reformule o comando negado (o protocolo proíbe re-tentar a mesma finalidade).
- Se precisar mesmo encadear, coloque o destrutivo por último e nada depois dele.

## 6. Caminho relativo resolve contra o CWD da sessão do terminal

`read_file`/`search_files`/`patch` resolvem caminho relativo contra o diretório
atual da sessão do `terminal`, que PERSISTE entre chamadas. Depois de
`cd backend && python -m pytest -q`, pedir `backend/apps/x/views.py` falha com
`Path not found` (o caminho virou `backend/backend/apps/...`) — e o mesmo vale
para `search_files(path="backend/apps/...")`.

- Comece cada comando de terminal com `cd <raiz do repo>`, ou passe caminho
  absoluto nas ferramentas de arquivo. É uma linha e elimina a classe.
- Sintoma que engana: a MESMA chamada funcionou 3 chamadas antes e agora diz que
  o arquivo não existe. Não é o arquivo — é o cwd.
- **Busca que volta 0 resultados não prova ausência.** Caso real:
  `search_files(pattern="USE_S3", path="C:\Projetos TI\moriah_app")` devolveu
  `{"total_count": 0}` para um padrão que existe no repo; a MESMA busca com
  caminho relativo à raiz (`path="backend"`) achou o arquivo. Antes de escrever
  "não existe" (num relatório de auditoria, sobretudo), repita com caminho
  relativo e inclua na mesma rodada um **controle positivo** — um padrão que você
  sabe existir. Se o controle não casar, quem está quebrada é a busca, não o alvo.
  Mesmo cuidado ao afirmar ausência por `grep` em `terminal`.

## 7. Outro agente escrevendo no MESMO working tree

Sessões paralelas (Codex/Claude/outro Hermes na mesma máquina) editam o mesmo
repositório ao vivo. Sinais que apareceram de verdade:

- a contagem de testes MUDA entre duas execuções da mesma suíte (75 → 91 → 95)
  sem você ter acrescentado nada;
- `git status` ganha arquivos modificados/untracked que você não tocou, no meio
  da sessão — e um commit novo pode surgir (o snapshot do início da sessão já
  não vale: `git log --oneline -3` é a fonte);
- `read_file` devolve "File not found" para um arquivo que existe (reescrita em
  andamento);
- busca/leitura devolve conteúdo ANTERIOR à edição (resultado obsoleto), e você
  "descobre" divergências que já foram resolvidas.

Regras:

- Fique em áreas de arquivo disjuntas da dele. Não edite o arquivo que ele está
  editando: você pode perder a corrida de escrita e derrubar o trabalho dele.
- Não assuma autoria: teste vermelho em arquivo alheio é DELE, em obra. Reporte
  como externo, com evidência (`git status`), em vez de "consertar" ou chamar de
  regressão sua.
- Se um arquivo alheio está quebrado e BLOQUEIA a sua verificação, o conserto
  mínimo (import faltando, por exemplo) é aceitável — anunciado como fora do seu
  escopo, e nunca como refatoração no código dele.
- Antes de concluir qualquer coisa sobre o estado do repo, rode `git status` e
  `git log`; não confie na sua lembrança do começo da sessão.
- Alerta que vale a pena dar ao usuário: trabalho seu não commitado pode ser
  varrido por um `git stash`/`checkout` do outro agente. Ofereça o commit de
  blindagem em vez de decidir sozinho.
- **Identifique quem está escrevendo antes de acusar "alguém".** Sessões vivas no
  state.db (`sessions` com `ended_at IS NULL` + mensagem recente; `source` =
  cli/whatsapp/subagent) e command lines dos processos
  (`Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match '<repo|agente>' }`).
  `process(action="list")` só enxerga os background processes DESTA sessão —
  lista vazia não significa "ninguém rodando". Impressão digital útil: scripts
  temporários com o nome da feature (`tmp/verifica_<feature>.py`, `tmp/fix_*.py`).
- **mtime não é sinal de vida.** Arquivo mantido aberto por processo com escrita
  bufferizada (rollout `.jsonl` de agente, log) pode ter mtime de horas atrás e
  conteúdo atual — comparar mtime para decidir "o outro agente parou" erra feio.
  Use o timestamp DENTRO do conteúdo (ou o timestamp da última mensagem no
  state.db) como sinal de atividade.

## Verificação final da classe

Depois de qualquer lote de edições: `ast.parse`/lint, suíte de testes, e
`git diff` conferindo que as linhas alteradas são as pretendidas — máscaras de
exibição não detectam corrupção no diff; comprimento e contagem sim.
