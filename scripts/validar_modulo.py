#!/usr/bin/env python3
"""Valida um MODULO.md contra o contrato do modulex.

O contrato deixa de ser norma escrita e vira teste que reprova merge.
Roda na maquina de quem extrai e em GitHub Actions no PR do catalogo.

Uso:
    python3 scripts/validar_modulo.py <caminho/MODULO.md> [...]
    python3 scripts/validar_modulo.py --todos          # varre o catalogo

Exit code 0 sem erro, 1 com erro. Aviso nao reprova.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _comum import (  # noqa: E402
    CHAVES_FRONTMATTER,
    NAO_DETERMINADO,
    SCHEMA,
    SECOES,
    SECOES_SEM_ND,
    STATUS_VALIDOS,
    Relatorio,
    e_data_iso,
    fatiar_secoes,
    ler_frontmatter,
    normalizar,
    raiz_do_repo,
    rel,
    resolver_catalogo,
    tem_caminho_absoluto,
    vencido_em,
)

# Campos que a esteira preenche sozinha. O resto exige julgamento — e e por
# isso que candidato nao e modulo (regra 13).
SECOES_MECANICAS = {7, 8, 10, 12, 14}
SECOES_DE_JULGAMENTO = {2, 3, 5, 6, 11, 13}

# O contrato declara explicitamente quais secoes aceitam NAO DETERMINADO
# como valor. As de julgamento nao estao aqui: secao de julgamento aberta
# e candidato, nao modulo ativo.
ND_PERMITIDO = {7, 8, 9, 10, 12}

# Para cobrar a contrapartida na secao 13 sem exigir que ela cite o numero
# da secao — modulo real descreve a lacuna em prosa, nao por indice.
PALAVRA_DA_SECAO = {
    2: ("sinonimo", "busca", "termo"),
    3: ("fatia",),
    5: ("decisao", "escopo"),
    6: ("stack", "dependencia"),
    7: ("pre requisito", "requisito", "conta", "token"),
    8: ("esforco", "faixa", "tempo"),
    9: ("plano", "fase", "gate"),
    10: ("artefato", "codigo pronto", "inventario"),
    11: ("falha", "armadilha", "cadeia"),
    12: ("erro", "codigo"),
}


def valores_nd(texto: str) -> bool:
    """NAO DETERMINADO usado como VALOR, nao mencionado em prosa.

    Distingue `| nucleo | **NAO DETERMINADO** | - |` (valor) de
    "sem observacao real o campo e NAO DETERMINADO" (prosa sobre a regra).
    """
    for linha in texto.splitlines():
        crua = linha.strip()
        if not crua:
            continue
        if crua.startswith("|"):
            celulas = [c.strip().strip("*`_ ") for c in crua.strip("|").split("|")]
            if any(c == NAO_DETERMINADO for c in celulas):
                return True
            continue
        if crua.strip("*`_ .:-") == NAO_DETERMINADO:
            return True
    return False


def validar(caminho: Path, rep: Relatorio) -> None:
    onde = rel(caminho)
    texto = caminho.read_text(encoding="utf-8")
    fm, corpo = ler_frontmatter(texto)

    # --- frontmatter -----------------------------------------------------
    if not fm:
        rep.erro("frontmatter", onde, "arquivo sem frontmatter expx-schema v1.")
        return

    for chave in CHAVES_FRONTMATTER:
        if chave not in fm:
            rep.erro(
                "chave-omitida",
                f"{onde}:frontmatter",
                f"`{chave}` ausente. No expx-schema v1 a chave nunca e omitida — "
                f"sem valor, use {NAO_DETERMINADO} ou lista vazia.",
            )

    if fm.get("schema") != SCHEMA:
        rep.erro("schema", f"{onde}:frontmatter", f"schema deve ser `{SCHEMA}`.")
    if fm.get("kind") != "modulo":
        rep.erro("kind", f"{onde}:frontmatter", "kind deve ser `modulo`.")

    status = str(fm.get("status", ""))
    if status not in STATUS_VALIDOS:
        rep.erro(
            "status",
            f"{onde}:frontmatter",
            f"status `{status}` invalido. Use um de {', '.join(STATUS_VALIDOS)}.",
        )

    ident = str(fm.get("id", ""))
    if not ident or ident != normalizar(ident).replace(" ", "-"):
        rep.erro("id", f"{onde}:frontmatter", "id deve ser slug minusculo sem acento.")
    if "/" in ident:
        rep.erro(
            "id-com-namespace",
            f"{onde}:frontmatter",
            "o namespace mora na chave `namespace`, nao dentro do `id` (D18).",
        )

    ns = str(fm.get("namespace", ""))
    if not ns or ns != normalizar(ns).replace(" ", "-"):
        rep.erro(
            "namespace",
            f"{onde}:frontmatter",
            "namespace deve ser slug minusculo sem acento (`publico` ou o slug da org).",
        )

    for chave in ("verificado_em",):
        if not e_data_iso(fm.get(chave)):
            rep.erro("data", f"{onde}:frontmatter", f"`{chave}` deve ser data ISO AAAA-MM-DD.")

    for chave in ("problema", "verificado_contra", "extraido_de"):
        valor = str(fm.get(chave, "")).strip()
        if not valor:
            rep.erro("vazio", f"{onde}:frontmatter", f"`{chave}` nao pode ser vazio.")
        elif valor == NAO_DETERMINADO and chave in ("problema", "extraido_de"):
            rep.erro(
                "nd-proibido",
                f"{onde}:frontmatter",
                f"`{chave}` nao aceita {NAO_DETERMINADO} — regra 5 (procedencia) e "
                "secao 1 (chave de busca).",
            )

    if not fm.get("stack_essencial"):
        rep.aviso(
            "stack-essencial-vazia",
            f"{onde}:frontmatter",
            "coluna essencial vazia: todo modulo tem alguma exigencia do terceiro.",
        )
    if not fm.get("stack_herdada"):
        rep.aviso(
            "stack-herdada-vazia",
            f"{onde}:frontmatter",
            "coluna herdada vazia e suspeita — quase todo modulo extraido carrega "
            "convencao da casa de origem, e nao enxerga-la e o caminho mais curto "
            "para injeta-la (regra 3).",
        )

    # --- secoes ----------------------------------------------------------
    secoes = fatiar_secoes(corpo)
    for numero, titulo in SECOES:
        if numero not in secoes:
            rep.erro(
                "secao-ausente",
                f"{onde}:secao {numero}",
                f"secao {numero} ({titulo}) nao existe. As 14 sao obrigatorias; "
                f"sem fonte, o valor e {NAO_DETERMINADO} — a secao nunca some.",
            )
            continue
        conteudo = secoes[numero].strip()
        if not conteudo:
            rep.erro("secao-vazia", f"{onde}:secao {numero}", f"secao {numero} ({titulo}) vazia.")
            continue
        if numero in SECOES_SEM_ND and valores_nd(conteudo):
            rep.erro(
                "nd-proibido",
                f"{onde}:secao {numero}",
                f"secao {numero} nao aceita {NAO_DETERMINADO}: sem ela o modulo nao e "
                "buscavel (1), nao declara suas bordas (4) ou nao e rastreavel (14).",
            )

    # regra 7: o "nao cobre" nunca fica vazio.
    if 4 in secoes:
        corpo4 = normalizar(secoes[4])
        if "nao cobre" not in corpo4:
            rep.erro(
                "nao-cobre",
                f"{onde}:secao 4",
                "a secao 4 nao declara o que NAO cobre (regra 7). Modulo que nao declara "
                "suas bordas produz plano que descobre o buraco na metade da execucao.",
            )

    # secao 6: o frontmatter tem que refletir o corpo. Um frontmatter mais
    # pobre que a propria secao 6 e o defeito silencioso — o indice e
    # derivado dele, e quem consulta sem abrir o MODULO.md ve menos do que
    # o modulo sabe.
    if 6 in secoes:
        # Por coluna, nunca pelo total: uma coluna curta compensada por outra
        # longa passa no total e esconde o defeito. Foi o que aconteceu no
        # nfse-municipal — 5 essenciais declarados para 7 descritos, com a
        # coluna herdada partida em 12 para 8.
        linhas6 = secoes[6].splitlines()
        # O corte e no TITULO da subsecao, nunca numa linha qualquer que
        # contenha "herdad": um item essencial do nfse-municipal diz
        # "com o namespace herdado", e cortar ali parte a tabela ao meio.
        corte = next(
            (
                i for i, l in enumerate(linhas6)
                if l.lstrip().startswith("#") and "herdad" in normalizar(l)
            ),
            len(linhas6),
        )
        for chave, trecho, rotulo in (
            ("stack_essencial", linhas6[:corte], "essencial"),
            ("stack_herdada", linhas6[corte:], "herdada"),
        ):
            linhas = [l for l in trecho if l.strip().startswith("|")]
            itens = max(0, len([l for l in linhas if not set(l) <= set("|- ")]) - 1)
            declarados = len(fm.get(chave) or [])
            if itens and declarados < itens:
                rep.aviso(
                    "frontmatter-mais-pobre-que-a-secao-6",
                    f"{onde}:frontmatter",
                    f"a coluna {rotulo} da secao 6 descreve {itens} item(ns) e "
                    f"`{chave}` declara {declarados}. O indice deriva do "
                    "frontmatter: quem consulta sem abrir o MODULO.md veria menos "
                    "do que o modulo sabe.",
                )

        corpo6 = normalizar(secoes[6])
        if "essencial" not in corpo6 or "herdad" not in corpo6:
            rep.erro(
                "duas-colunas",
                f"{onde}:secao 6",
                "a secao 6 precisa separar essencial ao problema x herdado do sistema "
                "de origem (regra 3). Modulo sem essa separacao injeta convencao alheia.",
            )

    # todo NAO DETERMINADO tem contrapartida na secao 13.
    com_nd = sorted(n for n, txt in secoes.items() if n != 13 and valores_nd(txt))
    if str(fm.get("esforco", "")).strip() == NAO_DETERMINADO and 8 not in com_nd:
        com_nd = sorted({*com_nd, 8})
    lacunas = normalizar(secoes.get(13, ""))
    for numero in com_nd:
        pistas = PALAVRA_DA_SECAO.get(numero, ())
        if pistas and not any(p in lacunas for p in pistas):
            rep.erro(
                "nd-sem-lacuna",
                f"{onde}:secao {numero}",
                f"a secao {numero} tem {NAO_DETERMINADO} como valor e a secao 13 nao "
                f"menciona nada sobre {pistas[0]}. Todo campo nao verificavel entra nas "
                "lacunas, com o que seria preciso para fecha-lo.",
            )

    if 13 in secoes and len(secoes[13].strip()) < 80:
        rep.aviso(
            "secao-13-magra",
            f"{onde}:secao 13",
            "a secao 13 e o ativo do modulo. Curta demais costuma significar resumo "
            "de documentacao — e resumo de documentacao nao vale o custo de manter.",
        )

    # --- candidato x modulo (regra 13) -----------------------------------
    abertas = [n for n in sorted(SECOES_DE_JULGAMENTO) if n in secoes and valores_nd(secoes[n])]
    if status == "candidato":
        rep.aviso(
            "candidato",
            onde,
            "status `candidato`: buscavel e marcado, nao injetavel na F3 nem na F6 "
            "(regra 13). "
            + (f"Secoes de julgamento ainda abertas: {abertas}." if abertas else
               "Nenhuma secao de julgamento aberta — pronto para promover a `ativo`."),
        )
    elif status == "ativo":
        for numero in abertas:
            rep.erro(
                "ativo-com-julgamento-aberto",
                f"{onde}:secao {numero}",
                f"status `ativo` com a secao {numero} em {NAO_DETERMINADO}. Secao de "
                "julgamento aberta e candidato, nao modulo ativo (regra 13). As secoes "
                f"{sorted(ND_PERMITIDO)} aceitam {NAO_DETERMINADO}; as de julgamento nao.",
            )

    # --- vencimento (regra 8) --------------------------------------------
    if e_data_iso(fm.get("verificado_em")) and vencido_em(str(fm["verificado_em"])):
        rep.aviso(
            "vencido",
            onde,
            f"verificado_em {fm['verificado_em']} passou do prazo de contrato (D8). "
            "Modulo desatualizado e pior que modulo nenhum: produz plano confiante "
            "e errado. Rode a M3.",
        )

    # --- regra transversal ------------------------------------------------
    for numero, linha in enumerate(texto.splitlines(), start=1):
        if tem_caminho_absoluto(linha):
            rep.erro(
                "caminho-absoluto",
                f"{onde}:{numero}",
                "caminho absoluto em artefato e proibido em todo o metodo.",
            )


def alvos(argv: list[str]) -> list[Path]:
    if argv and argv[0] == "--todos":
        raiz = raiz_do_repo()
        pasta, _ = resolver_catalogo(raiz)
        achados: list[Path] = sorted((pasta / "mod").rglob("MODULO.md")) if pasta else []
        achados += sorted(raiz.glob("exemplos/MODULO.*.md"))
        return achados
    return [Path(a) for a in argv]


def main(argv: list[str]) -> int:
    caminhos = alvos(argv)
    if not caminhos:
        print("uso: validar_modulo.py <MODULO.md> [...] | --todos")
        return 2
    rep = Relatorio(f"validar_modulo — {len(caminhos)} arquivo(s)")
    for caminho in caminhos:
        if not caminho.is_file():
            rep.erro("inexistente", str(caminho), "arquivo nao encontrado.")
            continue
        validar(caminho, rep)
    return rep.imprimir()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
