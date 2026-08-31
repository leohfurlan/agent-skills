---
name: harness-atos-sdd
description: Criar ou adaptar um harness de desenvolvimento Spec-Driven Development neutro de ferramenta, com instruções para agentes, fontes de verdade, contratos, gates, evidências e autorizações. Usar quando o usuário pedir para iniciar um projeto com o padrão Atos SDD, replicar o harness de outro projeto, estruturar desenvolvimento com agentes ou escolher entre os perfis minimal, standard e high-risk.
---

# Harness Atos SDD

Gerar um harness versionável que transforme decisões de produto em mudanças verificadas sem confundir especificação, implementação, publicação e efeito operacional.

## Preparar

1. Ler as instruções do repositório e localizar fontes existentes de requisitos, domínio, decisões, CI e comandos.
2. Inspecionar o estado Git e preservar alterações alheias. Trabalhar no checkout autorizado; usar worktree isolado quando a política do projeto exigir.
3. Identificar o perfil solicitado. Na ausência de escolha explícita, recomendar `standard` e declarar a suposição antes de escrever.
4. Ler [profiles.md](references/profiles.md) para o perfil escolhido. Ler [adoption.md](references/adoption.md) ao adaptar um repositório que já possua instruções, documentação ou gates.
5. Inventariar fatos descobertos e decisões ainda pendentes. Obter do ambiente os comandos existentes; não inventar lint, testes, banco, tracker ou CI.

Concluir esta etapa quando o perfil, a raiz do projeto, as fontes existentes, os comandos confirmados e os conflitos de arquivos estiverem identificados.

## Planejar sem alterar

Executar o gerador em modo de planejamento:

```text
python -X utf8 "<diretorio-da-skill>/scripts/generate_harness.py" --project-root "<raiz>" --project-name "<nome>" --profile standard
```

Resolver `<diretorio-da-skill>` a partir da localização desta skill. Não presumir que `scripts/` exista na raiz do projeto de destino.

Acrescentar cada comando descoberto com `--fast-command`, `--full-command` ou `--architecture-command`. O gerador apresenta arquivos novos e arquivos preservados; sem `--apply`, não escreve.

Tratar arquivo existente como fonte a integrar, não como obstáculo a apagar. Para `AGENTS.md`, `CLAUDE.md`, documentos canônicos, CI e configurações, comparar responsabilidades e planejar um merge mínimo.

Concluir esta etapa quando o plano explicar o que será criado, preservado e integrado manualmente.

## Gerar a base

Executar novamente com `--apply` após o plano estar coerente:

```text
python -X utf8 "<diretorio-da-skill>/scripts/generate_harness.py" --project-root "<raiz>" --project-name "<nome>" --profile standard --apply
```

O script cria somente caminhos ausentes. Integrar arquivos preservados com edição dirigida e manter:

- `DEVELOPMENT.md` como fonte canônica e neutra de ferramenta;
- `AGENTS.md` e `CLAUDE.md` como adaptadores curtos quando existirem;
- fatos, decisões, propostas e pendências em estados distintos;
- requisitos, contrato, spec e plano com responsabilidades próprias;
- gates configurados a partir de comandos reais;
- commit, push, merge, deploy, migration e efeito operacional como autorizações separadas.

Substituir marcadores `PENDING` apenas com evidência ou decisão do usuário. Um marcador explícito é preferível a uma suposição.

Concluir esta etapa quando todos os arquivos previstos estiverem criados ou conscientemente integrados, sem perda de conteúdo anterior.

## Validar

Executar a validação estrutural:

```text
python -X utf8 "<diretorio-da-skill>/scripts/generate_harness.py" --project-root "<raiz>" --profile standard --validate
```

Depois:

1. Confirmar que os adaptadores apontam para `DEVELOPMENT.md` sem duplicar suas regras.
2. Conferir que os arquivos do perfil e dos perfis herdados existem.
3. Validar JSONs e ausência de marcadores do gerador.
4. Executar somente gates seguros e já autorizados. Registrar configurado, executado, aprovado, falho e bloqueado separadamente.
   Tratar cada comando configurado como código versionado: revisar sua origem antes de usar `run_gates.py --run`.
5. Para `standard` e `high-risk`, verificar que uma feature pode percorrer PRD → `contract.md` → `spec.md` → `plan.md` → evidência.
6. Para `high-risk`, verificar isolamento de runtime, revisão independente, rollback e reconciliação de efeitos externos.

Concluir esta etapa quando a estrutura estiver válida e as limitações de runtime estiverem registradas sem transformar checks não executados em sucesso.

## Entregar

Informar:

- perfil aplicado e razão;
- arquivos criados, preservados e integrados;
- comandos e gates descobertos;
- validações realmente executadas;
- decisões `PENDING` e riscos restantes;
- ações externas não realizadas.

Criar o harness não autoriza commit, push, PR, deploy, migration, criação de recursos externos ou registro global de outras skills.
