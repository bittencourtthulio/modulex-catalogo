---
kind: modulo_lacunas
schema: expx-schema-v1
criado_em: 2026-09-02
atualizado_em: 2026-09-19
total_buscas_sem_resultado: 2
buscas_fechadas: 2
---

# Lacunas do catálogo

O que o catálogo **não cobre** e já foi pedido.

Toda busca do M0 que termina em `NAO EXISTE` entra aqui. Este arquivo é o que
transforma falha de busca em pauta: termo que aparece três vezes e nunca acha
nada é a próxima extração a fazer — ou o sinônimo que falta num módulo que já
existe.

## Buscas sem resultado

| data | termo procurado | quem/onde | vezes | encaminhamento |
|------|-----------------|-----------|-------|----------------|
| 2026-09-19 | `emitir nota fiscal` | verificação da instalação, a partir do ExpxNFe | 1 | **fechada** — `nfse-municipal`, extraído em 2026-09-19 |
| 2026-09-19 | `nfs-e` | verificação da instalação, a partir do ExpxNFe | 1 | **fechada** — `nfse-municipal`, extraído em 2026-09-19 |

As duas buscas acima foram feitas na verificação da cadeia de resolução, de
dentro de um projeto que não é o do catálogo. **Não são features**: não contam
no indicador do ciclo, que mede feature com integração de terceiro que consultou
módulo antes de planejar. Contam aqui, porque foram buscas reais que terminaram
em `NAO EXISTE`, e é isso que esta tabela registra.

As duas foram **fechadas no mesmo dia**, pela extração do `nfse-municipal` a
partir do próprio ExpxNFe — que era exatamente o "já existe feature entregue que
vira módulo" do encaminhamento `extrair`. A linha **não sai da tabela**: ela
registra que a busca falhou uma vez, e é isso que torna visível quanto tempo uma
lacuna fica aberta. Havendo, elas viram `extrair`.

`encaminhamento` assume um de três valores:

| valor | significa |
|-------|-----------|
| `aguardando` | ainda não houve trabalho que resolvesse este problema |
| `extrair` | já existe feature entregue que vira módulo; rodar M2 |
| `sinonimo:<id>` | o módulo existe, faltava o termo na seção 2. Corrigido lá |

## Os dois ramos

```
busca falha no M0
  → linha aqui
    → termo repetido SEM modulo    → candidato a extracao (M2)
    → termo repetido COM modulo    → sinonimo faltando (corrige a secao 2 do MODULO.md)
```

O segundo ramo é o que ninguém lembra de olhar, e é o mais barato de consertar:
uma linha na seção 2 conserta uma busca que falhava havia meses. Distinguir os
dois ramos é trabalho manual e vale o esforço — confundi-los custa uma extração
inteira desnecessária.

## Lacunas conhecidas do próprio catálogo

O que se sabe que falta, independentemente de alguém ter buscado.

| Lacuna | Impacto | O que fecharia |
|--------|---------|----------------|
| **domínios ainda sem nenhum módulo**: pagamento, storage, email transacional, assinatura digital | são os problemas que a especificação da skill nomeia como recorrentes. Nota fiscal **saiu desta lista** em 2026-09-19 | uma extração (M2) por domínio, a partir de feature já entregue |
| **nota fiscal de produto (NF-e / NFC-e) não tem módulo** | o `nfse-municipal` cobre **serviço**, que é municipal. Produto é SEFAZ estadual: outro terceiro, outro XML, outro catálogo de erros — e o próprio ExpxNFe já o implementa | uma segunda extração do ExpxNFe, com `problema` distinto e sinônimos cruzados com o `nfse-municipal` |
| **nenhum dos dois módulos tem faixa de esforço observada** | o P4 do prodx dimensiona só pelas fatias, sem ordem de grandeza. Nos dois casos a origem é anterior ao método, e não há datas de abertura e fechamento para ler | a primeira implantação cronometrada sob o método Expx fecha, se alguém registrar as datas |
| ~~o único módulo do catálogo é de uma stack só~~ **FECHADA em 2026-09-19** | o `nfse-municipal` veio de Next.js + Prisma + Turborepo, stack diferente do módulo zero. A separação essencial × herdada foi testada num segundo caso e **se sustentou**: o certificado e o mTLS são essenciais em qualquer projeto, e o envelope de resposta e a coluna de tenancy são herança nos dois | — |
| **nenhum módulo publicou `erros.json`** | a E1 do runx não pode cruzar código de erro com o log sem ler prosa. O `nfse-municipal` tem 8 códigos tabelados em prosa, prontos para virar formato máquina | produzir o dos dois módulos na próxima verificação; o `nfse-municipal` é o mais barato, porque a tabela já existe |
