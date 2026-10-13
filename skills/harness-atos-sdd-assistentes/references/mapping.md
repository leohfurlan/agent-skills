# Mapeamento skills (leohfurlan/agent-skills) → papéis

Fonte: github.com/leohfurlan/agent-skills, branch master, commit 8b514b3 (24/09/2026).

| Papel | Skills principais | Uso |
| --- | --- | --- |
| Assistente central (orquestrador) | harness-atos-sdd (adaptada), ask-matt, handoff, find-skills, retro | Rotear pedidos, escolher perfil, distribuir etapas, consolidar entrega/autorização |
| VP de produto (cada produto) | to-prd, grill-me / grilling / grill-with-docs, domain-modeling, to-specs, harness-atos-sdd (etapas 1–2) | PRD com IDs estáveis, decisões vs. pendências, CONTEXT.md/ADR, priorização por ondas |
| Docs | domain-modeling, grill-with-docs, research, harness-atos-sdd (adoção/adaptadores) | Manter DEVELOPMENT.md/AGENTS.md/CLAUDE.md, CONTEXT, ADRs, specs |
| Marketing & Social | research, to-prd (leitura) | Pesquisa em fontes primárias; consumir PRD para mensagens. Harness pouco aplicável |
| UX/UI | prototype (UI.md), expo-web-qa, codebase-design (leitura) | Protótipos descartáveis, QA web de apps Expo, aceite de UI contra contrato |
| Comercial | to-prd (leitura), research | Feedback de cliente → propostas no PRD (como proposta, não decisão) |
| Code Review | code-review, harness-atos-sdd (etapa 5/review.md), codebase-design, improve-codebase-architecture | Revisão Standards + Spec sobre commit congelado; veredito accepted/changes-required/decision-required |
| Cybersecurity | harness-atos-sdd perfil high-risk (data-policy, runtime-isolation, risk-review), code-review, git-guardrails-claude-code (conceito) | Matriz de risco, política de dados, isolamento, segredos |
| Suporte & Operações | diagnosing-bugs, silvia-agent, research | Diagnóstico com loop de reprodução; triagem de incidentes; reconciliação de efeito externo |
| DevOps | deploy-readiness-audit, harness-atos-sdd (gates/CI, release-and-rollback), resolving-merge-conflicts, windows-agent-file-editing (se Windows) | Prontidão de deploy, forense de branches, gates reais, rollback |
| Implementação (via clone autorizado) | implement, implement-spec, to-specs, diagnosing-bugs | Fatias pequenas com teste red primeiro e evidência |

Não aplicáveis diretamente: claude-handoff (dispara agente de fundo do Claude), git-guardrails-claude-code (hooks do Claude Code — só o conceito), migrate-to-shoehorn, scaffold-exercises, setup-matt-pocock-skills (configuração de repo, só com aval), skill-creator (gera openai.yaml/Codex; útil só como referência de formato), loop-me.

Perfil sugerido por produto (a confirmar com o usuário): emissão fiscal/NFS-e multi-tenant → high-risk (efeito fiscal, tenancy); demais → standard até prova de risco maior.
