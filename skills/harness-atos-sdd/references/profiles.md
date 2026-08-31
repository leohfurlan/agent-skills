# Perfis do Harness Atos SDD

Escolher o menor perfil que sustente os riscos reais. Os perfis são cumulativos: `standard` inclui `minimal`; `high-risk` inclui `standard`.

## Minimal

Usar para bibliotecas, protótipos duráveis e aplicações pequenas sem dados sensíveis ou efeitos externos relevantes.

Garantir:

- uma fonte canônica de desenvolvimento neutra de ferramenta;
- adaptadores para descoberta por agentes;
- vocabulário e decisões arquiteturais;
- gates rápidos e completos configuráveis;
- autorizações separadas para versionamento e entrega;
- estados distintos para configurado, executado e aprovado.

Arquivos-base:

- `DEVELOPMENT.md`, `AGENTS.md`, `CLAUDE.md`, `CONTEXT.md`;
- `.harness/project.yaml`, `.harness/gates.json`;
- `.harness/scripts/run_gates.py`;
- `docs/agents/authorization.md`;
- `docs/adr/0000-decision-template.md`.

## Standard

Usar como padrão para produtos mantidos continuamente, com múltiplas features, CI, integrações ou mais de um colaborador/agente.

Acrescentar:

- PRD canônico com IDs estáveis e dependências;
- decisões e pendências separadas;
- trio de feature `contract.md`, `spec.md`, `plan.md`;
- evidência ligada à versão avaliada;
- baseline para falhas preexistentes;
- revisão proporcional ao risco e revalidação após integração.

Arquivos adicionais:

- `docs/product/PRD.md`;
- `docs/product/decisions-and-open-questions.md`;
- `docs/specs/README.md`;
- `docs/specs/_template/{contract,spec,plan}.md`;
- `docs/agents/evidence.md`;
- `.harness/schemas/evidence.schema.json`.

## High-risk

Usar quando o produto envolve dinheiro, autorização, isolamento entre clientes, migrations destrutivas, dados regulados, efeitos fiscais, infraestrutura crítica ou operações externas difíceis de reverter.

Acrescentar:

- matriz de risco que determine revisão e gates;
- isolamento explícito de banco, filas, portas, credenciais e arquivos temporários;
- revisão independente sobre versão congelada;
- plano de rollback e recuperação;
- política de dados e redaction;
- reconciliação antes de repetir efeitos externos incertos;
- gate de arquitetura e testes do mecanismo real quando doubles não provarem a garantia.

Arquivos adicionais:

- `docs/agents/risk-review.md`;
- `docs/agents/runtime-isolation.md`;
- `docs/agents/release-and-rollback.md`;
- `docs/agents/data-policy.md`;
- `docs/specs/_template/review.md`;
- `.harness/architecture-rules.json`.

High-risk não significa executar todos os gates em toda alteração. Classificar o risco da mudança e aplicar os controles correspondentes.
