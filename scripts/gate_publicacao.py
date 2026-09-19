#!/usr/bin/env python3
"""Gate de publicacao: o que nunca pode subir para o catalogo.

Publicacao e irreversivel. Repositorio publico e forkado, indexado e
cacheado — o que vazou nao volta nem com force-push. Este script e a
ULTIMA linha de defesa, nao a primeira: a primeira e extrair em vez de
raspar (D19), e este gate existe para pegar o que escapou disso.

Roda duas vezes: na maquina de quem publica, ANTES do push, e no PR.
Rodar so no CI nao adianta — a essa altura o dado ja saiu da maquina.

Uso:
    python3 scripts/gate_publicacao.py <arquivo> [...]
    python3 scripts/gate_publicacao.py --staged     # o que esta no index do git

Exit code 0 sem erro, 1 com erro. Aviso nao reprova, mas pede olho humano.
"""

from __future__ import annotations

import math
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _comum import (  # noqa: E402
    Relatorio,
    git,
    ler_frontmatter,
    raiz_do_repo,
    rel,
    tem_caminho_absoluto,
)

# --- segredo: prefixo conhecido de provedor -------------------------------
# Bloqueio duro. Um prefixo destes nunca e coincidencia.
TOKENS = {
    "chave privada": r"-----BEGIN (?:RSA |EC |OPENSSH |PGP )?PRIVATE KEY",
    "aws access key": r"\bAKIA[0-9A-Z]{16}\b",
    "github token": r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{36,}\b",
    "github pat": r"\bgithub_pat_[A-Za-z0-9_]{60,}\b",
    "slack token": r"\bxox[abprs]-[A-Za-z0-9-]{10,}\b",
    "stripe live": r"\b(?:sk|rk)_live_[A-Za-z0-9]{20,}\b",
    "google api key": r"\bAIza[0-9A-Za-z_\-]{35}\b",
    "openai": r"\bsk-(?:proj-)?[A-Za-z0-9_\-]{32,}\b",
    "anthropic": r"\bsk-ant-[A-Za-z0-9_\-]{20,}\b",
    "sendgrid": r"\bSG\.[A-Za-z0-9_\-]{16,}\.[A-Za-z0-9_\-]{16,}\b",
    "twilio sid": r"\bAC[0-9a-f]{32}\b",
    "npm token": r"\bnpm_[A-Za-z0-9]{36}\b",
    "jwt": r"\beyJ[A-Za-z0-9_\-]{10,}\.eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\b",
    "url com credencial": r"\b[a-z][a-z0-9+.\-]*://[^/\s:@]+:[^/\s:@]+@[^\s/]+",
}

# --- atribuicao com cara de segredo ---------------------------------------
ATRIBUICAO = re.compile(
    r"(?i)\b([a-z0-9_]*(?:secret|token|password|passwd|senha|api[_-]?key|"
    r"private[_-]?key|access[_-]?key|service[_-]?role|client[_-]?secret)[a-z0-9_]*)"
    r"\s*[:=]\s*[\"']?([^\s\"',;]{12,})"
)

# Valores que sao claramente marcador, nao segredo.
MARCADORES = re.compile(
    r"(?i)^(?:<[^>]*>|\{\{.*\}\}|\$\{?[a-z0-9_]+\}?|x{4,}|\*{4,}|\.{3,}|"
    r"(?:seu|sua|your|my|troque|exemplo|example|sample|dummy|fake|placeholder|"
    r"changeme|redacted|nao[_ ]?determinado|process\.env).*|"
    r"[A-Z][A-Z0-9_]{6,})$"
)

# --- dado pessoal ---------------------------------------------------------
CPF = re.compile(r"\b(\d{3})\.?(\d{3})\.?(\d{3})-?(\d{2})\b")
CNPJ = re.compile(r"\b(\d{2})\.?(\d{3})\.?(\d{3})/?(\d{4})-?(\d{2})\b")
TELEFONE = re.compile(r"(?:\+55\s?)?\(?\b(?:1[1-9]|[2-9][0-9])\)?\s?9?\d{4}[-\s]?\d{4}\b")
EMAIL = re.compile(r"\b[A-Za-z0-9._%+\-]+@([A-Za-z0-9.\-]+\.[A-Za-z]{2,})\b")
DOMINIO = re.compile(r"\bhttps?://([a-z0-9.\-]+\.[a-z]{2,})", re.I)

DOMINIOS_DE_EXEMPLO = {
    "example.com", "example.org", "example.net", "exemplo.com", "exemplo.com.br",
    "test.com", "localhost", "email.com", "dominio.com", "empresa.com",
}

# Infra publica e documentacao — host aqui nao e dominio de cliente.
DOMINIOS_PUBLICOS = {
    "github.com", "raw.githubusercontent.com", "githubusercontent.com", "gist.github.com",
    "developer.mozilla.org", "nodejs.org", "python.org", "docs.python.org",
    "supabase.com", "supabase.io", "deno.land", "npmjs.com", "pypi.org",
    "vercel.com", "cloudflare.com", "letsencrypt.org", "openai.com", "anthropic.com",
    "w3.org", "json-schema.org", "opensource.org", "creativecommons.org",
    "wikipedia.org", "stackoverflow.com", "schema.org", "claude.ai", "claude.com",
    "opencode.ai", "github.io", "users.noreply.github.com", "noreply.github.com",
    "gov.br", "readthedocs.io", "mit-license.org",
}

# Endereco de servico do proprio GitHub: identifica um bot, nao uma pessoa.
EMAILS_DE_SERVICO = {"users.noreply.github.com", "noreply.github.com"}

EXTENSOES_TEXTO = {
    ".md", ".txt", ".json", ".yml", ".yaml", ".toml", ".ini", ".env", ".example",
    ".py", ".js", ".ts", ".tsx", ".jsx", ".sql", ".sh", ".bash", ".zsh", ".html", ".css",
}


def digitos_cpf_validos(g: tuple[str, ...]) -> bool:
    n = [int(c) for c in "".join(g)]
    if len(set(n)) == 1:
        return False
    for corte in (9, 10):
        soma = sum(n[i] * (corte + 1 - i) for i in range(corte))
        dv = (soma * 10) % 11 % 10
        if dv != n[corte]:
            return False
    return True


def digitos_cnpj_validos(g: tuple[str, ...]) -> bool:
    n = [int(c) for c in "".join(g)]
    if len(set(n)) == 1:
        return False
    for corte, pesos in ((12, [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]),
                         (13, [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])):
        soma = sum(n[i] * pesos[i] for i in range(corte))
        resto = soma % 11
        dv = 0 if resto < 2 else 11 - resto
        if dv != n[corte]:
            return False
    return True


def entropia(s: str) -> float:
    if not s:
        return 0.0
    contagem = Counter(s)
    total = len(s)
    return -sum((c / total) * math.log2(c / total) for c in contagem.values())


def hosts_permitidos(texto: str) -> set[str]:
    """Fornecedor declarado no frontmatter e host legitimo do modulo."""
    fm, _ = ler_frontmatter(texto)
    nomes = set()
    valor = fm.get("fornecedores")
    if isinstance(valor, list):
        nomes = {str(v).strip().lower() for v in valor if str(v).strip()}
    return nomes


def checar(caminho: Path, rep: Relatorio) -> None:
    onde = rel(caminho)
    try:
        texto = caminho.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        rep.aviso("binario", onde, "arquivo nao textual: o gate nao consegue ler. "
                                   "Confirme a olho antes de publicar.")
        return

    fornecedores = hosts_permitidos(texto)

    for numero, linha in enumerate(texto.splitlines(), start=1):
        local = f"{onde}:{numero}"

        for nome, padrao in TOKENS.items():
            if re.search(padrao, linha):
                rep.erro("segredo", local, f"{nome} no texto. Publicacao e irreversivel: "
                                           "gire esse segredo antes de qualquer coisa.")

        for chave, valor in ATRIBUICAO.findall(linha):
            if MARCADORES.match(valor.strip()):
                continue
            if entropia(valor) >= 3.0 and len(valor) >= 16:
                rep.erro("segredo", local, f"`{chave}` recebe valor de alta entropia "
                                           f"({len(valor)} chars). Se for segredo real, "
                                           "gire. Se for exemplo, use marcador.")
            else:
                rep.aviso("segredo-possivel", local, f"`{chave}` recebe valor literal. "
                                                     "Confirme que e marcador.")

        for m in CPF.finditer(linha):
            if digitos_cpf_validos(m.groups()):
                rep.erro("dado-pessoal", local, "CPF com digito verificador valido. "
                                                "Dado pessoal nao entra em catalogo compartilhado.")
        for m in CNPJ.finditer(linha):
            if digitos_cnpj_validos(m.groups()):
                rep.erro("dado-pessoal", local, "CNPJ valido — identifica o cliente de origem.")

        if TELEFONE.search(linha) and not re.search(r"(?i)\b(?:5511|55\s?11)?9{4,}", linha):
            rep.erro("dado-pessoal", local, "telefone com cara de real. Use numero "
                                            "obviamente ficticio ou marcador.")

        for dominio in EMAIL.findall(linha):
            baixo_dom = dominio.lower()
            if baixo_dom not in DOMINIOS_DE_EXEMPLO and baixo_dom not in EMAILS_DE_SERVICO:
                rep.erro("dado-pessoal", local, f"email em `{dominio}`. Use um dominio "
                                                "de exemplo ou remova.")

        for host in DOMINIO.findall(linha):
            host = host.lower()
            partes = host.split(".")
            base = ".".join(partes[-2:])
            sufixo = ".".join(partes[-3:]) if len(partes) >= 3 else base
            if host in DOMINIOS_PUBLICOS or base in DOMINIOS_PUBLICOS \
                    or sufixo in DOMINIOS_PUBLICOS:
                continue
            if host in DOMINIOS_DE_EXEMPLO or base in DOMINIOS_DE_EXEMPLO:
                continue
            if any(f in host for f in fornecedores):
                continue
            rep.aviso("dominio", local, f"`{host}` nao e infra publica conhecida nem "
                                        "fornecedor declarado. Confirme que nao e "
                                        "dominio de cliente.")

        if tem_caminho_absoluto(linha):
            rep.erro("caminho-absoluto", local, "caminho absoluto entrega maquina e "
                                                "pessoa, e e proibido em todo o metodo.")


def alvos(argv: list[str]) -> list[Path]:
    if argv and argv[0] == "--staged":
        raiz = raiz_do_repo()
        saida = git("diff", "--cached", "--name-only", "--diff-filter=ACMR", cwd=raiz)
        return [raiz / linha for linha in saida.splitlines() if linha.strip()]
    caminhos: list[Path] = []
    for arg in argv:
        p = Path(arg)
        if p.is_dir():
            caminhos += [f for f in sorted(p.rglob("*")) if f.is_file()]
        else:
            caminhos.append(p)
    return caminhos


def main(argv: list[str]) -> int:
    caminhos = [
        p for p in alvos(argv)
        if p.is_file() and (p.suffix.lower() in EXTENSOES_TEXTO or p.suffix == "")
    ]
    if not caminhos:
        print("gate_publicacao — nenhum arquivo textual para checar.")
        return 0
    rep = Relatorio(f"gate_publicacao — {len(caminhos)} arquivo(s)")
    for caminho in caminhos:
        checar(caminho, rep)
    codigo = rep.imprimir()
    if codigo:
        print("\n  Publicacao bloqueada. O que sobe e extraido, nunca raspado (regra 12).")
    return codigo


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
