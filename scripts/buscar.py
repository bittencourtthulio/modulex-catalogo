#!/usr/bin/env python3
"""M0 — consulta por problema em linguagem natural.

Le APENAS o modulos.json (D5). Nunca clona repositorio de modulo, nunca
abre MODULO.md, nunca toca a rede. A operacao mais frequente da skill tem
que ser barata; se encarecer, ninguem usa e a skill morre.

Busca lexical, sem dependencia e sem modelo. A secao 2 do contrato
(sinonimos em pt, en, fornecedores e termos da casa) existe justamente
para isto funcionar. Vetor so entra quando as issues de lacuna mostrarem
busca errando por vocabulario — e ai entra como arquivo commitado, nao
como banco.

Uso:
    python3 scripts/buscar.py "atender cliente por whatsapp"
"""

from __future__ import annotations

import math
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _comum import carregar_json, normalizar, resolver_catalogo, vencido_em  # noqa: E402

# Peso por campo: o problema vale mais que o sinonimo, que vale mais que a
# stack. E a ordem de busca de references/00-consulta.md.
PESOS = {"problema": 3.0, "fatia_problema": 2.0, "sinonimo": 2.0, "cobre": 1.0, "stack": 0.5}

VAZIAS = {
    "de", "da", "do", "das", "dos", "a", "o", "as", "os", "e", "em", "no", "na",
    "para", "por", "com", "um", "uma", "que", "the", "of", "to", "for", "with", "and",
}


def fichar(modulo: dict) -> list[tuple[str, str]]:
    """(campo, texto) — o indice invertido em miniatura."""
    campos: list[tuple[str, str]] = [("problema", str(modulo.get("problema", "")))]
    sin = modulo.get("sinonimos", {}) or {}
    for grupo in ("pt", "en", "fornecedores", "casa"):
        campos += [("sinonimo", str(t)) for t in sin.get(grupo, [])]
    for fatia in modulo.get("fatias", []) or []:
        campos.append(("fatia_problema", str(fatia.get("problema", ""))))
        campos.append(("cobre", str(fatia.get("cobre", ""))))
    for chave in ("stack_essencial", "stack_herdada"):
        campos += [("stack", str(t)) for t in modulo.get(chave, []) or []]
    return campos


def termos(texto: str) -> list[str]:
    return [t for t in normalizar(texto).split() if t and t not in VAZIAS and len(t) > 1]


def pontuar(consulta: list[str], modulo: dict) -> tuple[float, list[str]]:
    ponto, casaram = 0.0, []
    campos = fichar(modulo)
    for termo in consulta:
        melhor, onde = 0.0, ""
        for campo, texto in campos:
            alvo = normalizar(texto)
            if not alvo:
                continue
            if termo in alvo.split():
                valor = PESOS[campo]
            elif len(termo) >= 4 and termo in alvo:
                valor = PESOS[campo] * 0.6
            else:
                continue
            if valor > melhor:
                melhor, onde = valor, texto
        if melhor:
            ponto += melhor
            casaram.append(onde)
    # normaliza pelo tamanho da consulta: 2 de 2 termos vale mais que 2 de 9.
    if consulta:
        ponto *= math.sqrt(len(casaram) / len(consulta))
    return ponto, list(dict.fromkeys(casaram))[:4]


def main(argv: list[str]) -> int:
    if not argv:
        print('uso: buscar.py "problema em linguagem natural"')
        return 2
    consulta = termos(" ".join(argv))

    pasta, degrau = resolver_catalogo()
    if degrau == 0:
        print(
            "\nmodulex: catalogo nao alcancavel a partir deste projeto.\n"
            "Procurei, nesta ordem:\n"
            "  1. $MODULEX_CATALOGO        (variavel nao definida ou caminho inexistente)\n"
            "  2. .expx/modulex/docs/modulos/   (nao existe)\n"
            "  3. docs/modulos/                 (nao existe)\n\n"
            "Seguindo sem modulo. O sprintx planeja do zero, como sempre planejou.\n"
            "Para ligar o catalogo: defina MODULEX_CATALOGO, rode `npx expxdev init`,\n"
            "ou sincronize com `python3 scripts/sincronizar.py`.\n"
            "Isto NAO e NAO EXISTE: nao registra lacuna.\n"
        )
        return 0

    try:
        dados = carregar_json(pasta / "modulos.json")
    except (ValueError, OSError) as erro:
        print(f"\nmodulex: modulos.json ilegivel no degrau {degrau} ({erro}).")
        print("Trate como catalogo ausente. Reparar e M2/M3, nao M0.\n")
        return 0

    modulos = dados.get("modulos", [])
    if not modulos:
        print("\nmodulex: catalogo existe e esta vazio. Nada a consultar — a M2 o enche.\n")
        return 0

    notas = sorted(
        ((*pontuar(consulta, m), m) for m in modulos),
        key=lambda t: t[0],
        reverse=True,
    )
    achados = [(p, c, m) for p, c, m in notas if p >= 1.5]

    print()
    if not achados:
        print(f'NAO EXISTE — nenhum modulo para "{" ".join(argv)}".')
        print("Registre a busca no LACUNAS.md (ou abra a issue de lacuna) e siga sem modulo.")
        print("  python3 scripts/lacuna_issue.py \"" + " ".join(argv) + "\"")
    for ponto, casaram, modulo in achados[:5]:
        marca = ""
        if modulo.get("status") == "candidato":
            marca = "  [CANDIDATO — buscavel, NAO injetavel na F3/F6]"
        elif modulo.get("status") == "obsoleto":
            marca = "  [OBSOLETO]"
        print(f"EXISTE: `{modulo['id']}` ({ponto:.1f}){marca}")
        print(f"  problema: {modulo.get('problema')}")
        fatias = modulo.get("fatias", []) or []
        for fatia in fatias:
            print(
                f"    · {fatia.get('slug')} ({fatia.get('tipo')}) — "
                f"esforco: {fatia.get('esforco')}"
            )
            print(f"      NAO cobre: {fatia.get('nao_cobre')}")
        if casaram:
            print(f"  casou por: {'; '.join(casaram[:3])}")
        if vencido_em(str(modulo.get("verificado_em", ""))):
            print(
                f"  AVISO — verificacao vencida (verificado_em "
                f"{modulo.get('verificado_em')}). Modulo desatualizado e pior que "
                "modulo nenhum: produz plano confiante e errado. Rode a M3."
            )
        print(f"  pre-requisitos bloqueantes: {modulo.get('pre_requisitos_bloqueantes')}")
        print()

    if len(achados) > 1:
        print("Mais de um modulo serve. O modulex lista e cala: a escolha e do")
        print("sprintx (F2/F3), com o stackx na mesa (regra 1).\n")

    print(
        f"Catalogo: {pasta.as_posix().split('/')[-2] + '/' + pasta.name} (degrau {degrau}) "
        f"· {len(modulos)} modulo(s) · atualizado_em {dados.get('atualizado_em')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
