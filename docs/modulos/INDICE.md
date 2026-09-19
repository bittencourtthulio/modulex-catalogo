---
kind: modulo_indice
schema: expx-schema-v1
criado_em: 2026-09-02
atualizado_em: 2026-09-19
total_modulos: 2
ativos: 2
obsoletos: 0
vencidos: 0
---

# Índice de módulos

Append-only. Uma linha por módulo. É a versão legível do `modulos.json` — a
consulta do M0 lê o JSON; humano lê este arquivo.

Módulo obsoleto **nunca é apagado**: a M0 continua achando e responde
"existiu, está obsoleto, motivo". Apagar faz a próxima pessoa refazer a
descoberta.

| id | problema | fatias | fornecedor | esforco | verificado_em | status |
|----|----------|--------|------------|---------|---------------|--------|
| `whatsapp-uazapi` | atender cliente por WhatsApp, com caixa de entrada compartilhada pela equipe | 6 (nucleo + 5 opcionais) | uazapi | NAO DETERMINADO | 2026-08-24 | ativo |
| `nfse-municipal` | emitir nota fiscal de serviço eletrônica (NFS-e) em nome de um cliente, com cancelamento e PDF | 5 (nucleo + 4 opcionais) | sefin-nacional / abrasf | NAO DETERMINADO | 2026-09-19 | ativo |

## Indicadores

- **Módulos no catálogo:** 2
- **Ativos:** 2 · **Obsoletos:** 0
- **Com verificação vencida:** 0 — `whatsapp-uazapi` vence em 2027-02-24, `nfse-municipal` em 2027-03-19
- **Buscas sem resultado registradas:** 2 — `emitir nota fiscal` e `nfs-e`, ambas em 2026-09-19 e **fechadas** pelo `nfse-municipal` no mesmo dia
- **Sem faixa de esforço:** 2 — o P4 do prodx dimensiona só pelas fatias nesses casos
- **Stacks distintas representadas:** 2 — React+Supabase e Next.js+Prisma. A separação essencial × herdada foi finalmente testada num segundo caso

## O indicador do modulex

Dois números, e cada um sozinho mente. Precisam do memox para serem exatos;
sem ele, o catálogo reporta o que sabe e declara a leitura parcial.

- **Features com integração de terceiro que consultaram um módulo antes de planejar:** 0 de 0 — nenhuma feature ainda. As buscas de 2026-09-19 foram verificação da instalação, não features, e deliberadamente **não** entram aqui
- **Dessas, quantas viraram módulo novo depois:** 0

O `nfse-municipal` **também não entra no segundo número**: ele não saiu de uma
feature que consultou o catálogo antes de planejar — saiu de um sistema que
existia antes do modulex. Contá-lo aqui faria o indicador dizer que o ciclo
fechou quando ele ainda não começou a girar.

| Leitura | Escrita | Diagnóstico |
|---------|---------|-------------|
| alta | alta | ciclo fechado — estado saudável |
| alta | zero | o catálogo apodrece: é lido, envelhece, ninguém devolve |
| zero | alta | a consulta está cara demais |
| zero | zero | a skill não pegou |
