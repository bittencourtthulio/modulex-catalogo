"""Funcoes comuns aos scripts do modulex.

Sem dependencia externa: stdlib apenas. O gate e o validador rodam em
GitHub Actions e na maquina de quem extrai, e `pip install` na esteira e
custo que ninguem paga duas vezes.

Nenhum caminho absoluto. Todo caminho aqui e relativo a raiz do repositorio
ou vem por argumento.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

SCHEMA = "expx-schema-v1"
NAO_DETERMINADO = "NAO DETERMINADO"

STATUS_VALIDOS = ("ativo", "candidato", "obsoleto")

# D8: prazos de verificacao por tipo de campo, em dias.
PRAZOS_DIAS = {
    "contrato": 183,   # contrato da API, catalogo de erros, pre-requisitos
    "execucao": 365,   # cadeia de falha, plano, stack, esforco
    "problema": 730,   # problema, sinonimos, fatias, cobertura
}

CHAVES_FRONTMATTER = (
    "kind",
    "schema",
    "id",
    "namespace",
    "problema",
    "fornecedores",
    "fatias",
    "repo",
    "stack_essencial",
    "stack_herdada",
    "esforco",
    "verificado_em",
    "verificado_contra",
    "extraido_de",
    "status",
)

SECOES = (
    (1, "Problema que resolve"),
    (2, "Sinonimos e termos de busca"),
    (3, "Fatias"),
    (4, "O que cobre e o que NAO cobre"),
    (5, "Decisoes de escopo ja fechadas"),
    (6, "Dependencia de stack"),
    (7, "Pre-requisitos"),
    (8, "Faixa de esforco observada"),
    (9, "Plano de fases com gates"),
    (10, "Inventario de artefatos"),
    (11, "Cadeia de falha e armadilhas"),
    (12, "Catalogo de erros"),
    (13, "Lacunas"),
    (14, "Procedencia"),
)

# Secoes que nao aceitam NAO DETERMINADO (regra dura do contrato).
SECOES_SEM_ND = (1, 4, 14)


@dataclass
class Achado:
    """Uma falha encontrada por um script. `nivel` decide o exit code."""

    nivel: str  # "erro" | "aviso"
    regra: str
    onde: str
    detalhe: str

    def linha(self) -> str:
        marca = "ERRO " if self.nivel == "erro" else "aviso"
        return f"  [{marca}] {self.regra} :: {self.onde}\n          {self.detalhe}"


@dataclass
class Relatorio:
    titulo: str
    achados: list[Achado] = field(default_factory=list)

    def erro(self, regra: str, onde: str, detalhe: str) -> None:
        self.achados.append(Achado("erro", regra, onde, detalhe))

    def aviso(self, regra: str, onde: str, detalhe: str) -> None:
        self.achados.append(Achado("aviso", regra, onde, detalhe))

    @property
    def erros(self) -> list[Achado]:
        return [a for a in self.achados if a.nivel == "erro"]

    @property
    def avisos(self) -> list[Achado]:
        return [a for a in self.achados if a.nivel == "aviso"]

    def imprimir(self) -> int:
        print(f"\n{self.titulo}")
        if not self.achados:
            print("  ok — nada a apontar.")
            return 0
        for achado in self.achados:
            print(achado.linha())
        print(f"\n  {len(self.erros)} erro(s), {len(self.avisos)} aviso(s).")
        return 1 if self.erros else 0


def dividir_lista(miolo: str) -> list[str]:
    """Divide uma lista inline respeitando aspas.

    Necessario porque item de lista do expx-schema v1 contem virgula com
    frequencia — "endpoint publico, sem autenticacao de sessao" e um item
    so, nao dois. Dividir cru quebra o item ao meio e o indice passa a
    divergir do MODULO.md por defeito do parser, nao do conteudo.
    """
    itens: list[str] = []
    atual: list[str] = []
    aspas: str | None = None
    for ch in miolo:
        if aspas:
            if ch == aspas:
                aspas = None
            else:
                atual.append(ch)
            continue
        if ch in "\"'":
            aspas = ch
            continue
        if ch == ",":
            itens.append("".join(atual).strip())
            atual = []
            continue
        atual.append(ch)
    itens.append("".join(atual).strip())
    return [i for i in itens if i]


def escrever_lista(itens: list[str]) -> str:
    """Serializa a lista inline, citando o item que contem virgula."""
    partes = [f'"{i}"' if ("," in i or ":" in i) else i for i in itens]
    return "[" + ", ".join(partes) + "]"


def ler_frontmatter(texto: str) -> tuple[dict[str, object], str]:
    """Le o subconjunto de YAML do expx-schema v1.

    Aceita `chave: escalar` e `chave: [a, b, c]`. Nada mais — o schema nao
    usa aninhamento, e um parser completo traria dependencia.
    """
    if not texto.startswith("---"):
        return {}, texto
    partes = texto.split("---", 2)
    if len(partes) < 3:
        return {}, texto
    bruto, corpo = partes[1], partes[2]
    dados: dict[str, object] = {}
    for linha in bruto.splitlines():
        linha = linha.rstrip()
        if not linha.strip() or linha.lstrip().startswith("#"):
            continue
        if ":" not in linha:
            continue
        chave, _, valor = linha.partition(":")
        chave = chave.strip()
        valor = valor.strip()
        if valor.startswith("[") and valor.endswith("]"):
            miolo = valor[1:-1].strip()
            dados[chave] = dividir_lista(miolo) if miolo else []
        else:
            dados[chave] = valor
    return dados, corpo


def normalizar(texto: str) -> str:
    """Minusculas, sem acento, sem pontuacao — para comparar titulo de secao."""
    tabela = str.maketrans(
        "áàâãäéèêëíìîïóòôõöúùûüçÁÀÂÃÄÉÈÊËÍÌÎÏÓÒÔÕÖÚÙÛÜÇ",
        "aaaaaeeeeiiiiooooouuuucAAAAAEEEEIIIIOOOOOUUUUC",
    )
    texto = texto.translate(tabela).lower()
    return re.sub(r"[^a-z0-9]+", " ", texto).strip()


def fatiar_secoes(corpo: str) -> dict[int, str]:
    """Devolve {numero_da_secao: texto}, lendo os titulos `## N. ...`."""
    secoes: dict[int, str] = {}
    atual: int | None = None
    acumulado: list[str] = []
    for linha in corpo.splitlines():
        m = re.match(r"^##\s+(\d{1,2})[.)]?\s+(.*)$", linha.strip())
        if m:
            if atual is not None:
                secoes[atual] = "\n".join(acumulado)
            atual = int(m.group(1))
            acumulado = []
            continue
        if atual is not None:
            acumulado.append(linha)
    if atual is not None:
        secoes[atual] = "\n".join(acumulado)
    return secoes


def e_data_iso(valor: object) -> bool:
    if not isinstance(valor, str):
        return False
    try:
        date.fromisoformat(valor)
    except ValueError:
        return False
    return True


def vencido_em(verificado_em: str, prazo: str = "contrato", hoje: date | None = None) -> bool:
    """D8: o `verificado_em` e a data mais antiga entre os campos."""
    if not e_data_iso(verificado_em):
        return True
    hoje = hoje or date.today()
    return date.fromisoformat(verificado_em) + timedelta(days=PRAZOS_DIAS[prazo]) < hoje


# Montadas em pedacos de proposito: escritas literais, o proprio gate se
# acusaria de caminho absoluto ao varrer o seu codigo-fonte.
RAIZES_DE_MAQUINA = ("/" + "Users" + "/", "/" + "home" + "/", "/" + "root" + "/")
UNIDADE_WINDOWS = re.compile(r"\b[A-Za-z]:" + "\\\\")


def tem_caminho_absoluto(linha: str) -> bool:
    """Regra transversal: nenhum caminho absoluto em artefato ou saida."""
    if any(raiz in linha for raiz in RAIZES_DE_MAQUINA):
        return True
    return bool(UNIDADE_WINDOWS.search(linha))


def raiz_do_repo(inicio: Path | None = None) -> Path:
    p = (inicio or Path.cwd()).resolve()
    for candidato in (p, *p.parents):
        if (candidato / ".git").exists():
            return candidato
    return p


def resolver_catalogo(base: Path | None = None) -> tuple[Path | None, int]:
    """A cadeia de resolucao de `references/05-catalogo.md`.

    Devolve (pasta_do_catalogo, degrau). Degrau 0 quando nenhum resolve.
    Nenhum degrau toca a rede — a sincronizacao e operacao a parte.
    """
    base = (base or raiz_do_repo()).resolve()
    env = os.environ.get("MODULEX_CATALOGO", "").strip()
    if env:
        p = Path(env).expanduser()
        if (p / "modulos.json").is_file():
            return p, 1
    for degrau, rel in ((2, ".expx/modulex/docs/modulos"), (3, "docs/modulos")):
        p = base / rel
        if (p / "modulos.json").is_file():
            return p, degrau
    return None, 0


def rel(caminho: Path, base: Path | None = None) -> str:
    """Caminho sempre relativo — regra transversal do metodo."""
    base = (base or raiz_do_repo()).resolve()
    try:
        return str(Path(caminho).resolve().relative_to(base))
    except ValueError:
        return Path(caminho).name


def git(*args: str, cwd: Path | None = None) -> str:
    try:
        saida = subprocess.run(
            ["git", *args],
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return ""
    return saida.stdout.strip() if saida.returncode == 0 else ""


def carregar_json(caminho: Path) -> dict:
    with open(caminho, encoding="utf-8") as fh:
        return json.load(fh)


def gravar_json(caminho: Path, dados: dict) -> None:
    with open(caminho, "w", encoding="utf-8") as fh:
        json.dump(dados, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
