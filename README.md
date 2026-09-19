# modulex-catalogo

O catálogo de módulos do ecossistema Expx — o lugar onde o que já foi
resolvido volta antes de ser redescoberto.

A skill que consome este catálogo é a [`modulex`](https://github.com/bittencourtthulio/modulex).

## O que é um módulo

**Um problema resolvido, não uma biblioteca.** A chave de busca é o problema
na linguagem de quem pede — "atender cliente por WhatsApp", "emitir nota
fiscal de serviço" — nunca o nome do fornecedor.

Cada módulo é um repositório com um `MODULO.md` de 14 seções na raiz. Este
repositório **indexa**; o módulo se descreve.

## Como consultar

```bash
python3 scripts/buscar.py "emitir nota fiscal de servico"
```

A consulta lê **apenas** o `modulos.json`, offline. Nunca clona repositório de
módulo, nunca abre `MODULO.md`, nunca toca a rede. É a operação mais frequente
da skill e precisa ser barata — se encarecer, ninguém usa e o catálogo morre.

De dentro de outro projeto, sincronize antes:

```bash
python3 scripts/sincronizar.py
```

Esse é o **único** ponto que toca a rede. A busca continua lendo arquivo em
disco.

## Como contribuir com um módulo

1. Extraia com `/modulex-extrair` a partir de uma feature **que rodou em
   produção**. Código que não rodou não tem cicatriz, e é a cicatriz que dá
   valor ao módulo.
2. Rode o gate **na sua máquina**, antes de qualquer push:

   ```bash
   python3 scripts/gate_publicacao.py caminho/MODULO.md
   python3 scripts/validar_modulo.py caminho/MODULO.md
   ```

3. Abra o PR com `/modulex-publicar`. O CI confere contrato, gate e índice.

O que o PR pede a uma pessoa é o que nenhum script decide: **se as 14 seções
dizem a verdade, e se o "não cobre" está honesto.**

## O que nunca entra aqui

- **Segredo, domínio de cliente, CPF, CNPJ ou telefone real.** Este
  repositório é público: o que vaza aqui é forkado, indexado e cacheado, e não
  volta com force-push.
- **Campo preenchido por inferência.** Campo não verificável é
  `NAO DETERMINADO` e vai para a seção 13. Módulo com faixa de esforço
  inventada é pior que módulo inexistente, porque o escopo é dimensionado com
  base nesse número.
- **Artefato bruto.** O código fica no repositório do módulo, apontado pelo
  campo `repo`. O que viaja é o conhecimento.

Quando a origem é **privada e continua privada**, o módulo se basta: o catálogo
carrega a estrutura, o `repo` aponta para o próprio catálogo, e a seção 10 marca
cada linha como `nao distribuido`. Consultar e implementar a partir dele não
exige acesso nenhum à origem. Não há o que copiar — o que ele poupa é a
descoberta, que é a maior parte do custo.

O que sobe é **extraído, nunca raspado**: anonimizar falha aberto — o que o
padrão não pegou vai junto. Extrair falha fechado — o que não está no schema
nunca foi copiado.

## Falta módulo para o seu problema?

Abra uma issue com a label `lacuna`, ou deixe o script abrir:

```bash
python3 scripts/lacuna_issue.py "seu problema em linguagem natural"
```

Se já existir, ele soma um 👍 em vez de duplicar. Demanda repetida é o que
prioriza a próxima extração.

## Estrutura

```
docs/modulos/
  modulos.json       o indice maquina — o unico arquivo que a consulta le
  INDICE.md          a versao legivel, uma linha por modulo
  LACUNAS.md         o que o catalogo nao cobre e ja foi pedido
  mod/<ns>/<id>/     espelho derivado do MODULO.md de cada modulo
scripts/             o contrato como teste executavel — so stdlib
.github/workflows/   valida no PR, reindexa no merge, cobra revalidacao por cron
```

`modulos.json` é **derivado** dos `MODULO.md`. Divergência entre os dois: o
`MODULO.md` manda, e o índice é corrigido.

## Os três status

| | `candidato` | `ativo` | `obsoleto` |
|---|---|---|---|
| aparece na busca | sim, **marcado** | sim | sim, com o motivo |
| vira rascunho de plano | **não** | sim | não |
| tem artefato copiado | **não** | sim | não |

Módulo obsoleto **nunca é apagado**: apagar faz a próxima pessoa refazer a
descoberta.

## Licença

MIT.
