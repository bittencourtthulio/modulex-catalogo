#!/usr/bin/env python3
"""Publica um MODULO.md no catalogo, via PR.

O PR e o gate humano. Nao e obstaculo inventado: e o caminho de menor
resistencia do GitHub, entao e o unico que ninguem pula (D16).

Ordem, e ela importa:
  1. gate de publicacao, LOCAL, antes de qualquer push
  2. validacao do contrato
  3. espelho no catalogo + reindexacao
  4. branch, commit, PR

O passo 1 antes do 3 e deliberado: push protection do GitHub bloqueia no
remoto, mas a essa altura o segredo ja saiu da maquina.

Uso:
    python3 scripts/publicar.py <MODULO.md> --catalogo <pasta-do-repo-do-catalogo>
                                [--namespace publico] [--confirmar]

Sem --confirmar nada e enviado. Publicacao e irreversivel.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import gate_publicacao  # noqa: E402
import reindexar  # noqa: E402
import validar_modulo  # noqa: E402
from _comum import ler_frontmatter, rel  # noqa: E402


def passo(numero: int, titulo: str) -> None:
    print(f"\n[{numero}] {titulo}")


def executar(*args: str, cwd: Path) -> tuple[int, str]:
    r = subprocess.run(list(args), cwd=str(cwd), capture_output=True, text=True, check=False)
    return r.returncode, (r.stdout + r.stderr).strip()


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("modulo")
    ap.add_argument("--catalogo", required=True, help="pasta do repositorio do catalogo")
    ap.add_argument("--namespace", default=None, help="padrao: o do frontmatter")
    ap.add_argument("--confirmar", action="store_true")
    args = ap.parse_args(argv)

    origem = Path(args.modulo)
    if not origem.is_file():
        print(f"publicar: {args.modulo} nao existe.")
        return 2
    catalogo = Path(args.catalogo).resolve()
    if not (catalogo / "docs" / "modulos" / "modulos.json").is_file():
        print(f"publicar: {args.catalogo} nao parece o repositorio do catalogo.")
        return 2

    fm, _ = ler_frontmatter(origem.read_text(encoding="utf-8"))
    ident = str(fm.get("id", "")).strip()
    ns = args.namespace or str(fm.get("namespace", "")).strip()
    if not ident or not ns:
        print("publicar: o MODULO.md precisa de `id` e `namespace` no frontmatter.")
        return 2

    passo(1, "gate de publicacao (local, antes de qualquer push)")
    if gate_publicacao.main([str(origem)]):
        print("\npublicar: bloqueado pelo gate. Nada foi enviado.")
        return 1

    passo(2, "validacao do contrato")
    if validar_modulo.main([str(origem)]):
        print("\npublicar: o MODULO.md nao cumpre o contrato. Nada foi enviado.")
        return 1

    if str(fm.get("status")) == "candidato":
        print("\n  nota: status `candidato`. Ele sobe buscavel e marcado, e NAO e")
        print("  injetavel na F3 nem na F6 ate alguem fechar as secoes de julgamento.")

    destino = catalogo / "docs" / "modulos" / "mod" / ns / ident / "MODULO.md"
    branch = f"modulo/{ns}-{ident}-{date.today().isoformat()}"

    passo(3, f"espelho em {rel(destino, catalogo)} e reindexacao")
    if not args.confirmar:
        print("  (seco) copiaria o MODULO.md, rodaria reindexar --escrever,")
        print(f"  abriria a branch `{branch}` e o PR no catalogo.")
        print("\npublicar: nada foi enviado. Rode com --confirmar quando estiver pronto.")
        print("Publicacao e irreversivel: repositorio publico e forkado, indexado e cacheado.")
        return 0

    destino.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(origem, destino)
    if reindexar.main(["--escrever", "--catalogo", str(catalogo / "docs" / "modulos")]):
        print("publicar: reindexacao falhou.")
        return 1

    passo(4, "branch, commit e PR")
    for args_git in (
        ("git", "checkout", "-b", branch),
        ("git", "add", "docs/modulos"),
        ("git", "commit", "-m", f"modulo: {ns}/{ident}"),
    ):
        codigo, saida = executar(*args_git, cwd=catalogo)
        if codigo:
            print(f"  falhou em `{' '.join(args_git)}`:\n{saida}")
            return 1

    corpo = (
        f"Modulo `{ns}/{ident}`.\n\n"
        f"**Problema:** {fm.get('problema')}\n"
        f"**Status:** {fm.get('status')}\n"
        f"**Procedencia:** {fm.get('extraido_de')} · verificado em {fm.get('verificado_em')} "
        f"contra {fm.get('verificado_contra')}\n\n"
        "O CI confere contrato, gate e indice. O que este PR pede ao humano e o que "
        "nenhum script decide: se as 14 secoes dizem a verdade, e se o que NAO cobre "
        "esta honesto.\n"
    )
    codigo, saida = executar("gh", "pr", "create", "--fill=false", "--title",
                             f"modulo: {ns}/{ident}", "--body", corpo, cwd=catalogo)
    print(saida)
    return 0 if codigo == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
