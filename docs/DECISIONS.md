# Registro de Decisões Arquiteturais — Santa Rubi Label Studio

Este documento registra, no formato ADR (Architecture Decision Record)
simplificado, as decisões arquiteturais que moldaram o sistema até a
versão `v3.0-stable`. Cada registro é permanente: se uma decisão for
revista no futuro, a mudança deve ser documentada como um novo ADR que
referencia e supersede o anterior — nenhum registro existente deve ser
apagado ou reescrito.

Para o detalhamento técnico de cada módulo citado aqui, ver
[ARCHITECTURE.md](../ARCHITECTURE.md). Para o histórico de versões, ver
[CHANGELOG.md](../CHANGELOG.md) e [DOCUMENTACAO_CHECKPOINT.md](../DOCUMENTACAO_CHECKPOINT.md).

---

## ADR 001 — Existe apenas um pipeline de impressão

**Contexto**
O sistema tem duas telas que precisam imprimir etiquetas: a aba
"Impressão" (fluxo original, a partir de uma planilha avulsa) e, depois,
o Catálogo Integrado (fluxo permanente, via `PrintQueue`). Ao integrar o
Catálogo Integrado ao motor de impressão, existia o risco concreto de
nascer um segundo `ZplBuilder`/`PrinterService` só para atender a fila,
já que a fila trabalha com um modelo de dados diferente (`PrintItem`) do
usado pela aba "Impressão" (dicionário vindo do Excel).

**Decisão**
Existe um único motor de impressão em todo o sistema:
`ZplBuilder.build()`/`build_row()` + `PrinterService.print_raw()`. As duas
telas — "Impressão" e "Catálogo Integrado" — convergem obrigatoriamente
para esses mesmos módulos. É proibido criar um novo `ZplBuilder`, um novo
`PrinterService`, um novo `build()`/`build_row()` ou qualquer pipeline de
impressão paralelo.

**Justificativa**
O motor de impressão foi calibrado fisicamente contra impressões reais na
ELGIN L42PRO FULL (`v1.0-print-engine`, `v1.1-smart-print`,
`v1.2-layout-final`) — duplicá-lo significaria duplicar também o risco de
divergência de comportamento e a necessidade de recalibrar/testar
fisicamente duas vezes qualquer ajuste futuro.

**Consequências**
Toda nova origem de dados de impressão (como `PrintQueue`) precisa ser
*adaptada* para o formato que o motor já aceita, nunca ganhar seu próprio
motor. Qualquer correção ou calibração física feita uma vez vale
automaticamente para as duas telas.

**Data:** 2026-07-21 (formalizada em `v1.0-print-engine`; reafirmada
explicitamente na integração do Catálogo Integrado e em `v3.0-stable`)

---

## ADR 002 — PrintQueue é a única fonte da fila

**Contexto**
A Fila de Impressão do Catálogo Integrado precisa ser lida e alterada por
vários pontos da interface: botão "Adicionar à Fila", botões "Remover"/
"Limpar Fila", botões `[-]`/`[+]`, edição direta de quantidade, atalhos
DEL/Ctrl+A. Sem um dono único do estado, cada um desses pontos poderia
manter sua própria cópia da lista de itens, arriscando estado
dessincronizado.

**Decisão**
`PrintQueue` é a única fonte de verdade da fila de impressão. Toda leitura
passa por `items()`/`to_list()`/iteração (`__iter__`), e toda escrita por
seus métodos públicos: `add`, `remove`, `clear`, `contains`, `find`,
`update_quantity`, `increment`, `decrement`, `replace`. Nenhum outro
objeto — nem a interface, nem `CatalogService` — guarda uma cópia
independente do estado da fila.

**Justificativa**
Centralizar o estado num único objeto elimina a classe inteira de bugs de
dessincronização entre "o que a interface mostra" e "o que será
efetivamente impresso". Expor uma API rica (em vez de uma lista crua)
também permite a fila crescer (duplicar item, prioridade, ordenação) sem
quebrar quem já a consome.

**Consequências**
Depois de qualquer mutação, a interface sempre redesenha a partir de
`PrintQueue` (`_refresh_queue_view()`), nunca atualiza um cartão
manualmente. Igualdade de item é sempre por `codigo` do produto, nunca por
identidade de objeto.

**Data:** 2026-07-21 (separação de domínio e criação de `PrintQueue`;
API rica consolidada logo em seguida, no mesmo ciclo)

---

## ADR 003 — LabelData substitui dict

**Contexto**
`PrintQueueAdapter` convertia `PrintQueue` em `list[dict]` para alimentar
`ZplBuilder.build_row()` — o mesmo formato de dicionário solto que a aba
"Impressão" já usava, vindo diretamente da planilha Excel. Chaves de
dicionário não garantem nada em tempo de escrita: um erro de digitação
numa chave (`"numero"` vs. `"número"`) só se manifestaria em tempo de
execução, silenciosamente, como uma etiqueta com campo em branco.

**Decisão**
Criado `core/label_data.py` com `LabelData` (`@dataclass(frozen=True)`,
campos `codigo`, `descricao`, `categoria`, `numero`, `preco`) como o
único formato de entrada de `ZplBuilder.build_row()`. `build()` (etiqueta
única) mantém compatibilidade com `dict`, convertendo internamente para
`LabelData` antes de montar os campos.

**Justificativa**
Dá segurança de tipos na fronteira entre o domínio de impressão e o motor
de impressão — um nome de campo errado vira `AttributeError` imediato, não
uma etiqueta silenciosamente incorreta. Por ser imutável, uma mesma
instância pode ser compartilhada com segurança entre as N cópias de uma
etiqueta repetida por quantidade. A estrutura foi desenhada para crescer
(código de barras próprio, coleção, peso, fornecedor, QR code, marca) sem
voltar a depender de chaves soltas.

**Consequências**
`PrintQueueAdapter` e `ui/main_window.py` precisaram ser adaptados para
construir `LabelData` explicitamente. Validado que a mudança não altera
nenhum byte da saída ZPL gerada (comparação direta contra a versão
anterior à mudança).

**Data:** 2026-07-21 (`v3.0-stable` — refinamento arquitetural final)

---

## ADR 004 — PrintLayout centraliza todas as constantes físicas

**Contexto**
Constantes de calibração física da etiqueta e do rolo (margens, tamanhos
de fonte, posições de linha, parâmetros de código de barras,
`BATCH_ROW_COLUMNS`/`BATCH_COLUMN_PITCH`) estavam duplicadas entre
`core/zpl_builder.py`, `ui/main_window.py` e `ui/catalog_tab.py` — esta
última chegou a redeclarar localmente os mesmos dois valores já definidos
em `ui/main_window.py`, por não poderem se importar mutuamente.

**Decisão**
Criado `core/print_layout.py` como única fonte de todas as constantes
físicas de layout do sistema. `ZplBuilder` referencia esses valores por
atribuição de classe (nunca redeclara um literal); `ui/main_window.py` e
`ui/catalog_tab.py` importam `BATCH_ROW_COLUMNS`/`BATCH_COLUMN_PITCH`
diretamente do mesmo módulo.

**Justificativa**
Duplicação de constantes físicas é um risco real e silencioso de
regressão: alterar um valor de calibração num lugar e esquecer o outro
produziria etiquetas incorretas sem nenhum erro visível em código.
Centralizar torna explícito que esses números vêm de calibração física
validada em hardware real (ELGIN L42PRO FULL), não de estimativa de
código.

**Consequências**
Qualquer recalibração física futura (nova impressora, novo tamanho de
etiqueta) exige alterar um único módulo. A saída de `build()`/`build_row()`
foi comparada byte a byte contra a versão anterior à centralização —
idêntica em todos os cenários testados.

**Data:** 2026-07-21 (`v3.0-stable` — refinamento arquitetural final)

---

## ADR 005 — CatalogService concentra regras de negócio

**Contexto**
Nas primeiras etapas do Catálogo Integrado, busca, filtro e contadores
foram implementados diretamente dentro de `CatalogTab` (a classe de
interface), misturando lógica de negócio com código Tkinter.

**Decisão**
Toda lógica de busca, filtro (fornecedor/categoria), ordenação,
estatísticas e criação de solicitação de impressão (`create_print_item`)
foi extraída para `core/catalog_service.py` (`CatalogService`).
`CatalogTab` passou a ser presentation-only: lê controles da interface,
chama métodos de `CatalogService` e atualiza tabela/contadores — nunca
decide o que aparece.

**Justificativa**
Separar regra de negócio de apresentação permite testar toda a lógica de
busca/filtro/ordenação sem instanciar Tkinter, e evita que a interface
tome decisões que deveriam ser do domínio (ex.: qual é o critério de
"filtro combinado" entre pesquisa, fornecedor e categoria).

**Consequências**
Qualquer novo critério de busca, filtro, ordenação ou estatística é um
método novo em `CatalogService`, nunca lógica dentro de um handler de
botão ou de um `trace` de variável Tkinter.

**Data:** 2026-07-21 (etapa de extração de `CatalogService`, dentro do
ciclo do Catálogo Integrado)

---

## ADR 006 — CatalogRepository é responsável apenas por acesso aos dados

**Contexto**
O Catálogo Integrado precisa oferecer pesquisa e filtro instantâneos sobre
potencialmente milhares de produtos. Reler o arquivo Excel a cada tecla
digitada na busca seria lento e desnecessário, além de arriscar
comportamento inconsistente se a planilha mudasse no meio de uma sessão de
uso.

**Decisão**
`CatalogRepository` é o único ponto do sistema que toca a `DataSource`
(hoje `ExcelCatalogSource`). Suas operações `load()`/`reload()` são as
únicas que efetivamente leem/releem a origem; `repository.products`
sempre expõe a lista já carregada em memória (cache). Nenhuma outra
camada — `CatalogService`, `CatalogTab` ou qualquer teste — acessa a
`DataSource` diretamente.

**Justificativa**
Um cache em memória previsível e testável separa claramente "de onde vêm
os dados" de "o que fazer com eles" (`CatalogService`). O comportamento foi
comprovado em testes com um `FakeDataSource` que conta quantas vezes cada
operação de leitura é chamada, provando que pesquisa/filtro/ordenação
nunca disparam I/O.

**Consequências**
Pesquisa, filtro e ordenação são sempre operações em memória, instantâneas
independentemente do tamanho do catálogo. Só um clique explícito em
"Recarregar Catálogo" relê a planilha. Uma futura troca de origem de dados
(ex.: banco de dados) só precisa implementar a mesma interface
`DataSource`, sem alterar `CatalogService` nem a interface.

**Data:** 2026-07-21 (etapa de carregamento em memória + cache, dentro do
ciclo do Catálogo Integrado)

---

## ADR 007 — PrintQueueAdapter adapta dados sem regras de impressão

**Contexto**
Ao conectar `PrintQueue` ao motor de impressão existente (ADR 001), era
necessário converter `PrintItem` para o formato que `build_row()` espera.
Havia o risco de essa conversão absorver, por conveniência, regras que na
verdade pertencem ao motor de impressão (agrupamento em colunas, largura
do rolo) ou ao envio para a impressora.

**Decisão**
`PrintQueueAdapter` tem responsabilidade única: `PrintQueue ->
list[LabelData]`. Nenhuma regra de agrupamento em colunas, largura de
rolo, envio para a impressora, ou qualquer outra lógica de impressão vive
nele — apenas a tradução de um modelo de dados para o outro.

**Justificativa**
Manter a fronteira de conversão isolada permite testá-la de forma
totalmente determinística e sem hardware (sem mockar impressora nem
`ZplBuilder`), e evita que regras de impressão vazem para fora de
`ZplBuilder`/`PrinterService`, onde já vivem de forma centralizada (ADR
001).

**Consequências**
Quem monta o job de impressão de fato (`ui/catalog_tab.py`) é responsável
por agrupar as etiquetas em linhas/colunas e chamar
`build_row()`/`print_raw()`. `PrintQueueAdapter` nunca precisa saber sobre
`BATCH_ROW_COLUMNS`, impressoras ou threads.

**Data:** 2026-07-21 (integração da Fila de Impressão com o pipeline de
impressão existente)

---

## ADR 008 — UI nunca manipula listas internas diretamente

**Contexto**
Ao construir a Fila de Impressão visual (cartões, contadores, botões de
quantidade), havia o risco natural de a interface manter ou alterar
diretamente listas de `PrintItem` (ou de produtos do catálogo) para
renderizar a tela, em vez de sempre passar pelas APIs de domínio já
existentes (`PrintQueue`, `CatalogService`).

**Decisão**
A interface nunca acessa uma lista de `PrintItem` ou de produtos do
catálogo diretamente. Toda leitura passa por métodos públicos que já
devolvem o estado pronto (`PrintQueue.to_list()`/iteração,
`CatalogService.apply_filters()`), e toda escrita passa por métodos que
representam uma intenção de negócio (`add`/`remove`/`clear`/`increment`/
`decrement`/`update_quantity` em `PrintQueue`; `search`/`filter_*`/
`sort_by` em `CatalogService`) — nunca por manipulação de índice ou
mutação de lista solta na camada de UI.

**Justificativa**
Garante que domínio e apresentação evoluam de forma independente: a
interface pode ser redesenhada (novo layout de cartão, nova disposição de
botões) sem risco de quebrar invariantes do domínio (ex.: quantidade nunca
menor que 1, sem duplicar produto na fila). Também mantém o domínio
testável sem depender de Tkinter.

**Consequências**
Cada nova ação da interface (um botão novo, um atalho novo) precisa ter um
método correspondente no domínio antes de existir na tela — nunca lógica
ad-hoc manipulando listas dentro de um handler de evento.

**Data:** 2026-07-21 (separação de domínio e `PrintQueue` rica; reforçada
durante a construção da Fila de Impressão visual e sua integração com o
pipeline de impressão)

---

## ADR 009 — Arquitetura congelada na v3.0

**Contexto**
Depois do ciclo completo do Catálogo Integrado — infraestrutura,
carregamento em memória, extração de `CatalogService`, separação de
domínio (`PrintItem`/`PrintQueue`), Fila de Impressão visual e editável, e
integração com o pipeline de impressão existente — e de uma rodada final
de refinamento (`PrintLayout`, `LabelData`) para eliminar toda duplicação
remanescente entre as duas telas, o projeto atingiu um estado em que
catálogo, fila e impressão convergem para um único motor, sem lógica nem
constantes duplicadas.

**Decisão**
A arquitetura do Santa Rubi Label Studio é declarada oficialmente
congelada na versão `v3.0-stable`, documentada formalmente em
`ARCHITECTURE.md`, `CHANGELOG.md`, `ROADMAP.md`, `DOCUMENTACAO_CHECKPOINT.md`
e neste registro de decisões. A partir deste ponto, mudanças devem ser
evolução incremental sobre essa base — não refatoração recorrente da
mesma arquitetura.

**Justificativa**
Reduzir o risco de churn arquitetural contínuo e dar uma base estável e
documentada para que as próximas prioridades — confiabilidade, manutenção,
funcionalidades administrativas e distribuição do sistema, já anunciadas
desde `v1.3-produtividade` — possam ser endereçadas sem reabrir decisões
já validadas fisicamente e por testes.

**Consequências**
Qualquer mudança futura que exigisse duplicar `ZplBuilder`,
`PrinterService`, ou uma constante de `core/print_layout.py` deve ser
tratada como um sinal de alerta arquitetural, não como solução — e, se
uma dessas decisões precisar mesmo ser revista, isso deve gerar um novo
ADR que referencie explicitamente qual destes é superado, e por quê.

**Data:** 2026-07-21 (tag `v3.0-stable`)
