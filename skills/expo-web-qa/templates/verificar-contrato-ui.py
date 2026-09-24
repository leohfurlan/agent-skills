"""Verificador ESTATICO do contrato tela x check de aceite (esqueleto reutilizavel).

Complementa o Playwright: le os arquivos alterados e afirma que a interface
oferece rota, rotulo e payload que o check procura — util quando o servidor do
app pode estar fora do ar, e como contraparte barata (1 s) da execucao real.

Roda em ~1 s, nao toca em rede e nao escreve no banco. NAO substitui a suite nem
o aceite end-to-end: rotule-o como verificacao ad-hoc.

Uso:
    python hermes-verify-contrato-ui.py   # exit 0 passa, 1 falha (git-bash/CI)

Como adaptar (3 pontos):
  1. RAIZ do projeto.
  2. ARQUIVOS: caminho relativo -> apelido usado nas assertivas.
  3. Liste os pares (apelido, trecho esperado) do SEU contrato — o que o check de
     aceite procura na tela (rotulos por regex, rotas, campos do payload).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

RAIZ = Path(r"C:\Projetos TI\<projeto>")

ARQUIVOS = {
    "rota_lista": "mobile/app/schedule-admin.tsx",
    "rota_detalhe": "mobile/app/schedule-admin/[id].tsx",
    "layout": "mobile/app/_layout.tsx",
    "nav": "mobile/src/navigation.ts",
    "criar": "mobile/src/screens/ScheduleCreateScreen.tsx",
    "lista": "mobile/src/screens/ScheduleAdminScreen.tsx",
    "detalhe": "mobile/src/screens/ScheduleAdminDetailScreen.tsx",
    "api": "mobile/src/services/api.ts",
    "check": "tools/qa/checks/fase4.mjs",
}

FALHAS: list[str] = []


def ler(apelido: str) -> str:
    return (RAIZ / ARQUIVOS[apelido]).read_text(encoding="utf-8")


def sem_comentarios(fonte: str) -> str:
    """Assertiva de invariante vale para CODIGO, nao para a prosa que o explica.

    Sem isto, o proprio comentario que documenta a armadilha derruba a checagem
    (caso real: `${BASE}/api/...` citado num comentario explicativo).
    """
    sem_bloco = re.sub(r"/\*.*?\*/", "", fonte, flags=re.S)
    return "\n".join(l for l in sem_bloco.splitlines() if not l.strip().startswith("//"))


def confere(descricao: str, condicao: bool, detalhe: str = "") -> None:
    print(f"[{'OK   ' if condicao else 'FALHA'}] {descricao}{f' -> {detalhe}' if detalhe else ''}")
    if not condicao:
        FALHAS.append(descricao)


def main() -> int:
    fontes = {apelido: ler(apelido) for apelido in ARQUIVOS}

    print("-- rotas e guarda --")
    confere("rota da lista aponta para a tela de gestao", "ScheduleAdminScreen" in fontes["rota_lista"])
    confere("rota do detalhe aponta para a tela de detalhe", "ScheduleAdminDetailScreen" in fontes["rota_detalhe"])
    confere(
        "guarda por capacidade cobre o prefixo com id na URL",
        "PREFIXOS_DE_GESTAO" in fontes["layout"] and "startsWith" in fontes["layout"],
    )
    confere(
        "guarda explica em PT-BR sem renderizar a lista",
        "Acesso restrito" in fontes["layout"] and "coordenação" in fontes["layout"],
    )
    confere("item de menu existe e exige a capacidade", "schedule-admin" in fontes["nav"])

    print("-- rotulos que o check de aceite procura --")
    # (arquivo, trecho literal do rotulo) — mantenha em paridade com os regex do check
    rotulos = [
        ("lista", "Nova escala"),
        ("criar", "Salvar como rascunho"),
        ("detalhe", "Publicar"),
        ("detalhe", "Cancelar escala"),
        ("detalhe", "Adicionar integrante"),
        ("detalhe", "Confirmar escalação"),
    ]
    for apelido, rotulo in rotulos:
        confere(f"rotulo presente: {rotulo}", rotulo in fontes[apelido], f"arquivo={apelido}")

    print("-- payload e contrato da API --")
    confere("criacao envia o campo de escopo e nasce como rascunho", 'submit("draft")' in fontes["criar"])
    confere("cliente HTTP expoe patch e delete", "patch:" in fontes["api"] and "delete:" in fontes["api"])
    confere(
        "check fala com a API (:8000) e nao com o BASE do app (:8081)",
        "API_BASE" in fontes["check"] and "${BASE}/api/" not in sem_comentarios(fontes["check"]),
    )

    print()
    print(f"FALHAS: {'nenhuma' if not FALHAS else ', '.join(FALHAS)}")
    return 1 if FALHAS else 0


if __name__ == "__main__":
    sys.exit(main())
