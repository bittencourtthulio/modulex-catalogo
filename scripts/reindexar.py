#!/usr/bin/env python3
"""Reconstroi o indice do catalogo a partir dos MODULO.md espelhados.

O `modulos.json` e derivado: divergencia entre ele e o `MODULO.md` e
defeito do indice, e o `MODULO.md` manda. Este script e quem garante isso.

Dois modos, de proposito:
  --conferir  (padrao)  so aponta divergencia. E o que roda no PR.
  --escrever            corrige o indice e a tabela do INDICE.md.

O que ele NAO faz: inventar dado de fatia. `cobre`, `nao_cobre` e `esforco`
por fatia sao curadoria da M2 — o script preserva o que ja existe e avisa
quando falta, em vez de preencher com aproximacao tirada do markdown.

Uso:
    python3 scripts/reindexar.py [--conferir|--escrever] [--catalogo <pasta>]
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _comum import (  # noqa: E402
    NAO_DETERMINADO,
    STATUS_VALIDOS,
    Relatorio,
    carregar_json,
    gravar_json,
    ler_frontmatter,
    rel,
    resolver_catalogo,
    vencido_em,
)

# Chave nunca omitida (expx-schema v1). Entrada acrescentada a mao ao
# modulos.json sem uma delas e o defeito mais provavel do indice.
OBRIGATORIAS = (
    "id", "namespace", "problema", "sinonimos", "fatias", "repo",
    "stack_essencial", "stack_herdada", "pre_requisitos_bloqueantes",
    "verificado_em", "verificado_contra", "extraido_de", "status",
)

DERIVADOS = (
    "problema", "repo", "stack_essencial", "stack_herdada",
    "verificado_em", "verificado_contra", "extraido_de", "status", "namespace",
)


def espelhos(pasta: Path) -> list[Path]:
    return sorted((pasta / "mod").rglob("MODULO.md")) if (pasta / "mod").is_dir() else []


def entrada_nova(fm: dict) -> dict:
    return {
        "id": fm.get("id"),
        "namespace": fm.get("namespace"),
        "problema": fm.get("problema"),
        "sinonimos": {"pt": [], "en": [], "fornecedores": fm.get("fornecedores") or [], "casa": []},
        "fatias": [
            {
                "slug": slug,
                "tipo": "obrigatoria" if slug == "nucleo" else "opcional",
                "problema": NAO_DETERMINADO,
                "cobre": NAO_DETERMINADO,
                "nao_cobre": NAO_DETERMINADO,
                "esforco": NAO_DETERMINADO,
            }
            for slug in (fm.get("fatias") or ["nucleo"])
        ],
        "repo": fm.get("repo"),
        "stack_essencial": fm.get("stack_essencial") or [],
        "stack_herdada": fm.get("stack_herdada") or [],
        "pre_requisitos_bloqueantes": [],
        "verificado_em": fm.get("verificado_em"),
        "verificado_contra": fm.get("verificado_contra"),
        "extraido_de": fm.get("extraido_de"),
        "status": fm.get("status"),
    }


def tabela_indice(modulos: list[dict]) -> list[str]:
    linhas = []
    for m in sorted(modulos, key=lambda x: str(x.get("id"))):
        fatias = m.get("fatias") or []
        opcionais = sum(1 for f in fatias if f.get("tipo") == "opcional")
        desc = f"{len(fatias)} (nucleo + {opcionais} opcionais)" if fatias else "0"
        forn = ", ".join((m.get("sinonimos") or {}).get("fornecedores") or []) or "—"
        esf = next((f.get("esforco") for f in fatias if f.get("slug") == "nucleo"), NAO_DETERMINADO)
        linhas.append(
            f"| `{m.get('id')}` | {m.get('problema')} | {desc} | {forn} | "
            f"{esf} | {m.get('verificado_em')} | {m.get('status')} |"
        )
    return linhas


def reescrever_indice(caminho: Path, modulos: list[dict]) -> None:
    """Reescreve SO a tabela e os contadores. A prosa e de humano."""
    texto = caminho.read_text(encoding="utf-8")
    linhas = texto.splitlines()

    inicio = next(
        (i for i, l in enumerate(linhas) if l.startswith("| id |") or l.startswith("| `id`")),
        None,
    )
    if inicio is not None:
        fim = inicio + 2
        while fim < len(linhas) and linhas[fim].startswith("|"):
            fim += 1
        linhas[inicio + 2:fim] = tabela_indice(modulos)

    contagem = {
        "total_modulos": len(modulos),
        "ativos": sum(1 for m in modulos if m.get("status") == "ativo"),
        "candidatos": sum(1 for m in modulos if m.get("status") == "candidato"),
        "obsoletos": sum(1 for m in modulos if m.get("status") == "obsoleto"),
        "vencidos": sum(1 for m in modulos if vencido_em(str(m.get("verificado_em", "")))),
        "atualizado_em": date.today().isoformat(),
    }
    saida, vistas = [], set()
    for linha in linhas:
        chave = linha.split(":")[0].strip() if ":" in linha else ""
        if chave in contagem and chave not in vistas:
            saida.append(f"{chave}: {contagem[chave]}")
            vistas.add(chave)
        else:
            saida.append(linha)
    # chave nunca omitida: `candidatos` pode nao existir ainda no frontmatter.
    if "candidatos" not in vistas:
        for i, linha in enumerate(saida):
            if linha.startswith("ativos:"):
                saida.insert(i + 1, f"candidatos: {contagem['candidatos']}")
                break
    caminho.write_text("\n".join(saida) + "\n", encoding="utf-8")


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--escrever", action="store_true")
    ap.add_argument("--conferir", action="store_true")
    ap.add_argument("--catalogo", default=None)
    args = ap.parse_args(argv)
    escrever = args.escrever and not args.conferir

    pasta = Path(args.catalogo) if args.catalogo else resolver_catalogo()[0]
    if not pasta or not (pasta / "modulos.json").is_file():
        print("reindexar: catalogo nao alcancavel.")
        return 2

    dados = carregar_json(pasta / "modulos.json")
    por_id = {str(m.get("id")): m for m in dados.get("modulos", [])}
    rep = Relatorio(f"reindexar — {rel(pasta)} ({'escrevendo' if escrever else 'conferindo'})")

    vistos = set()
    for caminho in espelhos(pasta):
        fm, _ = ler_frontmatter(caminho.read_text(encoding="utf-8"))
        ident = str(fm.get("id", ""))
        if not ident:
            rep.erro("sem-id", rel(caminho), "espelho sem `id` no frontmatter.")
            continue
        vistos.add(ident)
        if ident not in por_id:
            rep.erro("ausente-no-indice", rel(caminho), f"`{ident}` nao esta no modulos.json.")
            if escrever:
                por_id[ident] = entrada_nova(fm)
                rep.aviso("criado", ident, "entrada criada com fatias em NAO DETERMINADO — "
                                           "`cobre`, `nao_cobre` e `esforco` sao curadoria da M2.")
            continue
        entrada = por_id[ident]
        for chave in DERIVADOS:
            esperado, atual = fm.get(chave), entrada.get(chave)
            if esperado is None or esperado == atual:
                continue
            rep.erro(
                "divergencia",
                f"{ident}:{chave}",
                f"indice diz {atual!r}, MODULO.md diz {esperado!r}. O MODULO.md manda.",
            )
            if escrever:
                entrada[chave] = esperado

    for ident, entrada in por_id.items():
        for chave in OBRIGATORIAS:
            if chave not in entrada or entrada[chave] in (None, ""):
                rep.erro(
                    "chave-omitida",
                    f"{ident}:{chave}",
                    f"`{chave}` ausente ou vazia no indice. No expx-schema v1 a chave "
                    "nunca e omitida — sem valor, NAO DETERMINADO ou lista vazia.",
                )
                if escrever and chave == "namespace":
                    entrada[chave] = "publico"
        if str(entrada.get("status", "")) not in STATUS_VALIDOS:
            rep.erro("status", f"{ident}:status",
                     f"status `{entrada.get('status')}` invalido. Use um de "
                     f"{', '.join(STATUS_VALIDOS)}.")
        if ident not in vistos and espelhos(pasta):
            rep.aviso("sem-espelho", ident, "entrada no indice sem MODULO.md espelhado em "
                                            "`mod/`. A M1 vai ter que buscar no repo do modulo.")
        for fatia in entrada.get("fatias", []) or []:
            if not str(fatia.get("nao_cobre", "")).strip():
                rep.erro("nao-cobre-vazio", f"{ident}:{fatia.get('slug')}",
                         "`nao_cobre` vazio (regra 7). Nunca fica vazio.")

    if escrever:
        dados["modulos"] = [por_id[k] for k in sorted(por_id)]
        dados["atualizado_em"] = date.today().isoformat()
        gravar_json(pasta / "modulos.json", dados)
        indice = pasta / "INDICE.md"
        if indice.is_file():
            reescrever_indice(indice, dados["modulos"])
        print(f"reindexar: {rel(pasta / 'modulos.json')} e INDICE.md atualizados.")
        return 0 if not rep.erros else rep.imprimir() * 0

    return rep.imprimir()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
