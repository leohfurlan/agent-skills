# Verificação ad-hoc de relatórios: o que deu errado e por quê

Registro do caso que originou o Passo 8 do SKILL.md (relatório de paridade app × mockup, 338 linhas, ~10 afirmações quantitativas). O relatório tinha **4 números errados** e a verificação os pegou antes da entrega. Serve como checklist de onde a contagem costuma mentir.

## Correções que a verificação forçou

| Afirmação publicada | Valor real | Causa raiz |
|---|---|---|
| "15 arquivos de rota" | **13** (`_layout` + 12 rotas) | contagem por `find`/leitura de saída truncada em vez de `os.walk` por extensão |
| "21 chamadas de `Alert.alert`" | **14** | número de memória, nunca contado pelo parser |
| cobertura mobile "37,3 %" | **41,5 % (100/241)** | agregado contaminado por captura inválida (ver abaixo) |
| "3.682 linhas" | **3.741** (`wc -l` em `src/ + app/`) | `sum(1 for _ in open(f))` conta uma linha a mais que `wc -l` em arquivos terminados por nova linha |
| "onze telas desktop e quinze mobile sem rota" | **15 desktop / 16 mobile** | recálculo manual sobre uma tabela que já tinha sido corrigida |

Nenhuma conclusão qualitativa mudou — só os números. É exatamente por isso que a checagem vale: o erro fica na manchete, não na análise.

## O erro mais caro: capturar o estado errado antes de comparar

A varredura por URL direta de `/song/<id>` (sem o parâmetro obrigatório `scheduleId`) fez o app chamar `/me/schedules/undefined/` → 404 → a tela exibiu a página de erro HTML do Django. O diff de texto contra o frame do mockup então deu **0 de 16 strings presentes**, e esse zero entrou no agregado como se fosse "tela não implementada".

Capturando o mesmo fluxo **pela navegação real** (clicar no card da escala → "Ver detalhes da música"), a tela rende 1/16 e o detalhe da escala 9/30 — bem diferente de 0. Regra: antes de publicar um `presentes = 0`, confirme que o texto capturado não é uma página de erro ou um estado diferente do que você acha que testou.

## Armadilhas de contagem (vieram do relatório anterior e do script de verificação)

- **Regex de credencial com janela curta**: `"email"[\s\S]{0,600}?set_password` não pega a conta cujo e-mail está ~700 chars acima (caso do admin). Use 1200 e deduplique com `if (!creds[email])`.
- **Casar request com response por `status >= 400`** perde os 201/204 e faz concluir "o clique não fez nada". Registre **request** (com payload) e **response** (com status) e case por URL.
- **`locator.fill()` em `TextInput` do React Native Web** não atualiza o `useState` (o guard de validação dispara e nada é enviado). Só `click()` + `pressSequentially()`.
- **`getByText(...).first()`** pega o título da página em vez do botão; use `getByRole('button', {name})` ou `[role="button"]` + `filter({hasText})`.
- **`node --check` em cada `.mjs`** — vale como checagem de sintaxe dos scripts de QA no relatório de verificação.
- **`rm -rf` é bloqueado** na ferramenta de terminal; use `find dir -delete` / `rm -f` (e evite `rm -rf tmp/node_modules` por reflexo).

## Onde rodar a suíte de testes do projeto

O container do backend **não** tinha pytest instalado (`No module named pytest`), mas o host tinha Django 5.1.10 + pytest e a suíte passou inteira:

```bash
cd backend && python -m pytest -q      # 67 passed, 3 warnings
```

Lição: quando o container falha por falta de dependência de dev, tente o host antes de concluir qualquer coisa sobre o projeto.

## Higiene do artefato de verificação

- Script temporário em `%TEMP%` com prefixo `hermes-verify-`, removido ao final.
- Cópia preservada no diretório de evidência (`output/.../verificar-relatorio.py`) para ser reexecutável.
- Cuidado com subagentes deixando os seus próprios `hermes-verify-*.py` no temp — limpe-os também.
- Checks que dependem de serviço externo (schema da API, banco) entram como **aviso** quando inacessíveis, nunca como "passa".
