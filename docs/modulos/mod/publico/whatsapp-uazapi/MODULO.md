---
kind: modulo
schema: expx-schema-v1
id: whatsapp-uazapi
namespace: publico
problema: atender cliente por WhatsApp, com caixa de entrada compartilhada pela equipe
fornecedores: [uazapi, api4com, openrouter]
fatias: [nucleo, organizacao, ia, ligacoes, grupos, notificacoes]
repo: https://github.com/bittencourtthulio/whatsapp-uazapi-integration
stack_essencial: ["endpoint publico alcancavel pela internet, sem autenticacao de sessao", "o endpoint responde 2xx em todo caminho, inclusive no payload ignorado", "dois segredos de autenticacao distintos: um cria a conexao, outro opera", normalizacao de destinatario que preserva o identificador de grupo, "ordem de tratamento dos eventos: reacao, edicao, voto, mensagem", cache proprio da midia recebida, banco para conversas e mensagens]
stack_herdada: [react 18 + typescript + vite, "supabase: postgres com rls, edge functions deno, realtime", coluna de tenancy chamada company_id, funcao de tenancy get_user_company_ids com privilegio elevado, contexto de cliente ativo activeCompany.company_id, formato de resposta success-data, shadcn/ui + tailwind com utilitario cn, hooks useAuth e use-toast, interface em pt-BR, publicacao de tabela no realtime do supabase, grant explicito por tabela ao papel autenticado, migracoes somente-adicao]
esforco: NAO DETERMINADO
verificado_em: 2026-08-24
verificado_contra: documentacao publica da uazapi em 2026-08-24
extraido_de: Expx Flow — CRM multi-tenant com modulo WhatsApp em producao
status: ativo
---

# WhatsApp via Uazapi

Atendimento de cliente por WhatsApp com caixa de entrada compartilhada: conexão da
conta por QR, recebimento e envio de mensagens, e a inbox onde a equipe atende.
Extraído de um CRM multi-tenant que rodava o módulo em produção.

Este é o **módulo zero** do catálogo — o primeiro extraído, e o caso contra o qual
o contrato do modulex foi validado.

## 1. Problema que resolve

Atender cliente por WhatsApp dentro do próprio sistema, com a equipe compartilhando
uma caixa de entrada — em vez de cada atendente usar o WhatsApp do celular, sem
histórico, sem atribuição e sem ninguém sabendo quem respondeu o quê.

## 2. Sinonimos e termos de busca

**Português:** whatsapp, zap, wpp, atendimento por whatsapp, atendimento pelo
whatsapp, atender cliente pelo whatsapp, falar com cliente pelo whatsapp,
responder cliente no whatsapp, inbox de atendimento, caixa de entrada, conversa
com cliente, mensagem para cliente, disparo de mensagem, qr code do whatsapp,
chatbot de whatsapp, central de atendimento

**Inglês:** whatsapp, whatsapp integration, chat inbox, shared inbox, messaging,
instant messaging, conversation, webhook de mensagem, qr pairing, message provider

**Fornecedores:** uazapi, api4com (ligações), openrouter (camada de IA)

**Termos da casa:** instância, sessão, número conectado, atendimento, conversa,
atribuir conversa, etiqueta, resposta rápida

**Termos vizinhos que NÃO são este módulo:** Meta Cloud API / WhatsApp Business API
oficial, Z-API, Twilio, SMS, Telegram. Ver seção 4.

## 3. Fatias

O módulo é grande e fatiável. Cada opcional passa no teste: pode não ser instalada
sem quebrar o núcleo.

| Fatia | Tipo | Resolve |
|-------|------|---------|
| `nucleo` | obrigatória | conectar o número, receber e enviar mensagem, e atender numa inbox — sprints 0, 1 e 2 |
| `organizacao` | opcional | quem atende o quê: atribuição, squad, transferência, etiquetas, respostas rápidas, notas, lembretes — sprint 3 |
| `ia` | opcional | análise da conversa em tempo real, copiloto de resposta e agente configurável — sprint 4 |
| `ligacoes` | opcional | ligar para o contato por voz, via API4Com, com gravação — sprint 5.1 |
| `grupos` | opcional | gestão de grupos de WhatsApp (GroupOps) — sprint 5.2 |
| `notificacoes` | opcional | gatilhos, templates e histórico de notificação automática — sprint 5.3 |

**Escopo mínimo real:** `nucleo`. Quem pede "atender cliente por WhatsApp" precisa
dele e de mais nada. As cinco opcionais respondem a outros pedidos, que o cliente
pode nem ter feito — este é o efeito mais importante do módulo no P4 do prodx.

## 4. O que cobre e o que NAO cobre

### `nucleo`

**Cobre:**
- criação da conexão (instância) e pareamento por QR code, com status de conexão
- recebimento de toda mensagem que chega ao número, via webhook público
- envio de texto, mídia, reação, enquete; edição e exclusão de mensagem
- inbox com lista de conversas e janela de chat, atualizando ao vivo sem recarregar
- sincronização do histórico de conversas e download de mídia com cache
- ações de chat: arquivar, silenciar, fixar, marcar como lida, bloquear, encaminhar

**NÃO cobre:**
- **API oficial da Meta (WhatsApp Business API)** — o fornecedor não faz; é provedor não oficial. Avaliar contra a exigência de conformidade do cliente antes de propor
- **outros provedores** (Z-API, Twilio, Meta Cloud) — ficou fora do escopo da origem; as colunas específicas de Z-API foram removidas na extração
- **outros canais** (Telegram, SMS, Instagram, email) — fora do escopo
- **o cadastro de cliente** ao qual a conversa se liga — depende do projeto de destino; o módulo tem o campo de vínculo, não a entidade
- **disparo em massa e campanha** — fora do escopo, e é o que mais causa banimento de número
- **relatório e métrica de atendimento** (tempo de resposta, volume por atendente) — fora do escopo
- **fila de distribuição automática** — quem distribui é a fatia `organizacao`, e mesmo lá a atribuição é manual

### `organizacao`

**Cobre:** atribuição de conversa a um usuário, histórico de atribuição, squad,
transferência, etiquetas, respostas rápidas, notas internas, lembretes.

**NÃO cobre:** distribuição automática por regra ou rodízio; SLA e escalonamento;
horário de atendimento; pesquisa de satisfação — todos fora do escopo da origem.

### `ia`

**Cobre:** análise da conversa em tempo real com card de resumo, copiloto que sugere
resposta, agente configurável com identidade/formato/conhecimento e playground de teste.

**NÃO cobre:** resposta automática sem humano no meio — o agente sugere e responde no
playground; ligar isso na conversa real é decisão e trabalho do destino. Também não
cobre treinamento de modelo próprio nem base vetorial: o conhecimento do agente é texto
de configuração.

### `ligacoes`

**Cobre:** botão de ligar na conversa, ramal/SIP, webhook de gravação da chamada.

**NÃO cobre:** chamada de voz ou vídeo **pelo WhatsApp** — é telefonia comum, por outro
fornecedor (API4Com), para o número do contato. Também não cobre URA, fila de voz nem
transcrição da ligação.

### `grupos`

**Cobre:** informações do grupo, metadados, participantes, mensagens e eventos de grupo.

**NÃO cobre:** moderação automática; entrada em grupo por convite em massa. E há uma
borda operacional: grupos só chegam à inbox principal quando a instância está marcada
para receber mensagem de grupo — por padrão, não chegam.

### `notificacoes`

**Cobre:** gatilhos, templates, histórico e agendamento de notificação automática ao cliente.

**NÃO cobre:** opt-out do destinatário e limitação de taxa — **e esta é a borda mais
perigosa do módulo**. Enviar para quem não tem relação com o remetente é o que faz um
número ser banido. Quem usar esta fatia precisa construir as duas coisas; o módulo não
as traz prontas.

## 5. Decisoes de escopo ja fechadas

**Pauta da F2 do sprintx.** Cada linha abaixo é uma **pergunta** a fazer no projeto de
destino, nunca uma resposta já dada. O módulo decidiu para a casa dele, que era um CRM
multi-tenant.

| Decisão | Valor na origem | O que muda no destino se for diferente |
|---------|-----------------|---------------------------------------|
| um provedor só | somente Uazapi; sem Meta Cloud API, sem Z-API | trocar de provedor reescreve as funções de envio e o webhook; abstrair para dois provedores é trabalho novo, não previsto no plano |
| onde ficam as credenciais | **no banco**, por cliente — nunca em variável de ambiente | nasce de multi-tenant com conta Uazapi distinta por cliente. Em projeto de tenant único, variável de ambiente é mais simples e mais segura |
| separação entre clientes | coluna dedicada + função de tenancy com privilégio elevado, usada por toda política de acesso | projeto de tenant único não precisa; **mas remover a coluna toca todas as 39 tabelas e todas as políticas** — a origem recomenda manter um registro fixo em vez de remover |
| webhook | endpoint **público único**, sem autenticação de sessão | exige domínio público alcançável de fora. Sem isso, esta decisão não se sustenta e o recebimento não funciona |
| grupos na inbox | não chegam por padrão; só com a instância marcada | se o atendimento por grupo for o caso de uso, isto inverte |
| camada de IA | gateway compartilhado, com modelo configurável por cliente | destino que já tem sua própria camada de IA não deve instalar uma segunda |
| adjacentes | incluídos na origem (ligações, grupos, notificações) | são fatias opcionais aqui; a origem os queria, o destino provavelmente não |

## 6. Dependencia de stack

### Essencial ao problema — viaja

| Item | Por que o terceiro exige |
|------|--------------------------|
| endpoint público, alcançável pela internet, **sem autenticação de sessão** | a Uazapi chama de fora, sem usuário logado; com verificação de sessão, recebe 401 e nada chega |
| o endpoint responde **2xx em todo caminho**, inclusive no payload ignorado | resposta diferente de 2xx faz o fornecedor reenfileirar o evento para sempre |
| **dois segredos de autenticação distintos**: um cria a conexão, outro opera | é o contrato do fornecedor. Trocar um pelo outro dá 401 confuso |
| normalização de destinatário que **preserva o identificador de grupo** | é regra do WhatsApp: tirar os não-dígitos de um identificador de grupo faz a mensagem "enviar com sucesso" e nunca chegar |
| ordem de tratamento dos eventos: reação → edição → voto → mensagem | chegam no mesmo endpoint com formatos diferentes; ordem errada faz uma reação virar mensagem |
| cache próprio da mídia recebida | as URLs de mídia do fornecedor expiram; sem cache, a mídia some da conversa |
| banco para conversas e mensagens | o histórico não vive no fornecedor |

### Herdada do sistema de origem — traduzir pelo stackx do destino

| Item | O que é na origem | Equivalente no destino |
|------|-------------------|------------------------|
| framework de interface | React 18 + TypeScript + Vite | a preencher |
| banco e backend | Supabase — Postgres com RLS, Edge Functions em Deno, Realtime | a preencher |
| nome da coluna de tenancy | `company_id` | a preencher |
| função de tenancy | `get_user_company_ids()` com privilégio elevado | a preencher |
| contexto de cliente ativo no navegador | `activeCompany.company_id` — nunca `.id` | a preencher |
| formato de resposta das funções | `{ success, data }` / `{ success, error }` | a preencher |
| biblioteca de interface | shadcn/ui + Tailwind, com utilitário `cn()` | a preencher |
| autenticação e aviso ao usuário | `useAuth`, `use-toast` | a preencher |
| idioma da interface | pt-BR em toda tela, aviso e mensagem visível | a preencher |
| atualização ao vivo | publicação de tabela no Realtime do Supabase | a preencher |
| permissão explícita por tabela | `GRANT` para o papel autenticado em toda tabela nova | a preencher |
| migrações somente-adição | nunca editar migração já aplicada | a preencher |

**Nota sobre a coluna herdada:** ela é longa de propósito. Este módulo veio de um
sistema com stack e arquitetura fortemente acopladas, e é exatamente essa lista que
o `patch-stackx.md` existe para impedir de entrar por omissão no projeto de destino.

As funções de servidor e os hooks portam quase sem mudança para outra stack de mesmo
formato; **os 56 componentes de interface são os que não portam** — dependem de
biblioteca de UI e de idioma.

## 7. Pre-requisitos

| Pré-requisito | Bloqueante | Observação |
|---------------|-----------|------------|
| conta no fornecedor Uazapi, com segredo de administração | **sim** | sem ela o gate do sprint 1 não passa. Construir sprints 0 e 1 e parar no gate é o comportamento correto — não simular |
| um número de WhatsApp para parear | **sim** | é o gate do sprint 1: parear e ver o status virar conectado |
| domínio público alcançável pela internet | **sim** | o recebimento depende do endpoint público. Sem ele, só o envio funciona |
| banco com controle de acesso por linha e funções de servidor | **sim** | é a fundação do sprint 0 |
| entidades de base no banco de destino (clientes/organizações, usuários, vínculo) | **sim** | as migrações da fundação as referenciam por chave estrangeira |
| chave de provedor de IA | não | só para a fatia `ia`; sem ela as demais fatias funcionam |
| conta API4Com | não | só para a fatia `ligacoes` |
| armazenamento de arquivo para cache de mídia | não | sem ele a mídia recebida expira e some; o resto funciona |

## 8. Faixa de esforco observada

> **Isto não é estimativa.** É referência histórica. A estimativa deste projeto é a
> F3.5 do sprintx e depende do plano real.

| Fatia | Faixa | Data da observação | Origem |
|-------|-------|--------------------|--------|
| `nucleo` | **NAO DETERMINADO** | — | — |
| `organizacao` | **NAO DETERMINADO** | — | — |
| `ia` | **NAO DETERMINADO** | — | — |
| `ligacoes` | **NAO DETERMINADO** | — | — |
| `grupos` | **NAO DETERMINADO** | — | — |
| `notificacoes` | **NAO DETERMINADO** | — | — |

**O módulo zero nasce sem faixa de esforço em nenhuma fatia.** O repositório de origem
não declara esforço em lugar nenhum, e o módulo foi extraído de um sistema em produção
sem cronometragem da construção original.

Isto é o comportamento correto, não um defeito da extração: campo não verificável vira
`NAO DETERMINADO` e entra nas lacunas (regra 6). Faixa inventada aqui seria pior que
faixa nenhuma, porque o P4 do prodx encolhe escopo com base neste número.

O que fecharia: uma execução real cronometrada, por fatia, ou o relatório de entrega
do mergex de uma implantação. Ver seção 13.

## 9. Plano de fases com gates

**Rascunho da F3 do sprintx.** As fases abaixo não conhecem o projeto de destino: elas
podem ser reordenadas, fundidas, cortadas e renomeadas. **Os gates não podem ser
cortados sem substituto** — é a parte do plano que veio da cicatriz, não da opinião.

| Fase | Fatia | Entrega | Gate |
|------|-------|---------|------|
| 0.1 | núcleo | tabelas de configuração, conexões, conversas e mensagens | as migrações aplicam sem erro |
| 0.2 | núcleo | função de tenancy, políticas de acesso, permissões explícitas | uma consulta às tabelas retorna **vazio** e **não** erro de permissão |
| 0.3 | núcleo | publicação de atualização ao vivo e configuração das funções | as tabelas aparecem publicadas |
| 1.1 | núcleo | funções de criar conexão, gerar QR, testar status, gerenciar e registrar webhook | as funções respondem |
| 1.2 | núcleo | hooks de configuração e de conexões | a interface lê o estado |
| 1.3 | núcleo | tela de conexão, cartão de status, modal de QR, lista de conexões | **criar conexão → o QR aparece → parear → o status vira conectado no banco** |
| 2.1 | núcleo | endpoint público de recebimento, com roteamento dos tipos de evento | mensagem enviada de um telefone real chega ao banco |
| 2.2 | núcleo | envio de texto, mídia, reação, edição, exclusão, sincronização, download | mensagem enviada pelo sistema **chega num telefone real** |
| 2.3 | núcleo | inbox: lista, janela de chat, balão, campo de envio, mídia, atualização ao vivo | mensagem recebida **aparece na inbox sem recarregar** |
| 2.4 | núcleo | ações de chat: arquivar, silenciar, fixar, marcar lida, bloquear, encaminhar, enquete | cada ação persiste |
| 3.1 | organizacao | atribuição, histórico, squad, transferência, vínculo com cliente | atribuir conversa e o outro cliente não a enxerga |
| 3.2 | organizacao | etiquetas e respostas rápidas | aplicar etiqueta e ela persiste sob controle de acesso |
| 3.3 | organizacao | notas, lembretes, tarefa rápida | criar nota e ela persiste |
| 4.1 | ia | gateway de IA compartilhado e configuração de modelo | o gateway resolve o modelo do cliente |
| 4.2 | ia | análise em tempo real e cartão de resumo | o cartão preenche para uma conversa real |
| 4.3 | ia | copiloto, agente configurável, painéis, playground | o copiloto sugere e o agente responde no playground |
| 5.1 | ligacoes | botão de ligar, ramal, webhook de gravação | uma ligação é feita |
| 5.2 | grupos | grupos, membros, mensagens, eventos | um grupo é gerenciado |
| 5.3 | notificacoes | gatilhos, templates, histórico, agendamento | um gatilho dispara |

**Ordem e dependências, o que não pode ser invertido:**

- o sprint 0 vem inteiro antes de tudo. Depurar a fase 4 sobre uma fundação quebrada é
  sofrimento — os modos de falha se compõem;
- o gate 0.2 é o mais importante do plano: consulta que retorna vazio **sem erro** é a
  assinatura de permissão faltando, e essa falha é silenciosa em todas as fases seguintes;
- a decisão de tenancy é tomada **antes da primeira migração**: mudá-la depois renomeia
  uma coluna em 39 tabelas, em toda política de acesso e em 34 funções de servidor;
- as migrações aplicam em ordem numérica; há chaves estrangeiras entre elas;
- `organizacao`, `ia`, `ligacoes`, `grupos` e `notificacoes` são independentes entre si
  e todas dependem do núcleo.

## 10. Inventario de artefatos

| Artefato | Quantos | Onde | Marca |
|----------|---------|------|-------|
| migrações SQL, numeradas na ordem de aplicação | 14 | `skills/whatsapp-uazapi/assets/migrations/` | rodou em produção (consolidadas a partir das migrações incrementais da origem) |
| funções de servidor (Deno) | 34 | `skills/whatsapp-uazapi/assets/edge-functions/` | rodou em produção |
| hooks React | 21 | `skills/whatsapp-uazapi/assets/frontend/hooks/` | rodou em produção |
| componentes React | 56 | `skills/whatsapp-uazapi/assets/frontend/components/` | rodou em produção |
| bibliotecas auxiliares (repetição de chamada, formatação) | 2 | `skills/whatsapp-uazapi/assets/frontend/lib/` | rodou em produção |
| documentos de plano (orquestrador + fases) | 20 | `skills/whatsapp-uazapi/references/` | plano |
| exemplos de payload, requisição e formatação | 5 | `skills/whatsapp-uazapi/assets/examples/` | exemplo |

**Total: mais de 150 arquivos.** É por isso que a consulta do M0 nunca clona o
repositório do módulo — só a injeção puxa peso, e mesmo ela não desce os artefatos:
eles são copiados na F6, task a task, sob TDD.

**Ressalva de procedência sobre as migrações:** o SQL rodou em produção, mas foi
**consolidado** para a extração — cada tabela virou um `CREATE TABLE` único com as
colunas incrementais embutidas, em vez da sequência histórica de alterações. E as
migrações originais **não** emitiam a permissão explícita por tabela; ela foi
acrescentada na extração, justamente porque sua ausência é o modo de falha mais
confuso da stack. O SQL final não é byte a byte o que rodou.

## 11. Cadeia de falha e armadilhas conhecidas

**Hipóteses para a E1 do runx. NÃO são causa comprovada** (regra 10). A E1 exige prova;
isto é a ordem em que vale olhar.

A regra que governa o diagnóstico: **isole o elo primeiro, leia o código do elo depois.**
Mudar código antes de localizar a quebra é como as tardes desaparecem.

A cadeia tem sete elos. O sintoma já particiona a busca: **recebimento** quebra nos elos
3 a 7; **envio** quebra nos elos 1, 2 ou na normalização do destinatário.

| Elo | Sintoma observável | Como isolar | O que o resultado prova |
|-----|--------------------|-------------|-------------------------|
| 1 configuração do cliente | nada funciona, nem enviar nem conectar | a configuração existe e tem endereço e segredo? | prova que há o que usar; **não** prova que o segredo é válido |
| 2 conexão | envio falha; status não é "conectado" | qual o status da conexão no banco? | status diferente de conectado explica o envio; **não** explica o recebimento |
| 3 webhook registrado | nada chega, e o registro do endpoint não tem nenhuma entrada | há registro de chamada no endpoint? | **nenhuma** entrada prova que o fornecedor não está chamando; **não** diz por quê |
| 4 endpoint público | o registro mostra 401/403 | a função exige sessão? | 401 no registro prova que a verificação de sessão ficou ligada nessa função |
| 5 gravação no banco | o endpoint responde, mas não há mensagem gravada | há mensagem recente na tabela? | **há** mensagem → a quebra é depois (6 ou 7); **não há** → é antes (3 ou 4) |
| 6 atualização ao vivo | a mensagem aparece só ao recarregar a página | a tabela está publicada? | tabela não publicada explica; **não** exclui filtro errado na assinatura do frontend |
| 7 leitura pelo usuário | consulta retorna **vazio, sem erro** | a permissão explícita existe? a função de tenancy devolve algo para este usuário? | vazio sem erro é assinatura de permissão faltando ou tenancy quebrada — **não** de ausência de dado |

**Armadilhas:**

- **consulta devolve vazio e nenhum erro** — falta a permissão explícita na tabela, ou a
  política de acesso consulta diretamente uma tabela protegida em vez de passar pela
  função de tenancy. É a falha mais confusa desta stack porque **não há mensagem de erro**
- **o fornecedor reenvia o mesmo evento para sempre** — algum caminho do endpoint
  respondeu diferente de 2xx. Inclusive o caminho do payload ignorado
- **"enviou com sucesso" e não chegou** — normalização do destinatário: identificador de
  grupo que perdeu o sufixo ao passar por uma limpeza de não-dígitos, ou código de país
  duplicado. É a falha de envio mais comum
- **o nome do grupo aparece como o nome de um membro** — o nome do contato foi lido do
  remetente da mensagem; num grupo, o remetente é um participante, não a conversa
- **a mídia para de carregar depois de um tempo** — as URLs do fornecedor expiram; sem o
  cache próprio, a mídia some do histórico
- **conecta e cai em poucos minutos** — a mesma conta está pareada em outro lugar, ou a
  conexão foi apagada do lado do fornecedor
- **o QR aparece e escanear não faz nada** — o QR expirou; é de vida curta e precisa ser
  gerado e escaneado na hora
- **401 no envio** — o segredo de administração foi usado onde deveria ir o da conexão

**O que parece defeito e não é:** grupo ausente da inbox (é o padrão); contador de não
lidas que não zera (quem zera é a ação de marcar como lida, na abertura); mensagem
enviada do próprio celular aparecendo como saída (está correto).

## 12. Catalogo de erros

| Código | Significa | Causas possíveis | Retry |
|--------|-----------|------------------|-------|
| 401 na criação de conexão | não autorizado | segredo de administração errado ou ausente na configuração do cliente | não — corrigir a credencial |
| 401 no envio ou em operação de mensagem | não autorizado | usou o segredo de administração onde vai o da conexão; conexão recriada do lado do fornecedor sem atualizar o segredo guardado | não — corrigir o cabeçalho ou re-sincronizar a conexão |
| 401/403 no endpoint de recebimento | não autorizado | a verificação de sessão ficou ligada na função pública | não — é configuração |
| 200 no envio, nada no telefone | aceito e não entregue | normalização do destinatário; conta não conectada | não — o erro não é de transporte |
| evento reenviado indefinidamente | o fornecedor não recebeu 2xx | algum caminho do endpoint responde outro código | não se aplica — o retry é do fornecedor, e é o sintoma |
| resposta vazia sem erro na leitura | não é erro do fornecedor | permissão faltando ou tenancy quebrada | não |
| falha ao carregar mídia | URL expirada | mídia não foi para o cache próprio | sim, pelo caminho de download com cache |

`NAO DETERMINADO`: o módulo **não traz o catálogo de códigos de erro do fornecedor**. A
tabela acima foi montada a partir dos modos de falha observados na origem, não da
documentação da Uazapi. Não há `erros.json`. Ver seção 13.

## 13. Lacunas

O ativo mais caro deste módulo. As quatro primeiras foram descobertas na marra e não
estão na documentação de ninguém.

| Lacuna | O que se sabe | O que falta para fechar |
|--------|---------------|-------------------------|
| resposta 2xx obrigatória em **todo** caminho | payload ignorado que responde 4xx faz o fornecedor reenfileirar o evento para sempre. A documentação não diz isso | nada — está fechada, é conhecimento do módulo |
| o nome da conversa vem do objeto da conversa, não do remetente | em grupo, o remetente é um participante; ler dali nomeia a conversa com o nome de um membro | nada — fechada |
| identificador de grupo não pode passar por limpeza de não-dígitos | a mensagem é aceita e nunca chega. Falha silenciosa e cara de achar | nada — fechada |
| dois segredos de autenticação com papéis distintos | trocar um pelo outro dá 401 sem explicação. A documentação não destaca a distinção | nada — fechada |
| **faixa de esforço, em todas as seis fatias** | **nenhuma observação real** — a origem não cronometrou, e o repositório não declara esforço em lugar nenhum | uma execução real cronometrada por fatia, ou o relatório de entrega do mergex de uma implantação |
| catálogo de códigos de erro do fornecedor | só os modos de falha observados na origem; não há a lista oficial de códigos | ler a documentação atual da Uazapi e produzir `erros.json` |
| limites de taxa do fornecedor | desconhecidos. O módulo não implementa limitação nem espera entre envios | documentação do fornecedor, ou medição |
| política de banimento de número | sabe-se que enviar para quem não tem relação com o remetente causa banimento; não se sabe o limiar | não é documentado publicamente pelo WhatsApp; só observação de campo |
| comportamento sob volume | o módulo rodou num CRM; não há medida de quantas mensagens por segundo o desenho suporta | uma medição real |
| custo do fornecedor | não registrado | consulta ao plano vigente da Uazapi |
| conformidade | a Uazapi é provedor **não oficial**; isso tem implicação legal e contratual que a extração não avaliou | avaliação jurídica do cliente de destino |

## 14. Procedencia

**Extraído de:** Expx Flow — CRM multi-tenant com o módulo WhatsApp rodando em produção.
**Extraído em:** 2026-08-24 (versão 1.0.0 do pacote de origem).
**Extraído por:** manualmente, pelo autor do sistema de origem, antes de o modulex existir.

**Sanitização declarada pela origem:** sem segredos, sem referências de projeto, sem
telefones reais, sem domínios específicos. Uma URL de projeto que estava fixa no código
virou variável de ambiente; o domínio do produto na função de notificação virou variável.

| Data | O que foi verificado | Contra o quê | Resultado |
|------|----------------------|--------------|-----------|
| 2026-08-24 | contrato da API, endpoints, autenticação, formatação de destinatário, modos de falha | documentação pública da Uazapi e o código em produção da origem | publicação inicial |
| 2026-09-02 | conformidade do módulo ao contrato do modulex | `references/04-contrato.md` | 14 seções preenchidas; 7 campos `NAO DETERMINADO`, todos na seção 13 |

**Atenção — a data que conta:** o contrato da API foi verificado pela última vez em
**2026-08-24**, contra a documentação pública. O prazo desse campo é de 6 meses
(`references/03-verificacao.md`), portanto este módulo vence em **2027-02-24**. A
verificação de 2026-09-02 foi de **conformidade ao contrato do modulex**, não da API —
ela não renova o prazo.
