# Adoção e integração

Ler ao instalar o harness em um repositório existente ou promover de um perfil para outro.

## Preservar fontes existentes

Mapear cada arquivo atual para uma responsabilidade antes de editar:

| Conteúdo existente | Destino preferido |
| --- | --- |
| Regras permanentes de desenvolvimento | `DEVELOPMENT.md` |
| Ponte específica de ferramenta | `AGENTS.md` ou `CLAUDE.md` |
| Vocabulário do negócio | `CONTEXT.md` |
| Decisão com alternativas e consequências | `docs/adr/` |
| Resultado de produto e critérios observáveis | `docs/product/PRD.md` |
| Interface entre provedor e consumidor | `contract.md` |
| Decisão técnica e estratégia de teste | `spec.md` |
| Ordem e checkpoints | `plan.md` |
| Comando executável | configuração, script ou CI |

Manter uma definição em uma fonte. Usar links para conectar artefatos; não sincronizar cópias por disciplina manual.

## Integrar adaptadores

Manter `AGENTS.md` e `CLAUDE.md` curtos. Apontar para `DEVELOPMENT.md` com condição clara de leitura e preservar apenas detalhes realmente específicos da ferramenta.

Quando um adaptador existente também roteia para documentos especializados, manter esses ponteiros. Remover duplicação somente depois de confirmar que a fonte canônica cobre o mesmo comportamento.

## Descobrir gates

Ler manifests, scripts e CI. Registrar o comando, diretório, pré-requisitos e escopo. Deixar listas vazias quando nenhum comando estiver confirmado.

Classificar cada gate como:

- `discovered`: existe no repositório;
- `proposed`: ainda depende de decisão ou implementação;
- `executed`: foi rodado nesta versão;
- `passed`, `failed` ou `blocked`: resultado observado.

## Evoluir o perfil

Para subir de perfil, executar o gerador primeiro sem `--apply`. Criar apenas os arquivos da nova camada e revisar se decisões anteriores continuam coerentes.

O gerador não altera automaticamente os arquivos controlados já existentes. Em um upgrade, é esperado que `.harness/project.yaml` e `.harness/gates.json` apareçam como `integration-required`, pois ainda registram o perfil anterior. Integrar manualmente o novo `profile` e as listas de comandos, preservando extensões locais; depois executar `--validate` com o perfil novo. Uma validação que falha antes dessa integração é uma proteção, não um upgrade incompleto silencioso.

Reduzir o perfil exige decisão explícita: identificar garantias removidas, consumidores afetados e novo tratamento dos riscos. Não apagar evidências ou histórico para simplificar a estrutura.

## Integrar ao CI

Usar `.harness/scripts/run_gates.py` como runner local e fonte de evidência. Adicionar um adaptador ao CI já usado pelo projeto; não criar uma segunda plataforma de CI por conveniência.

O CI deve gravar saída íntegra e mostrar um resumo. Truncar somente a visualização, nunca a evidência na origem.
