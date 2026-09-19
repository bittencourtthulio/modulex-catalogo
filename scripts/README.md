# scripts — o contrato como teste executável

Stdlib apenas. Sem `pip install`: estes scripts rodam em GitHub Actions e na
máquina de quem extrai, e dependência na esteira é custo que ninguém paga
duas vezes.

Saída sem acento, como as demais saídas do catálogo. Nenhum caminho absoluto.

| Script | O que faz | Quando roda |
|---|---|---|
| `buscar.py` | **M0**: busca lexical, lê só o `modulos.json`, offline | a operação mais frequente |
| `detectar_candidato.py` | **a esteira**: enfileira candidato. Não extrai módulo | hook, ao fim do trabalho |
| `validar_modulo.py` | o contrato: 14 seções, schema, `status`, lacunas | antes de publicar, e no PR |
| `gate_publicacao.py` | segredo, dado pessoal, domínio de cliente, caminho absoluto | **antes do push**, e no PR |
| `reindexar.py` | o índice derivado dos `MODULO.md` — confere ou escreve | no PR (`--conferir`), no merge |
| `publicar.py` | gate, contrato, espelho, PR — nada sem `--confirmar` | na publicação |
| `sincronizar.py` | puxa o catálogo do GitHub para o degrau 2 | o **único** ponto que toca a rede |
| `lacuna_issue.py` | busca sem resultado vira issue com voto | no desfecho `NAO EXISTE` |
| `vencidos.py` | quem passou do prazo da D8 | cron mensal |
| `_comum.py` | frontmatter, seções, cadeia do catálogo, prazos | importado pelos demais |

## As duas ordens que não se negociam

**O gate antes do push, não só no CI.** Push protection do GitHub bloqueia
segredo no remoto — mas a essa altura o dado já saiu da máquina, já passou por
proxy e já está em log. Rodar só no CI é fechar a porta depois.

**Nada envia sem `--confirmar`.** `publicar.py` e `lacuna_issue.py` são secos
por padrão. Publicação é irreversível: repositório público é forkado, indexado
e cacheado.

## Como testar depois de mexer

```bash
python3 -m py_compile scripts/*.py
python3 scripts/validar_modulo.py --todos
python3 scripts/reindexar.py --conferir
python3 scripts/gate_publicacao.py $(git ls-files)
python3 scripts/buscar.py "atender cliente por whatsapp"   # EXISTE
python3 scripts/buscar.py "emitir nota fiscal"             # NAO EXISTE
```

**Gate que nunca acusa nada está quebrado.** Teste contra uma isca com token
de provedor, CPF válido, telefone e domínio de cliente, e confirme que ele
*não* acusa `${VAR}`, `<marcador>` nem `@example.com`.

**Detector que acusa documentação também está quebrado.** O teste de regressão
é rodá-lo sobre um intervalo só de documentação deste repositório — que fala de
WhatsApp o tempo todo e não integra coisa nenhuma:

```bash
python3 scripts/detectar_candidato.py --desde 65c468e --ignorar '^scripts/' 
```

Tem que dar zero ponto. Foi assim que a primeira versão foi pega: ela contava
`uazapi` num `.json` de catálogo como SDK, e `webhook` em prosa como rota.

Sobre `scripts/` ele **dispara**, e está certo: o código do gate contém, por
construção, os prefixos de token e os nomes de variável que ele procura. Por
isso `.expx/` — a instalação do método no projeto do cliente — está na lista de
ignorados.
