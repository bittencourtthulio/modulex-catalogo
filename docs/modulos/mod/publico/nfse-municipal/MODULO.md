---
kind: modulo
schema: expx-schema-v1
id: nfse-municipal
namespace: publico
problema: emitir nota fiscal de servico eletronica (NFS-e) em nome de um cliente, com cancelamento e PDF
fornecedores: [sefin-nacional, adn, abrasf]
fatias: [nucleo, cancelamento, danfse, reforma-tributaria, multi-municipio]
repo: https://github.com/bittencourtthulio/ExpxNFe
stack_essencial: [certificado digital A1 em pfx acessivel pelo processo que transmite, runtime com mTLS e criptografia nativa no servidor, assinatura XML-DSig RSA-SHA1 com canonicalizacao C14N e namespace herdado, declaracao assinada vai comprimida e em base64 dentro de envelope JSON, "numeracao de RPS sequencial sob transacao, sem buraco e sem repeticao", persistir o XML transmitido e a resposta bruta da rejeicao, "todo texto do XML em ASCII, no protocolo ABRASF"]
stack_herdada: [next.js 15 app router + typescript + turborepo, postgres com prisma, supabase para auth e storage do certificado, "zod, shadcn/ui, tailwind", envelope de resposta sucesso-dados-erro, coluna de tenancy software_house_id, api key guardada como hash sha-256, interface em pt-BR]
esforco: NAO DETERMINADO
verificado_em: 2026-09-19
verificado_contra: emissao real no SEFIN Nacional em producao, municipio de Cabo Frio/RJ, entre 2026-07 e 2026-09
extraido_de: ExpxNFe — plataforma multi-tenant de emissao fiscal, com NFS-e em producao
status: ativo
---

# NFS-e municipal — Sistema Nacional (ADN) e ABRASF

Emitir nota fiscal de serviço eletrônica em nome de um cliente: montar a
declaração a partir dos dados do serviço, assinar com o certificado digital do
prestador, transmitir ao município, e guardar o que voltou.

Extraído do ExpxNFe, uma plataforma multi-tenant de emissão fiscal com NFS-e em
produção desde julho de 2026.

Este arquivo é o **contrato do módulo**: o que o `modulex` lê para injetar este
conhecimento na base de um trabalho em andamento. É o único arquivo que a
injeção (M1) puxa; os artefatos só descem depois, task a task, na execução.

## 1. Problema que resolve

Emitir NFS-e pelo próprio sistema, em nome do cliente, em vez de alguém digitar
a nota no portal da prefeitura — com a numeração controlada, o XML guardado e o
PDF disponível para quem contratou o serviço.

É o problema que aparece toda vez que um sistema que vende ou intermedia
**serviço** precisa fechar o ciclo fiscal sem mandar o cliente para fora dele.

## 2. Sinonimos e termos de busca

**Português:** nota fiscal de serviço, nfs-e, nfse, emitir nota fiscal, emissão
de nota, nota fiscal eletrônica de serviço, nota de serviço, RPS, DPS, ISS,
ISSQN, prefeitura, sistema nacional de nfs-e, DANFSE, cancelar nota fiscal,
tomador, prestador, competência, item da lista de serviço, LC 116

**Inglês:** service invoice, electronic invoice, municipal invoice, e-invoicing,
tax invoice, invoice issuance, invoice cancellation

**Fornecedores e padrões:** sefin nacional, sefin.nfse.gov.br, ADN,
adn.nfse.gov.br, ABRASF, ABRASF 3.02, GerarNfse, CancelarNfse

**Termos da casa:** emissão, transmitir, rejeição, ambiente de homologação,
certificado A1, mTLS, chave de acesso, série, contador

> **Não confundir com NF-e / NFC-e.** Nota fiscal de **produto** (modelos 55 e
> 65) é outro terceiro — SEFAZ estadual, SOAP, outro padrão de XML e outro
> catálogo de erros. É problema diferente, e é módulo diferente. Este módulo
> cobre **serviço**, que é municipal.

## 3. Fatias

| Fatia | Tipo | Resolve |
|-------|------|---------|
| `nucleo` | **obrigatória** | montar a declaração, assinar, transmitir, e guardar o resultado |
| `cancelamento` | opcional | cancelar uma NFS-e já emitida |
| `danfse` | opcional | gerar o PDF da nota para o tomador |
| `reforma-tributaria` | opcional | os campos de IBS/CBS e o código NBS na declaração |
| `multi-municipio` | opcional | atender mais de um município, com protocolos diferentes |

Cada opcional passou no teste: pode **não** ser instalada sem quebrar o núcleo.
Emitir sem cancelar funciona; emitir sem PDF funciona; emitir para um município
só funciona. O contrário não vale — nenhuma delas existe sem o núcleo.

**`multi-municipio` é a que mais engana.** Parece infraestrutura, e é escopo: um
sistema que atende um município só não precisa de tabela de municípios nem de
roteamento por protocolo, e carregar isso sem precisar traz junto a armadilha
mais cara do módulo (ver seção 11, elo 2).

## 4. O que cobre e o que NAO cobre

### `nucleo`

**Cobre:** montagem do XML da declaração (DPS no Sistema Nacional, RPS no
ABRASF), assinatura XML-DSig RSA-SHA1 sobre o grupo de informações, transmissão
com mTLS, parse da resposta, persistência do XML emitido **e do rejeitado**,
numeração sequencial de RPS por cliente, ambiente de homologação e produção.

**NÃO cobre:** apuração de imposto (o valor do ISS vem calculado de fora);
cadastro de serviços ou de preços; emissão em lote; carta de correção;
substituição automática de nota rejeitada; conciliação contábil; e **a tabela
oficial de Código de Tributação Nacional** — o desdobro nacional não é embarcado,
e isso tem consequência direta (seção 11, elo 4).

### `cancelamento`

**Cobre:** pedido de cancelamento assinado, transmissão, e aferição de vínculo
entre o evento e a nota alvo.

**NÃO cobre:** prazo legal de cancelamento por município — quem valida se ainda
dá tempo é a prefeitura, não este módulo; substituição de nota (que é operação
diferente de cancelamento); estorno financeiro.

### `danfse`

**Cobre:** PDF da nota a partir do XML autorizado, com caminho alternativo
quando o gerador principal falha.

**NÃO cobre:** layout customizado por município ou por marca; envio do PDF por
e-mail como ato fiscal (envio existe, mas é cortesia, não entrega fiscal);
assinatura do PDF.

### `reforma-tributaria`

**Cobre:** o grupo IBS/CBS na declaração, o código NBS, e as alíquotas apuradas.

**NÃO cobre:** o cálculo dos novos tributos; a transição de regime; qualquer
decisão sobre o que é devido. O módulo transporta os valores, não os apura.

### `multi-municipio`

**Cobre:** tabela de municípios com o protocolo de cada um, roteamento
automático por código IBGE, e herança de protocolo quando o dado dinâmico vem
incompleto.

**NÃO cobre:** o cadastro dos municípios em si — cada município novo é trabalho
de descoberta, com URL, versão e protocolo próprios. **Um município novo não é
configuração, é integração.** O módulo entrega o mecanismo de roteamento, não a
lista.

## 5. Decisoes de escopo ja fechadas

**Pauta da F2 do sprintx — o módulo decidiu isto para a casa dele, com as
restrições dela. Nenhuma é fato consumado neste projeto.**

| Decisão na origem | Alternativa descartada | Pergunta para a F2 |
|---|---|---|
| certificado A1 guardado cifrado, no servidor | certificado no cliente, assinatura no navegador | quem guarda o certificado, e quem responde por ele? |
| um certificado por cliente emissor | um certificado da casa, emitindo para todos | há um emissor só, ou vários? |
| numeração de RPS controlada pelo sistema | numeração vinda de quem chama a API | quem é dono da numeração? Duas fontes brigando geram rejeição na prefeitura |
| ambiente (produção/homologação) vem do cadastro do cliente | ambiente vem em cada requisição | ver seção 11, elo 6: esta decisão já custou uma rejeição |
| XML rejeitado é persistido junto com o emitido | guardar só o que foi aceito | sem o rejeitado não há diagnóstico possível |
| API REST com chave por cliente | integração direta no banco | há sistema de terceiro consumindo, ou só o próprio produto? |

A linha do ambiente é a mais instrutiva: ela **parece** detalhe de configuração e
é decisão de arquitetura, e a origem errou nela antes de acertar.

## 6. Dependencia de stack

**Teste aplicado item a item: se eu trocar isto, o terceiro para de funcionar?**

### Essencial ao problema — viaja para qualquer projeto

| Item | Por que é essencial |
|---|---|
| certificado digital A1 (`.pfx`) acessível pelo processo que transmite | a autenticação com o município é **mTLS** com o certificado do prestador; não há token, não há chave de API |
| runtime capaz de mTLS e de criptografia nativa | assinar e transmitir exigem as duas coisas no servidor; não roda no navegador |
| assinatura XML-DSig RSA-SHA1 com canonicalização C14N, com o namespace herdado | é o contrato do padrão; assinatura fora disso volta rejeitada |
| a declaração assinada vai comprimida e em base64, dentro de um envelope JSON | é o formato que o Sistema Nacional recebe |
| numeração de RPS sequencial, sem buraco e sem repetição, sob transação | número repetido é rejeição na prefeitura; número pulado é pergunta do contador |
| persistir o XML transmitido **e** a resposta bruta da rejeição | sem os dois não se diagnostica nada, e a rejeição não se reproduz |
| todo texto do XML em ASCII, no protocolo ABRASF | ver seção 11, elo 3 — não é preferência, é o que o validador aceita |

### Herdada do sistema de origem — precisa ser traduzida pelo stackx do destino

| Item | O equivalente no destino pode ser qualquer coisa |
|---|---|
| Next.js 15 com App Router, TypeScript, Turborepo | qualquer runtime de servidor |
| PostgreSQL com Prisma | qualquer banco |
| Supabase para auth e storage do certificado | qualquer storage cifrado |
| Zod para validação, shadcn/ui e Tailwind na interface | qualquer um |
| envelope de resposta `{ sucesso, dados, erro }` | convenção da casa |
| coluna de tenancy `software_house_id` | qualquer nome, ou nenhum se o projeto é de tenant único |
| chave de API guardada como hash SHA-256, exibida uma vez | é boa prática, não exigência do município |
| interface e mensagens em pt-BR | escolha de produto |

A coluna herdada **não está vazia**, e isso é deliberado: um módulo cuja herança
parece vazia quase sempre tem herança que ninguém enxergou.

## 7. Pre-requisitos

| Pré-requisito | Bloqueante? |
|---|---|
| certificado digital A1 válido do prestador, com a senha | **sim** — sem ele não há transmissão, nem em homologação |
| inscrição municipal ativa do prestador no município de prestação | **sim** — a prefeitura recusa quem não está inscrito |
| o município de prestação estar mapeado: código IBGE, protocolo, endpoint | **sim** — município não mapeado não tem para onde transmitir |
| runtime de servidor com saída para a internet e suporte a mTLS | **sim** |
| banco para as notas, os XMLs e o contador de numeração | **sim** |
| chave de cifragem para o certificado em repouso | sim, se o certificado for guardado pelo sistema |
| código de tributação nacional (desdobro) dos serviços que serão emitidos | não bloqueia subir, **bloqueia emitir** — ver elo 4 |

## 8. Faixa de esforco observada

**`NAO DETERMINADO`** — por fatia e no total.

O trabalho não foi conduzido sob o método Expx: não há plano, orquestrador, QA
nem relatório de entrega de onde tirar datas de abertura e fechamento. O
histórico do repositório mostra a **ordem** em que as coisas aconteceram, não
quanto custaram.

Estimar aqui é proibido (regra 6): o P4 do prodx encolhe escopo com base neste
número, e um número inventado envelhece como se fosse observado. Vai para as
lacunas (seção 13).

O que se pode dizer sem estimar, porque está no histórico: a integração com o
padrão ABRASF foi construída primeiro, e a migração para o Sistema Nacional veio
depois, forçada por prazo regulatório — não por escolha.

## 9. Plano de fases com gates

**`NAO DETERMINADO`** como plano do método. Não existe `ORQUESTRADOR.md` deste
trabalho, e inventar um a partir do histórico seria fabricar procedência.

O que existe, e é honesto declarar como **ordem observada**, não como plano
auditado:

```
1. montar o XML da declaração e validar contra o schema
2. assinar com o certificado e conferir a assinatura isoladamente
3. transmitir em homologação, e só então em produção
4. persistir emitido e rejeitado
5. numeração sob transação
6. cancelamento
7. PDF
```

**O gate que o histórico comprova, e que vale como gate de verdade:** não se
passa da fase 2 para a 3 sem uma emissão aceita em homologação. Cada rejeição da
seção 12 foi descoberta transmitindo — nenhuma apareceu na leitura da
documentação.

## 10. Inventario de artefatos

| Artefato | Quantos | Onde | Marca |
|---|---|---|---|
| pacote do domínio NFS-e (emissão, cancelamento, consulta, substituição, parsers, assinatura, clients, DANFSE) | 52 arquivos | `packages/nfse-core/` | rodou em produção |
| testes automatizados do pacote | 20 | `packages/nfse-core/src/**/__tests__/` | rodou em produção |
| rotas da API REST de NFS-e | 6 | `apps/web/app/api/v1/nfse/` | rodou em produção |
| telas e formulário de serviços | — | `apps/web/app/(portal)/servicos/` | rodou em produção |
| migrações relacionadas a NFS-e e municípios | 2 | `apps/web/migrations/` | rodou em produção |
| modelos de dados `MunicipioNfse` e `SerieContador` | 2 | `packages/database/prisma/schema.prisma` | rodou em produção |
| guia do integrador — Sistema Nacional | 1 | `docs/integrador-nfse-nacional.md` | documentação, validada contra emissão real |
| guia do integrador — IBS/CBS | 1 | `docs/integrador-nfse-ibs-cbs.md` | documentação |
| script de emissão real em homologação | 1 | `packages/nfse-core/scripts/` | ferramenta de diagnóstico |

**Marca de procedência:** o código rodou em produção emitindo NFS-e reais em
Cabo Frio/RJ. O que está marcado como documentação foi escrito **depois** da
emissão real e conferido contra ela.

## 11. Cadeia de falha e armadilhas conhecidas

**Hipóteses de causa a comprovar — nunca causa declarada.** O E1 do runx exige
prova. Isto é a ordem em que vale olhar.

O sintoma particiona a busca antes da primeira consulta: **falha na emissão**
quebra nos elos 1 a 6; **falha no PDF** quebra no elo 7; **número errado de RPS**
quebra no elo 8.

### Elo 1 — Certificado

**Sintoma:** falha de conexão, ou erro de handshake antes de qualquer resposta
do município.
**Checar:** o certificado abre com a senha guardada? Está dentro da validade?
**Prova:** abrir o `.pfx` isoladamente prova que o par certificado/senha está
bom. **Não prova** que ele está habilitado naquele município.

### Elo 2 — Roteamento de protocolo do município

**Sintoma:** a transmissão vai para um endpoint que responde erro genérico, ou
não responde — e o município "funcionava ontem".
**Checar:** o protocolo resolvido para aquele código IBGE é o que o município
usa hoje?
**Prova:** logar o endpoint efetivamente chamado prova o roteamento. **Não prova**
que o endpoint certo aceitaria — pode haver dois defeitos.

> **Esta é a armadilha mais cara do módulo, e ela já aconteceu em produção.** Um
> município que havia migrado de protocolo voltou a ser roteado para o
> webservice antigo, já desligado, porque a origem dinâmica dos dados registrou
> o município **sem a coluna de protocolo** — e o default silencioso do código
> completou a regressão sem nenhum aviso. A correção tem duas partes, e as duas
> importam: protocolo ausente **herda** o conhecido em vez de cair no default, e
> a herança **emite aviso** em vez de acontecer calada. Um default silencioso num
> campo que decide para onde a requisição vai é uma regressão esperando data.

### Elo 3 — Bytes fora do ASCII no XML (protocolo ABRASF)

**Sintoma:** rejeição de XML em desacordo com o schema, sem apontar campo.
**Checar:** há acento em alguma parte do texto — razão social, endereço,
discriminação do serviço?
**Prova:** transmitir a mesma nota com o texto transliterado. Se passa, era isto.

> Descoberto na marra: **toda** emissão aceita em produção era 100% ASCII, e as
> duas rejeitadas tinham acento em nome de rua. O validador não diz isso em lugar
> nenhum.

### Elo 4 — Código de tributação nacional com desdobro errado

**Sintoma:** rejeição dizendo que o código de tributação não existe na lista de
serviços.
**Checar:** os dois últimos dígitos do código — o desdobro nacional.
**Prova:** o próprio órgão é o oráculo; um código inexistente rejeita, um válido
passa dessa validação. **Não prova** que a nota inteira está correta.

> Armadilha de desenho: o sistema consegue derivar item e subitem do item da
> lista de serviço, mas **não conhece o desdobro nacional** — a tabela oficial
> não é embarcada. Quando o código não vem informado, o desdobro é assumido como
> `00`, e todo serviço cujo desdobro real seja diferente é rejeitado. **Sempre
> informe o código completo, com 6 dígitos.**

### Elo 5 — Alíquota informada quando não deveria

**Sintoma:** rejeição de alíquota informada indevidamente, em prestador não
optante do Simples.
**Checar:** o campo de alíquota está indo vazio, ou está indo como zero?
**Prova:** inspecionar o XML transmitido. Campo vazio que vira `0` por coerção de
tipo e é tratado como "tem alíquota" é exatamente o defeito que já aconteceu
aqui — `0` não é ausência.

### Elo 6 — Ambiente divergente

**Sintoma:** rejeição de ambiente informado diverge do ambiente de recebimento.
**Checar:** de onde saiu o ambiente desta transmissão — do cadastro do cliente ou
de um payload salvo antes?
**Prova:** comparar o ambiente do XML com o do cadastro no instante da
transmissão.

> Já aconteceu: o ambiente saía de um rascunho salvo, que podia estar defasado em
> homologação, e a declaração ia para o contexto de produção. **O ambiente tem
> uma fonte de verdade só**, e quando há uma API pública, ela é a exceção
> deliberada — lá quem informa é quem chama.

### Elo 7 — PDF em ambiente serverless

**Sintoma:** o download da nota entrega um arquivo de erro em vez do PDF.
**Checar:** o gerador de PDF sobrevive ao empacotamento do ambiente de deploy?
**Prova:** a resposta tem tipo de conteúdo de PDF, ou de JSON?

> Defeito duplo, e o segundo é o que engana: o gerador não sobrevivia ao
> empacotamento serverless, **e** a interface baixava a resposta de erro
> cegamente, sem conferir o tipo do conteúdo. O sintoma visível era "o PDF veio
> corrompido". **Quem baixa arquivo precisa conferir o que recebeu.**

### Elo 8 — Numeração de RPS

**Sintoma:** rejeição na prefeitura por número de RPS, ou número que ignora o
que foi configurado.
**Checar:** o caminho que emitiu consumiu o contador, ou leu um campo de
numeração que ninguém atualiza?
**Prova:** comparar o número transmitido com o contador imediatamente antes.

> Já aconteceu: dois caminhos de emissão, um consumindo o contador e outro lendo
> um campo estático. **Duas fontes de numeração é uma fonte a mais do que pode
> existir.**

## 12. Catalogo de erros

Códigos observados em integração real com o Sistema Nacional. Em rejeição, a
mensagem vem como `"<código> - <descrição>"` e o corpo bruto da resposta é
preservado para diagnóstico.

| Código | Significado | Causa provável | Retry resolve? |
|---|---|---|---|
| `E0310` | código de tributação nacional não existe na lista | desdobro errado nos dois últimos dígitos | **não** — corrija o código |
| `E0617` | alíquota informada indevidamente | alíquota enviada para não optante do Simples | **não** — não envie o campo |
| `E0429` | alíquota de ISSQN inválida | campo vazio virando zero por coerção de tipo | **não** |
| `E0713` | indicador de tributos ou percentual do Simples não podem ser informados | envio de tributo estimado para não optante | **não** |
| `E0235` | endereço do tomador obrigatório quando há CNPJ | endereço ausente | **não** — complete o cadastro |
| `E0006` | ambiente informado diverge do de recebimento | ambiente saindo de payload defasado | **não** — corrija a fonte do ambiente |
| `E0714` | erro na assinatura do arquivo | assinatura XML-DSig inválida | **não** — é defeito de plataforma |
| `E160` | XML em desacordo com o schema (ABRASF) | bytes fora do ASCII, ou tipo de data errado | **não** |

**Duas cautelas, e elas valem para todo código desta tabela:**

- **Código de erro não é causa.** `E160` diz que o XML não passou no schema; não
  diz se foi acento, tipo de data ou campo a mais. A tabela lista os suspeitos; o
  E1 prova qual é.
- **Erro fora desta tabela não é erro impossível.** É erro novo — e vira gatilho
  de verificação deste módulo.

## 13. Lacunas

**A seção que justifica o módulo existir.** Documentação de API qualquer um lê.

| Lacuna | O que se sabe | O que fecharia |
|---|---|---|
| **faixa de esforço** | nada: o trabalho não passou pelo método Expx | uma implantação cronometrada de qualquer fatia |
| **plano de fases auditado** | há ordem observada no histórico, não plano | a próxima implantação, planejada pelo sprintx |
| **a tabela de código de tributação nacional não é embarcada** | o desdobro precisa vir de fora, e errado ele rejeita | embarcar a tabela oficial, ou documentar como consultá-la |
| **um município só está mapeado** | Cabo Frio/RJ, protocolo do Sistema Nacional | cada município novo é descoberta própria; não há lista pronta |
| **prazo legal de cancelamento por município** | não determinado; quem valida é a prefeitura | levantamento por município, se virar requisito |
| **comportamento do protocolo ABRASF hoje** | foi construído e rodou, mas o único município do módulo migrou para o Sistema Nacional; o caminho ABRASF **não está em uso em produção neste momento** | uma emissão real em município que ainda use ABRASF |
| **o que a documentação oficial não diz** | que o validador ABRASF rejeita bytes fora do ASCII; que o desdobro assumido como `00` rejeita; que alíquota vazia coagida a zero rejeita; que o host de emissão não é o mesmo de distribuição | já está nesta seção — foi tudo descoberto transmitindo |

A última linha é o ativo. **Nenhum desses quatro itens está em documentação
oficial**, e cada um custou pelo menos uma rejeição em produção para aparecer.

## 14. Procedencia

| Campo | Valor |
|---|---|
| **Sistema de origem** | ExpxNFe — plataforma multi-tenant de emissão fiscal, open-source e auto-hospedável |
| **Rodou em produção?** | **Sim.** NFS-e reais emitidas em Cabo Frio/RJ |
| **Período observado** | de 2026-07 (integração ABRASF) a 2026-09 |
| **Marco de referência** | 2026-08-03 — a migração do município para o Sistema Nacional, por ato regulatório, e a primeira emissão real nesse protocolo |
| **Padrões e versões** | Sistema Nacional NFS-e (DPS v1.01, REST com mTLS); ABRASF v3.02 (SOAP) |
| **Extraído em** | 2026-09-19 |
| **Extraído de que artefatos** | código-fonte, `SPEC.md`, guias do integrador, e o histórico do repositório. **Não havia** plano, QA ou relatório de entrega do método Expx |
| **Verificado contra** | a emissão real em produção e os guias escritos a partir dela |

**Ressalva de procedência, obrigatória:** este módulo foi extraído de um sistema
que **não** foi construído sob o método Expx. As seções 8 e 9 são
`NAO DETERMINADO` por isso, e não por descuido. Tudo o mais nele vem de código
que rodou e de rejeições que aconteceram — não de leitura de documentação.
