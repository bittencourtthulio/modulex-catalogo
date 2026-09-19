#!/usr/bin/env python3
"""Registra uma busca sem resultado como issue de lacuna no catalogo.

O LACUNAS.md local e cego: so enxerga o que este projeto procurou. A issue
e compartilhada, e a reacao de quem tambem procurou vira voto. Em alguns
meses, a fila de extracao esta priorizada por demanda real — e publica.

Regra que sustenta isso: catalogo inalcancavel NAO registra lacuna. Isso
aqui so roda quando a busca chegou ao catalogo e ele nao tinha (D15).

Uso:
    python3 scripts/lacuna_issue.py "emitir nota fiscal de servico" [--confirmar]

Sem --confirmar, so mostra o que faria: abrir issue em repositorio publico
e acao para fora, e acao para fora se confirma antes.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _comum import normalizar  # noqa: E402

REPO_PADRAO = "bittencourtthulio/modulex-catalogo"


def gh(*args: str) -> tuple[int, str]:
    try:
        r = subprocess.run(["gh", *args], capture_output=True, text=True, check=False)
    except FileNotFoundError:
        return 127, "gh nao encontrado. Instale o GitHub CLI ou registre no LACUNAS.md."
    return r.returncode, (r.stdout or r.stderr).strip()


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("termo", nargs="+")
    ap.add_argument("--repo", default=os.environ.get("MODULEX_CATALOGO_REPO", REPO_PADRAO))
    ap.add_argument("--confirmar", action="store_true")
    args = ap.parse_args(argv)

    termo = " ".join(args.termo).strip()
    titulo = f"lacuna: {termo}"

    codigo, saida = gh("issue", "list", "--repo", args.repo, "--label", "lacuna",
                       "--state", "open", "--limit", "100",
                       "--json", "number,title,reactionGroups")
    existentes = []
    if codigo == 0:
        try:
            existentes = json.loads(saida or "[]")
        except ValueError:
            existentes = []

    alvo = normalizar(termo)
    igual = next(
        (i for i in existentes
         if normalizar(i["title"].removeprefix("lacuna:")) == alvo), None,
    )
    parecidas = [
        i for i in existentes
        if i is not igual and any(t in normalizar(i["title"]) for t in alvo.split() if len(t) > 3)
    ]

    print()
    if igual:
        numero = igual["number"]
        print(f"Ja existe issue de lacuna #{numero}: {igual['title']}")
        print("Acao: somar um voto (reacao +1) — demanda repetida e o que prioriza a extracao.")
        if args.confirmar:
            c, s = gh("api", f"repos/{args.repo}/issues/{numero}/reactions",
                      "-f", "content=+1", "--silent")
            print("  voto somado." if c == 0 else f"  falhou: {s}")
        else:
            print("  (seco — rode com --confirmar para votar)")
    else:
        print(f"Nenhuma issue de lacuna para: {termo}")
        if parecidas:
            print("  Parecidas, confira antes de duplicar:")
            for i in parecidas[:5]:
                print(f"    #{i['number']} {i['title']}")
        corpo = (
            f"Busca da M0 que terminou em `NAO EXISTE`.\n\n"
            f"**Termo procurado:** {termo}\n\n"
            "Dois ramos possiveis, e distinguir e trabalho manual que vale a pena:\n\n"
            "- termo repetido **sem** modulo -> candidato a extracao (M2)\n"
            "- termo repetido **com** modulo -> faltava sinonimo na secao 2 de um "
            "modulo que ja existe. Corrigir la e mais barato que extrair\n\n"
            "Some um :+1: se voce tambem procurou isto e nao achou."
        )
        print("Acao: abrir issue no repositorio PUBLICO " + args.repo)
        if args.confirmar:
            c, s = gh("issue", "create", "--repo", args.repo, "--title", titulo,
                      "--body", corpo, "--label", "lacuna")
            print(f"  {s}" if c == 0 else f"  falhou: {s}")
        else:
            print("  (seco — rode com --confirmar para abrir)")
            print(f"\n--- titulo ---\n{titulo}\n--- corpo ---\n{corpo}")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
