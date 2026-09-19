#!/usr/bin/env python3
"""Puxa o catalogo do GitHub para a copia local (degrau 2).

A rede acontece AQUI, e so aqui. A M0 continua offline: ela le o arquivo
que este script deixou no disco. Foi a condicao para o catalogo em nuvem
nao quebrar a promessa de consulta barata (D16).

Usa ETag: rodar de novo sem mudanca no remoto nao baixa nada.

Uso:
    python3 scripts/sincronizar.py [--remoto <url-base>] [--destino <pasta>]

Padrao do remoto: $MODULEX_REMOTO, senao o catalogo publico do metodo.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _comum import raiz_do_repo, rel  # noqa: E402

REMOTO_PADRAO = "https://raw.githubusercontent.com/bittencourtthulio/modulex-catalogo/main/docs/modulos"
DESTINO_PADRAO = ".expx/modulex/docs/modulos"


def baixar(url: str, etag: str | None) -> tuple[bytes | None, str | None]:
    pedido = urllib.request.Request(url, headers={"User-Agent": "modulex-sincronizar"})
    if etag:
        pedido.add_header("If-None-Match", etag)
    try:
        with urllib.request.urlopen(pedido, timeout=20) as resposta:
            return resposta.read(), resposta.headers.get("ETag")
    except urllib.error.HTTPError as erro:
        if erro.code == 304:
            return None, etag
        raise


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--remoto", default=os.environ.get("MODULEX_REMOTO", REMOTO_PADRAO))
    ap.add_argument("--destino", default=DESTINO_PADRAO)
    ap.add_argument("--com-espelhos", action="store_true",
                    help="baixa tambem os MODULO.md espelhados (a M1 pode fazer sob demanda)")
    args = ap.parse_args(argv)

    raiz = raiz_do_repo()
    destino = raiz / args.destino
    destino.mkdir(parents=True, exist_ok=True)
    marcas_caminho = destino / ".etags.json"
    marcas = json.loads(marcas_caminho.read_text()) if marcas_caminho.is_file() else {}

    arquivos = ["modulos.json", "INDICE.md", "LACUNAS.md"]
    baixados, iguais = [], []
    for nome in arquivos:
        url = f"{args.remoto.rstrip('/')}/{nome}"
        try:
            conteudo, etag = baixar(url, marcas.get(nome))
        except (urllib.error.URLError, OSError) as erro:
            print(f"  ! {nome}: {erro}")
            if nome == "modulos.json":
                print("\nmodulex: sincronizacao falhou. A copia local anterior continua valendo —")
                print("catalogo velho e problema da M3, e rede fora nunca bloqueia (regra 11).")
                return 1
            continue
        if conteudo is None:
            iguais.append(nome)
            continue
        (destino / nome).write_bytes(conteudo)
        if etag:
            marcas[nome] = etag
        baixados.append(nome)

    if args.com_espelhos:
        try:
            dados = json.loads((destino / "modulos.json").read_text(encoding="utf-8"))
        except (ValueError, OSError):
            dados = {"modulos": []}
        for modulo in dados.get("modulos", []):
            ns, ident = modulo.get("namespace", "publico"), modulo.get("id")
            rel_url = f"mod/{ns}/{ident}/MODULO.md"
            url = f"{args.remoto.rstrip('/')}/{rel_url}"
            try:
                conteudo, etag = baixar(url, marcas.get(rel_url))
            except (urllib.error.URLError, OSError):
                continue
            if conteudo is None:
                iguais.append(rel_url)
                continue
            alvo = destino / rel_url
            alvo.parent.mkdir(parents=True, exist_ok=True)
            alvo.write_bytes(conteudo)
            if etag:
                marcas[rel_url] = etag
            baixados.append(rel_url)

    marcas_caminho.write_text(json.dumps(marcas, indent=2) + "\n", encoding="utf-8")
    print(f"\nmodulex: catalogo sincronizado em {rel(destino)} (degrau 2).")
    print(f"  baixados: {len(baixados)} · sem mudanca: {len(iguais)}")
    if baixados:
        print("  " + ", ".join(baixados[:8]))
    print("  a M0 volta a ser offline a partir daqui.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
