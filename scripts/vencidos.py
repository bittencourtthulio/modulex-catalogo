#!/usr/bin/env python3
"""Lista modulos com verificacao vencida, e opcionalmente abre issue.

D8: prazos por tipo de campo — 6 meses para contrato da API, catalogo de
erros e pre-requisitos; 12 para cadeia de falha, plano, stack e esforco;
24 para problema, sinonimos, fatias e cobertura. O `verificado_em` e a
data MAIS ANTIGA entre os campos, e por isso o prazo cobrado aqui e o de
contrato: e o contrato que quebra o plano.

Modulo desatualizado e pior que modulo nenhum (regra 8). Um cron mensal
transforma "alguem devia revisar" em issue com nome e prazo.

Uso:
    python3 scripts/vencidos.py [--catalogo <pasta>] [--abrir-issue] [--repo <owner/nome>]
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _comum import PRAZOS_DIAS, carregar_json, e_data_iso, resolver_catalogo  # noqa: E402


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalogo", default=None)
    ap.add_argument("--abrir-issue", action="store_true")
    ap.add_argument("--repo", default=os.environ.get("MODULEX_CATALOGO_REPO", ""))
    ap.add_argument("--aviso-previo", type=int, default=30,
                    help="dias antes do vencimento em que o modulo ja aparece")
    args = ap.parse_args(argv)

    pasta = Path(args.catalogo) if args.catalogo else resolver_catalogo()[0]
    if not pasta:
        print("vencidos: catalogo nao alcancavel.")
        return 0

    dados = carregar_json(pasta / "modulos.json")
    hoje = date.today()
    limite = timedelta(days=PRAZOS_DIAS["contrato"])
    linhas = []
    for modulo in dados.get("modulos", []):
        verificado = str(modulo.get("verificado_em", ""))
        if not e_data_iso(verificado):
            linhas.append((modulo, None, "sem data de verificacao valida"))
            continue
        vence = date.fromisoformat(verificado) + limite
        faltam = (vence - hoje).days
        if faltam <= args.aviso_previo:
            estado = "VENCIDO" if faltam < 0 else f"vence em {faltam} dia(s)"
            linhas.append((modulo, vence, estado))

    if not linhas:
        print(f"vencidos: nenhum modulo vencido nem vencendo nos proximos "
              f"{args.aviso_previo} dias.")
        return 0

    print(f"\n{len(linhas)} modulo(s) pedindo M3:\n")
    for modulo, vence, estado in linhas:
        print(f"  · {modulo.get('namespace')}/{modulo.get('id')} — {estado} "
              f"(verificado_em {modulo.get('verificado_em')}"
              + (f", vence {vence}" if vence else "") + ")")
    print("\n  Modulo desatualizado e pior que modulo nenhum: produz plano confiante e")
    print("  errado, e o erro so aparece na execucao — depois de o P4 ja ter encolhido")
    print("  o escopo com base numa faixa de esforco que nao vale mais.\n")

    if args.abrir_issue and args.repo:
        for modulo, vence, estado in linhas:
            chave = f"{modulo.get('namespace')}/{modulo.get('id')}"
            titulo = f"M3: revalidar {chave}"
            achou = subprocess.run(
                ["gh", "issue", "list", "--repo", args.repo, "--search", titulo,
                 "--state", "open", "--json", "number"],
                capture_output=True, text=True, check=False,
            )
            if achou.returncode == 0 and json.loads(achou.stdout or "[]"):
                continue
            corpo = (
                f"`{chave}` esta **{estado}**.\n\n"
                f"- `verificado_em`: {modulo.get('verificado_em')}\n"
                f"- `verificado_contra`: {modulo.get('verificado_contra')}\n"
                f"- prazo de contrato da API: {PRAZOS_DIAS['contrato']} dias (D8)\n\n"
                "A M3 revalida contra a documentacao atual do fornecedor, corrige o que "
                "divergiu, e **avisa quem consumiu o modulo desde a ultima verificacao**.\n\n"
                "Divergencia achada em campo corrige so aquele campo (D14): renovar o "
                "`verificado_em` inteiro sem reverificar o resto e mentir a data."
            )
            subprocess.run(
                ["gh", "issue", "create", "--repo", args.repo, "--title", titulo,
                 "--body", corpo, "--label", "m3"],
                check=False,
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
