# Agent Skills

Repositório central das skills pessoais usadas no **Codex e no Claude Code**.

O objetivo é manter uma única fonte das instruções, referências e scripts que orientam os agentes. Uma melhoria desenvolvida em qualquer um deles deve entrar neste repositório e, depois de validada e promovida, ficar disponível para ambos.

## O que é uma skill

Uma skill descreve um fluxo de trabalho reutilizável: quando aplicá-lo, quais informações consultar, quais decisões tomar e como verificar o resultado. Seu ponto de entrada é o arquivo `SKILL.md`, que pode ter referências, scripts e outros recursos de apoio.

Neste repositório há, por exemplo:

- [to-prd](skills/to-prd/SKILL.md): transforma necessidades de produto em requisitos e critérios de aceite.
- [to-specs](skills/to-specs/SKILL.md): transforma requisitos selecionados em especificações, contratos e planos técnicos.
- [diagnosing-bugs](skills/diagnosing-bugs/SKILL.md): orienta a investigação de problemas.
- [code-review](skills/code-review/SKILL.md): orienta a revisão de mudanças.
- [skill-creator](skills/skill-creator/SKILL.md): cria e evolui skills seguindo a política deste repositório.

Compartilhar uma skill significa compartilhar seus arquivos e suas regras. Isso não garante respostas idênticas entre modelos, nem instala ferramentas, conectores ou permissões.

## Princípios

1. **Uma fonte de verdade:** os arquivos mantidos ficam em `skills/<nome>/` neste repositório.
2. **Instalação por vínculos:** as pastas globais dos agentes apontam para a origem estável, sem manter cópias editáveis independentes.
3. **Desenvolvimento isolado:** mudanças são preparadas em uma branch e um worktree separados da instalação em uso.
4. **Validação antes da promoção:** revisar instruções, dependências e comportamento antes de atualizar a versão estável.
5. **Histórico rastreável:** commits registram mudanças; tags identificam versões aprovadas.
6. **Autorização explícita:** criar ou editar uma skill não autoriza automaticamente publicar, fazer push ou promover uma versão.

## Estrutura

```text
agent-skills/
├── README.md
├── .gitignore
└── skills/
    └── <nome-da-skill>/
        ├── SKILL.md
        ├── references/       # Quando necessárias
        ├── scripts/          # Quando necessários
        ├── assets/           # Quando necessários
        └── agents/
            └── openai.yaml  # Metadados específicos do Codex, quando presentes
```

O `SKILL.md` é o ponto de entrada; as demais pastas dependem da necessidade de cada skill. Versionamos os recursos utilizados junto com as instruções. Caches Python são ignorados pelo Git.

## Como o compartilhamento funciona

No ambiente Windows de Leonardo, a origem estável é:

```text
C:/Projetos TI/agent-skills/skills/<nome>/
```

As instalações usam **junctions de diretório por skill**:

| Agente | Entrada global | Origem |
| --- | --- | --- |
| Codex | `C:/Users/Leonardo/.agents/skills/<nome>` | Pasta correspondente neste repositório |
| Claude Code | `C:/Users/Leonardo/.claude/skills/<nome>` | A mesma pasta correspondente |

As pastas globais principais continuam sendo diretórios reais. Skills de sistema, de plugins ou que ainda não foram incorporadas ao repositório permanecem separadas.

Ao editar um arquivo por uma junction, altera-se o arquivo de origem. Portanto, editar pela instalação global também altera a versão em uso: **os vínculos não isolam desenvolvimento**.

### Exceção: skill-creator no Codex

A entrada de sistema do Codex em `C:/Users/Leonardo/.codex/skills/.system/skill-creator/SKILL.md` encaminha a leitura para a [criadora compartilhada](skills/skill-creator/SKILL.md). Não criamos outra entrada de mesmo nome em `.agents/skills`.

No Claude Code, a criadora usa a junction normal.

Atualizações do Codex podem restaurar a entrada de sistema. Nesse caso, é preciso verificar e reaplicar o encaminhamento; a versão personalizada permanece neste repositório.

### O que não é automático

- Clonar este repositório em outra máquina não cria junctions nem configura os agentes.
- Criar uma pasta nova em `skills/` não registra sua entrada global nos dois agentes.
- Fazer push não atualiza um checkout em outra máquina.
- Tags identificam versões, mas não impedem alterações no checkout instalado.
- Os vínculos locais, os backups e a entrada de sistema do Codex ficam fora deste repositório.

O registro dos vínculos e a promoção são operações locais e explícitas. Este repositório ainda não contém um instalador ou uma pipeline automática de releases.

## Fluxo de criação e evolução

### 1. Preparar o desenvolvimento

Use a [skill-creator](skills/skill-creator/SKILL.md) e confira o estado do Git antes de começar.

Crie ou reutilize um worktree deste mesmo repositório, com uma branch dedicada. Desenvolva em `<worktree>/skills/<nome>/`, mantendo os vínculos globais apontados para o checkout estável.

**Trocar de branch no checkout estável não oferece isolamento:** isso também troca os arquivos carregados pelos agentes. Evite editar a mesma skill simultaneamente pelo Codex e pelo Claude.

### 2. Validar e revisar

Verifique:

- Metadados e estrutura da skill.
- Referências e recursos realmente disponíveis.
- Limites de escopo, permissões e ações que exigem aprovação.
- Comportamento em cenários representativos, incluindo erros e casos de borda relevantes.
- Compatibilidade com os dois agentes e suas ferramentas.

Para validar a estrutura de uma skill em desenvolvimento, use o validador incluído na criadora, passando o caminho da skill no worktree:

```powershell
python -X utf8 "C:/Projetos TI/agent-skills/skills/skill-creator/scripts/quick_validate.py" "<worktree>/skills/<nome>"
```

Esse script depende de Python e PyYAML. Ele verifica estrutura e metadados, não comprova a qualidade do comportamento.

Na instalação atual, também é possível validar as fontes com o Claude Code:

```powershell
claude plugin validate "C:/Projetos TI/agent-skills/skills"
```

Para validar uma mudança ainda não promovida, substitua o caminho pelo diretório `skills` do worktree. Valide as fontes reais: o validador do Claude pode ignorar junctions, embora as sessões carreguem seus destinos.

Registre o que foi executado, o resultado e, nas avaliações de comportamento, o modelo e os cenários utilizados. Uma revisão manual não equivale a um teste executado.

### 3. Versionar e promover

Com autorização:

1. Revise o diff e faça commit apenas das mudanças pretendidas.
2. Crie uma tag para a versão aprovada.
3. Atualize o checkout estável com o conteúdo aprovado, preservando alterações locais alheias.
4. Registre os vínculos de skills novas nos dois agentes.
5. Confira os destinos, o conteúdo e a descoberta pelos agentes.
6. Envie os commits e as tags autorizados ao remoto.

Ao substituir uma instalação existente, compare o conteúdo e preserve um backup fora das pastas examinadas pelos agentes. Se houver divergências, resolva-as antes de substituir qualquer diretório.

Uma configuração inicial ou correção direta na instalação ativa é uma exceção que precisa de autorização e deve ser identificada como tal.

## Convenção de versões

Usamos como convenção tags por skill:

| Tipo de mudança | Exemplo |
| --- | --- |
| Correção que preserva o comportamento esperado | `to-specs/v1.0.1` |
| Capacidade nova compatível com o fluxo existente | `to-specs/v1.1.0` |
| Mudança incompatível em entradas, saídas ou fluxo obrigatório | `to-specs/v2.0.0` |

Os números acima são exemplos, não versões já publicadas. A pasta continua com o nome estável, como `skills/to-specs/`; o histórico e as tags ficam no Git.

O retorno a uma versão anterior também deve ser controlado: preservar trabalho pendente, selecionar a revisão aprovada e verificar novamente a instalação. Não sobrescrever alterações locais para fazer rollback.

## Compatibilidade e limites

Priorize instruções portáveis, caminhos relativos para recursos internos e explicações claras de dependências.

Recursos específicos de um agente — como ferramentas MCP, hooks, metadados e comandos próprios — precisam ser identificados e testados no ambiente correspondente. Uma skill voltada a um recurso exclusivo de Claude ou Codex pode estar disponível para ambos sem conseguir executar o mesmo fluxo nos dois.

Não versionar credenciais, tokens, sessões ou dados de produção. Compartilhar instruções não compartilha acessos e não dispensa aprovações.

Preserve os avisos de autoria e as licenças dos recursos incorporados. A presença de uma skill neste repositório não transfere sua autoria nem altera a licença original.

## Estado inicial

Na configuração de 28/08/2026, foram conectadas 25 skills existentes e adicionada a `skill-creator` compartilhada. O Codex reconheceu as 26 skills, o validador do Claude aprovou as fontes e os vínculos foram conferidos por destino e conteúdo.

O fluxo de worktrees, revisão e tags é a política para evolução. Ele não representa uma automação já implementada, nem significa que todas as skills foram testadas funcionalmente nos dois agentes.

## Referências

- [Política da skill-creator deste repositório](skills/skill-creator/SKILL.md)
- [Skills no Codex](https://learn.chatgpt.com/docs/build-skills)
- [Skills no Claude Code](https://code.claude.com/docs/en/skills)
