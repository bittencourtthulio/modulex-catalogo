#!/usr/bin/env python3
"""Detecta que um trabalho entregue tem cara de modulo e o enfileira.

Este script NAO extrai modulo. Ele enfileira candidato (D17).

A divisao e deliberada: um script sem humano no meio preenche os 14 campos
por inferencia, e campo inventado e pior que modulo inexistente. Entao ele
so escreve o que consegue OBSERVAR — datas reais, arquivos, variaveis de
ambiente, hosts, codigos de erro tratados — e deixa em aberto tudo que
exige julgamento: o que o modulo NAO cobre, o que e essencial x herdado, e
as lacunas descobertas na marra. Essas o humano responde na M2.

A fila e LOCAL e nunca e publicada. Por isso ela pode conter nome de
repositorio, caminho e host de cliente: e evidencia para quem vai extrair,
nao conteudo de catalogo. O que sobe e o MODULO.md, e so ele passa no gate.

Uso:
    python3 scripts/detectar_candidato.py [--desde <ref>] [--slug <slug>] [--quieto]

Saida: .expx/modulex/fila/<slug>.json  (exit 0 mesmo sem candidato —
       hook que falha atrapalha o trabalho de quem esta entregando)
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _comum import NAO_DETERMINADO, SCHEMA, git, gravar_json, raiz_do_repo  # noqa: E402

# SDK de terceiro no gerenciador de pacotes. Lista curta de proposito:
# o sinal forte e o host no codigo, nao o pacote.
SDKS = (
    "stripe", "twilio", "sendgrid", "mailgun", "resend", "postmark", "nodemailer",
    "@aws-sdk", "boto3", "@google-cloud", "firebase", "@supabase", "mercadopago",
    "pagarme", "asaas", "iugu", "gerencianet", "efi", "openai", "anthropic",
    "@slack", "discord.js", "telegraf", "whatsapp", "uazapi", "evolution-api",
    "docusign", "clicksign", "zenvia", "pusher", "algolia", "cloudinary", "s3",
    "nfe", "nfse", "focusnfe", "enotas", "plugnotas",
)

VARIAVEL = re.compile(
    r"(?i)\b([A-Z][A-Z0-9_]{3,})\s*=|process\.env\.([A-Z][A-Z0-9_]{3,})|"
    r"Deno\.env\.get\(\s*[\"']([A-Z][A-Z0-9_]{3,})[\"']|"
    r"os\.environ(?:\.get)?[\[(]\s*[\"']([A-Z][A-Z0-9_]{3,})[\"']"
)
VARIAVEL_DE_TERCEIRO = re.compile(
    r"(?i)(API|TOKEN|SECRET|KEY|WEBHOOK|CLIENT_ID|ACCOUNT|SENDER|PROVIDER|"
    r"ENDPOINT|BASE_URL|MERCHANT|STORE)"
)

HOST = re.compile(r"https?://([a-z0-9][a-z0-9.\-]*\.[a-z]{2,})", re.I)
HOST_INTERNO = re.compile(
    r"(?i)^(localhost|127\.|0\.0\.0\.0|\[::1\]|.*\.local$|.*\.test$|"
    r"(www\.)?(github|npmjs|pypi|developer\.mozilla|w3|schema)\.)"
)

ROTA_WEBHOOK = re.compile(r"(?i)(webhook|/hooks?/|callback|notificacao|notification)")
CODIGO_ERRO = re.compile(
    r"(?i)\b(?:status|statusCode|status_code|code|response\.status)\s*(?:===?|==|!=)\s*(\d{3})\b"
    r"|\bcase\s+(\d{3})\s*:"
)

EXT_CODIGO = {".ts", ".tsx", ".js", ".jsx", ".py", ".sql", ".sh", ".go", ".rb", ".php", ".java"}
EXT_CONFIG = {".env", ".example", ".sample", ".json", ".yml", ".yaml", ".toml"}

# SDK so conta quando esta no manifesto de dependencias. Um `.json` de dados
# que cita "uazapi" nao integra nada — foi assim que a primeira versao deste
# script acusou o proprio repositorio da skill.
MANIFESTOS = {
    "package.json", "requirements.txt", "pyproject.toml", "go.mod",
    "Gemfile", "composer.json", "Cargo.toml", "deno.json", "pubspec.yaml",
}
# `.expx/` e a instalacao do proprio metodo: os scripts do modulex contem,
# por construcao, os padroes que o detector procura. Varre-los seria o
# detector se detectando.
IGNORAR = re.compile(
    r"(?:^|/)(node_modules|\.git|dist|build|\.next|vendor|__pycache__|\.venv|\.expx)/"
)


def arquivos_do_trabalho(raiz: Path, desde: str | None, ignorar: str | None = None) -> list[str]:
    """Os arquivos que este trabalho tocou, pelo git."""
    base = desde
    if not base:
        for ref in ("origin/main", "origin/master", "main", "master"):
            achado = git("merge-base", "HEAD", ref, cwd=raiz)
            if achado:
                base = achado
                break
    if not base:
        return []
    saida = git("diff", "--name-only", "--diff-filter=ACMR", f"{base}...HEAD", cwd=raiz)
    nomes = [n for n in saida.splitlines() if n.strip() and not IGNORAR.search(n)]
    if ignorar:
        extra = re.compile(ignorar)
        nomes = [n for n in nomes if not extra.search(n)]
    return nomes


def janela_do_trabalho(raiz: Path, desde: str | None) -> dict[str, object]:
    """Secao 8: observacao real, nao estimativa.

    O que o git prova e a JANELA DE CALENDARIO entre o primeiro e o ultimo
    commit — nao horas trabalhadas. A distincao vai escrita no proprio
    campo, porque quem le tende a usar como se fosse estimativa (regra 6).
    """
    base = desde or "origin/main"
    intervalo = f"{base}...HEAD" if git("rev-parse", "--verify", base, cwd=raiz) else "HEAD"
    datas = git("log", "--format=%cs", intervalo, cwd=raiz).splitlines()
    datas = sorted(d for d in datas if d.strip())
    if not datas:
        return {"observacao": NAO_DETERMINADO, "origem": "git nao devolveu commits"}
    inicio, fim = datas[0], datas[-1]
    dias = (date.fromisoformat(fim) - date.fromisoformat(inicio)).days + 1
    return {
        "primeiro_commit": inicio,
        "ultimo_commit": fim,
        "dias_de_calendario": dias,
        "commits": len(datas),
        "observacao": f"{dias} dia(s) de calendario, {len(datas)} commits",
        "origem": f"git, {intervalo}",
        "atencao": (
            "janela de calendario, NAO horas trabalhadas e NAO estimativa. "
            "So vira faixa de esforco da secao 8 se alguem confirmar que a "
            "janela corresponde ao trabalho (regra 6)."
        ),
    }


def varrer(raiz: Path, nomes: list[str]) -> dict[str, object]:
    variaveis: set[str] = set()
    hosts: set[str] = set()
    sdks: set[str] = set()
    webhooks: set[str] = set()
    erros: set[str] = set()
    artefatos: dict[str, int] = {}

    for nome in nomes:
        caminho = raiz / nome
        sufixo = caminho.suffix.lower()
        artefatos[sufixo or "(sem extensao)"] = artefatos.get(sufixo or "(sem extensao)", 0) + 1
        if not caminho.is_file() or sufixo not in (EXT_CODIGO | EXT_CONFIG):
            continue
        try:
            texto = caminho.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue

        for grupos in VARIAVEL.findall(texto):
            for nome_var in grupos:
                if nome_var and VARIAVEL_DE_TERCEIRO.search(nome_var):
                    variaveis.add(nome_var)

        if sufixo in EXT_CODIGO or caminho.name.startswith(".env"):
            for host in HOST.findall(texto):
                host = host.lower()
                if not HOST_INTERNO.match(host):
                    hosts.add(host)

        if caminho.name in MANIFESTOS:
            baixo = texto.lower()
            for sdk in SDKS:
                if sdk in baixo:
                    sdks.add(sdk)

        # Rota de webhook e sinal de codigo, nao de prosa nem de dado.
        if sufixo in EXT_CODIGO and (ROTA_WEBHOOK.search(nome) or ROTA_WEBHOOK.search(texto[:4000])):
            webhooks.add(nome)

        for a, b in CODIGO_ERRO.findall(texto):
            codigo = a or b
            if codigo and codigo[0] in "45":
                erros.add(codigo)

    return {
        "variaveis_de_ambiente": sorted(variaveis),
        "hosts_externos": sorted(hosts),
        "sdks_detectados": sorted(sdks),
        "rotas_de_webhook": sorted(webhooks),
        "codigos_de_erro_tratados": sorted(erros),
        "arquivos_por_extensao": dict(sorted(artefatos.items())),
        "total_de_arquivos": len(nomes),
    }


def pontuar(achado: dict[str, object]) -> tuple[int, list[str]]:
    """Confianca de que isto integrou um terceiro. Nunca decide sozinho."""
    pontos, porques = 0, []
    if achado["hosts_externos"]:
        pontos += 3
        porques.append(f"{len(achado['hosts_externos'])} host(s) externo(s) no codigo")
    if achado["sdks_detectados"]:
        pontos += 2
        porques.append(f"SDK de terceiro: {', '.join(achado['sdks_detectados'][:4])}")
    if achado["variaveis_de_ambiente"]:
        pontos += 2
        porques.append(f"{len(achado['variaveis_de_ambiente'])} variavel(is) de credencial")
    if achado["rotas_de_webhook"]:
        pontos += 2
        porques.append("rota de webhook")
    if achado["codigos_de_erro_tratados"]:
        pontos += 1
        porques.append("tratamento explicito de codigo de erro HTTP")
    return pontos, porques


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="enfileira candidato a modulo")
    ap.add_argument("--desde", default=None, help="ref git de inicio (padrao: merge-base com main)")
    ap.add_argument("--slug", default=None, help="slug do trabalho (padrao: nome da branch)")
    ap.add_argument("--saida", default=".expx/modulex/fila", help="pasta da fila, relativa a raiz")
    ap.add_argument("--limiar", type=int, default=4, help="pontos minimos para enfileirar")
    ap.add_argument("--quieto", action="store_true", help="nao imprime nada se nao houver candidato")
    ap.add_argument("--ignorar", default=None,
                    help="regex de caminhos a pular, alem dos ignorados por padrao")
    args = ap.parse_args(argv)

    raiz = raiz_do_repo()
    nomes = arquivos_do_trabalho(raiz, args.desde, args.ignorar)
    if not nomes:
        if not args.quieto:
            print("modulex: nenhum arquivo no intervalo — nada a enfileirar.")
        return 0

    achado = varrer(raiz, nomes)
    pontos, porques = pontuar(achado)
    if pontos < args.limiar:
        if not args.quieto:
            print(f"modulex: sem cara de modulo ({pontos}/{args.limiar} pontos). Nada enfileirado.")
        return 0

    branch = git("rev-parse", "--abbrev-ref", "HEAD", cwd=raiz) or "trabalho"
    slug = args.slug or re.sub(r"[^a-z0-9]+", "-", branch.lower()).strip("-") or "trabalho"

    candidato = {
        "schema": SCHEMA,
        "kind": "modulo_candidato",
        "slug": slug,
        "detectado_em": date.today().isoformat(),
        "confianca": {"pontos": pontos, "limiar": args.limiar, "porque": porques},
        "observado": achado,
        "janela": janela_do_trabalho(raiz, args.desde),
        "secoes_mecanicas": {
            "7_pre_requisitos": achado["variaveis_de_ambiente"],
            "8_esforco": "ver `janela` — precisa de confirmacao humana (regra 6)",
            "10_inventario": achado["arquivos_por_extensao"],
            "12_erros": achado["codigos_de_erro_tratados"],
            "14_procedencia": {
                "branch": branch,
                "commit": git("rev-parse", "--short", "HEAD", cwd=raiz),
                "detectado_em": date.today().isoformat(),
            },
        },
        "secoes_de_julgamento": {
            n: NAO_DETERMINADO
            for n in (
                "1_problema", "2_sinonimos", "3_fatias", "4_nao_cobre",
                "5_decisoes", "6_essencial_x_herdado", "9_plano", "11_cadeia_de_falha",
                "13_lacunas",
            )
        },
        "aviso": (
            "Fila LOCAL. Nao publique este arquivo: ele carrega nome de branch, "
            "caminho e host que podem identificar o cliente. O que sobe e o "
            "MODULO.md produzido pela M2, e so ele passa pelo gate."
        ),
        "proximo_passo": f"/modulex-extrair {slug}",
    }

    pasta = raiz / args.saida
    pasta.mkdir(parents=True, exist_ok=True)
    destino = pasta / f"{slug}.json"
    gravar_json(destino, candidato)

    print(f"\nmodulex: candidato a modulo enfileirado ({pontos} pontos).")
    for porque in porques:
        print(f"  · {porque}")
    print(f"\n  fila: {args.saida}/{slug}.json")
    print(f"  proximo: /modulex-extrair {slug}")
    print("  o que falta e julgamento: o que NAO cobre, essencial x herdado, e as lacunas.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
