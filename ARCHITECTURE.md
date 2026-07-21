# Arquitetura — Santa Rubi Label Studio (v3.0-stable)

Este documento descreve a arquitetura técnica atual do sistema: camadas,
responsabilidade de cada módulo, fluxo de dados e regras que devem ser
respeitadas em qualquer evolução futura. Para o histórico de *como* se
chegou a esta arquitetura, ver [DOCUMENTACAO_CHECKPOINT.md](DOCUMENTACAO_CHECKPOINT.md).
Para o resumo de funcionalidades por versão, ver [CHANGELOG.md](CHANGELOG.md).

## 1. Visão geral

O Santa Rubi Label Studio é uma aplicação desktop Windows (Python 3.12,
Tkinter/ttk) com duas telas (abas) que resolvem problemas diferentes mas
compartilham o mesmo motor de impressão:

- **Aba "Impressão"** (`ui/main_window.py`) — fluxo direto a partir de uma
  planilha Excel pontual: pesquisa, seleção, impressão unitária/lote/
  selecionados.
- **Aba "Catálogo Integrado"** (`ui/catalog_tab.py`) — catálogo permanente
  e configurável, com uma Fila de Impressão própria que o usuário monta
  antes de imprimir tudo de uma vez.

As duas abas nunca reimplementam impressão: ambas terminam no mesmo
`ZplBuilder.build_row()` + `PrinterService.print_raw()`. Esse é o princípio
arquitetural mais importante do projeto — **existe apenas um motor de
impressão** — e é verificado nos testes e reforçado em cada etapa de
evolução.

## 2. Arquitetura em camadas

```
┌─────────────────────────────────────────────────────────────────┐
│  UI (Tkinter/ttk)                                                │
│  ui/main_window.py            ui/catalog_tab.py                  │
│  (aba "Impressão")             (aba "Catálogo Integrado")         │
└──────────────┬──────────────────────────┬────────────────────────┘
               │                          │
               │                          ▼
               │                 ┌────────────────────┐
               │                 │  Domínio do catálogo │
               │                 │  CatalogRepository   │
               │                 │  CatalogService       │
               │                 │  CatalogProduct        │
               │                 └──────────┬────────────┘
               │                          │
               │                          ▼
               │                 ┌────────────────────┐
               │                 │  Domínio de impressão│
               │                 │  PrintItem            │
               │                 │  PrintQueue            │
               │                 └──────────┬────────────┘
               │                          │
               │                          ▼
               │                 ┌────────────────────┐
               │                 │  PrintQueueAdapter    │
               │                 └──────────┬────────────┘
               │                          │
               ▼                          ▼
        ┌──────────────────────────────────────┐
        │           LabelData (tipado)           │
        └──────────────────┬─────────────────────┘
                            ▼
                  ┌───────────────────┐
                  │   ZplBuilder        │◄── core/print_layout.py
                  │  (build/build_row)  │    (constantes físicas)
                  └─────────┬───────────┘
                            ▼
                  ┌───────────────────┐
                  │   PrinterService    │
                  │   (print_raw)        │
                  └─────────┬───────────┘
                            ▼
                      ELGIN L42PRO FULL
```

Em paralelo, e completamente desacoplado do caminho acima, existe o
**pipeline de pré-visualização** (`LabelRenderer` + `core/barcode.py`),
usado só pela aba "Impressão" para desenhar um bitmap em tela. Ele nunca
importa `ZplBuilder`/`PrinterService`, e vice-versa.

## 3. Responsabilidades de cada módulo

### Camada de impressão (compartilhada pelas duas abas)

| Módulo | Responsabilidade |
|---|---|
| `core/print_layout.py` | Única fonte de constantes físicas de layout (dimensões da etiqueta, margens, código de barras, posições de linha, fontes, colunas do rolo). Nenhum outro módulo declara esses valores — todos importam daqui. |
| `core/label_data.py` | `LabelData` — dataclass `frozen`, representa uma etiqueta pronta para o motor de impressão (`codigo`, `descricao`, `categoria`, `numero`, `preco`). Extensível para campos futuros (código de barras próprio, coleção, peso, fornecedor, QR code, marca). |
| `core/zpl_builder.py` | `ZplBuilder` — monta o comando ZPL (`^XA...^XZ`) a partir de `LabelData` (`build_row()`) ou de um `dict` (`build()`, usado pela impressão unitária/teste). Não desenha nada; gera texto que a própria impressora interpreta. Não fala com a impressora nem sabe de `PrintQueue`/catálogo. |
| `core/printer.py` | `PrinterService` — toda a comunicação com o spooler do Windows: listar impressoras, obter a padrão, enviar dados brutos (`print_raw`). Não sabe nada sobre ZPL, produtos ou layout. |

### Domínio de impressão (usado hoje pelo Catálogo Integrado; a aba
"Impressão" ainda monta sua lista de lote diretamente)

| Módulo | Responsabilidade |
|---|---|
| `core/print_item.py` | `PrintItem` — uma solicitação de impressão (`product: CatalogProduct`, `quantity: int`). Quantidade sempre normalizada para inteiro ≥ 1, nunca 0/negativo/texto. |
| `core/print_queue.py` | `PrintQueue` — coleção rica de `PrintItem`. Única classe que manipula a fila; a interface nunca acessa uma lista diretamente. Igualdade de produto por `codigo`, nunca por identidade de objeto. |
| `core/print_queue_adapter.py` | `PrintQueueAdapter.to_label_data()` — converte `PrintQueue` para `list[LabelData]`. Responsabilidade única de conversão; nenhuma regra de impressão. |
| `core/print_log.py` | Log de cada trabalho de impressão da fila (`data/print_log.txt`): horário, produtos, etiquetas, tempo, resultado. |

### Domínio do catálogo (exclusivo da aba "Catálogo Integrado")

| Módulo | Responsabilidade |
|---|---|
| `core/catalog_datasource.py` | `DataSource` — interface abstrata de origem de dados do catálogo. |
| `core/catalog_excel_source.py` | `ExcelCatalogSource` — implementação concreta sobre um arquivo `.xlsx` (múltiplas abas). |
| `core/catalog_repository.py` | `CatalogRepository` — único ponto que lê a `DataSource`; mantém cache em memória (`load()`/`reload()`); nunca relê o Excel para pesquisa/filtro. |
| `core/catalog_product.py` | `CatalogProduct` — entidade permanente do produto (sem quantidade — isso é responsabilidade de `PrintItem`). |
| `core/catalog_service.py` | Busca, filtro (fornecedor/categoria), ordenação, estatísticas, e `create_print_item()` (ponte para o domínio de impressão). |
| `core/catalog_settings.py` | Configuração persistida (`config.json`, chave `catalog_integrado`): arquivo, abas, mapeamento de colunas, estado do painel. |
| `core/catalog_validator.py` | Valida a configuração (arquivo existe, abas existem, todas as colunas mapeadas) e produz um relatório para a interface. |
| `core/text_normalize.py` | Normalização de texto (case/acento-insensível) usada na busca do catálogo. |

### Módulos compartilhados/gerais

| Módulo | Responsabilidade |
|---|---|
| `core/config.py` | Persistência simples de preferências em `data/config.json`. |
| `core/excel_reader.py` | Leitura/validação da planilha usada pela aba "Impressão" (independente do Catálogo Integrado). |
| `core/barcode.py` / `core/label_renderer.py` | Pipeline de pré-visualização (bitmap) — só usado pela aba "Impressão"; nunca pelo caminho de impressão real. |

### Interface

| Módulo | Responsabilidade |
|---|---|
| `ui/main_window.py` | Janela principal + aba "Impressão" completa (tabela, pesquisa, seleção, preview, impressão unitária/lote/selecionados). |
| `ui/catalog_tab.py` | Aba "Catálogo Integrado": configuração, tabela do catálogo, painel da Fila de Impressão, botão "Imprimir Fila". Camada de apresentação pura — nenhuma regra de negócio do catálogo vive aqui (tudo em `CatalogService`), e nenhuma regra de impressão (tudo em `ZplBuilder`/`PrinterService`, via `PrintQueueAdapter`). |

## 4. Pipeline de impressão

Ponto único de convergência das duas abas:

```
LabelData (um por etiqueta)
        │
        ▼
ZplBuilder.build_row(labels, column_pitch=BATCH_COLUMN_PITCH,
                      total_width=BATCH_COLUMN_PITCH * BATCH_ROW_COLUMNS)
        │  (agrupado em blocos de BATCH_ROW_COLUMNS, hoje 3 — calibração
        │   física do rolo, vive em core/print_layout.py)
        ▼
   comando ZPL (^XA...^XZ)
        │
        ▼
PrinterService(printer_name).print_raw(zpl)
        │
        ▼
   spooler RAW do Windows
        │
        ▼
   ELGIN L42PRO FULL
```

- `ZplBuilder.build()` (etiqueta única, a partir de um `dict`) é usado pela
  impressão de teste/unitária/rápida da aba "Impressão" — continua
  aceitando `dict` por compatibilidade, convertendo para `LabelData`
  internamente antes de montar os campos.
- `ZplBuilder.build_row()` (uma ou mais etiquetas lado a lado, a partir de
  `list[LabelData]`) é usado pela impressão em lote de ambas as abas.
- Nenhuma lógica de posicionamento, truncamento ou geração de ZPL existe
  fora de `ZplBuilder` — se um dia mudar de impressora/firmware, este é o
  único módulo que precisa mudar.

## 5. Fluxo do Catálogo Integrado

```
Excel (1+ abas)
    │
    ▼
ExcelCatalogSource ──► CatalogRepository (load/reload; cache em memória)
                              │
                              ▼
                        CatalogProduct (lista)
                              │
                              ▼
                        CatalogService
                (search / filter_supplier / filter_category /
                 sort_by / apply_filters / get_statistics)
                              │
                              ▼
                        CatalogTab (tabela — só apresentação)
                              │
                    usuário seleciona produtos
                              │
                              ▼
              CatalogService.create_print_item(product)
           (usa a quantidade padrão configurada na coluna QTD)
                              │
                              ▼
                          PrintItem
                              │
                              ▼
                    PrintQueue.add() / increment()
              (sem duplicar — incrementa se já existir)
                              │
                              ▼
                  Fila de Impressão (painel lateral)
        (remover, limpar, [-]/[+], edição direta, DEL, Ctrl+A)
                              │
                    usuário clica "Imprimir Fila"
                              │
                              ▼
                    PrintQueueAdapter.to_label_data()
                              │
                              ▼
                  (entra no pipeline de impressão — Capítulo 4)
```

## 6. PrintQueue

Coleção rica — a única classe que manipula a fila de impressão. A
interface nunca acessa uma lista de `PrintItem` diretamente.

- **Básico**: `add(product, quantity)`, `remove(product)`, `clear()`,
  `items()` / `to_list()`, `count()`, `total_labels()`, `is_empty()`.
- **Consulta**: `contains(product)`, `find(product)`.
- **Edição em lugar**: `update_quantity(product, quantity)` (não cria item
  novo se o produto não existir — retorna `False`), `increment(product,
  amount=1)`, `decrement(product, amount=1)` (nunca abaixo de 1).
- **Substituição em bloco**: `replace(items)` — pensado para futuras
  importações/duplicação de itens.
- **Protocolos Python**: `__len__`, `__iter__`, `__contains__` (`len(queue)`,
  `for item in queue`, `product in queue`).
- **Igualdade**: dois itens são o mesmo produto quando têm o mesmo
  `codigo` — nunca por identidade de objeto.

## 7. PrintQueueAdapter

Responsabilidade única: `PrintQueueAdapter.to_label_data(queue) ->
list[LabelData]`. Expande cada `PrintItem` em N `LabelData` idênticos
(N = quantidade), usando `product.display_category` (não `categoria`
bruta, para permitir indireção futura) e `product.numeracao`. Nenhuma
regra de impressão (agrupamento em colunas, largura de rolo, envio para a
impressora) vive aqui.

## 8. LabelData

`@dataclass(frozen=True)` com os campos `codigo`, `descricao`, `categoria`,
`numero`, `preco`. Substitui o `list[dict]` que antes atravessava a
fronteira entre `PrintQueueAdapter` e `ZplBuilder.build_row()`: dá
segurança de tipos (erros de nome de campo viram `AttributeError` em vez
de silenciosamente produzir uma etiqueta em branco) e, por ser imutável,
a mesma instância pode ser compartilhada com segurança entre as N cópias
de uma etiqueta repetida por quantidade. Estrutura pensada para crescer
(código de barras próprio, coleção, peso, fornecedor, QR code, marca) sem
voltar a depender de chaves de dicionário soltas.

## 9. PrintLayout

`core/print_layout.py` é a única fonte de todas as constantes físicas de
layout do sistema: dimensões da etiqueta (`LABEL_WIDTH_DOTS`/
`LABEL_HEIGHT_DOTS`), margens, parâmetros do código de barras (Code128,
Start Code C), posição Y de cada linha de campo, tamanho de fonte de cada
campo, truncamento de descrição (`DESCRIPTION_MAX_CHARS`/
`DESCRIPTION_RIGHT_MARGIN`), e a calibração do rolo de etiquetas
(`BATCH_ROW_COLUMNS = 3`, `BATCH_COLUMN_PITCH = 264`). `ZplBuilder`
referencia esses valores por atribuição de classe (nunca redeclara um
literal); `ui/main_window.py` e `ui/catalog_tab.py` importam
`BATCH_ROW_COLUMNS`/`BATCH_COLUMN_PITCH` diretamente daqui.

## 10. ZplBuilder

Ver Capítulo 3 (camada de impressão) e Capítulo 4 (pipeline). Resumo:
monta o comando ZPL como texto puro, sem nenhuma dependência de Pillow,
Tkinter, `win32print` ou do domínio do catálogo/fila. `build()` aceita
`dict` (compatibilidade com a impressão unitária da aba "Impressão");
`build_row()` aceita `list[LabelData]`.

## 11. PrinterService

`core/printer.py`. Comunicação exclusiva com o spooler de impressão do
Windows via `win32print`: `list_printers()`, `get_default_printer()`,
`print_raw(data, copies=1)` — envia dados brutos (o comando ZPL) sem
passar pelo driver GDI. Não sabe nada sobre ZPL, `LabelData`, catálogo ou
fila — só envia bytes para uma impressora nomeada.

## 12. Regras arquiteturais

1. **Existe apenas um motor de impressão.** `ZplBuilder` e `PrinterService`
   nunca são duplicados; qualquer novo ponto de impressão deve reutilizá-
   los diretamente.
2. **Constantes físicas vivem só em `core/print_layout.py`.** Nenhum
   módulo declara um valor de layout próprio.
3. **`CatalogProduct` nunca tem quantidade.** Quantidade é sempre uma
   propriedade de `PrintItem` (a intenção de imprimir), nunca do produto
   em si.
4. **A interface nunca manipula listas de `PrintItem` diretamente.** Toda
   leitura/escrita da fila passa pelos métodos públicos de `PrintQueue`.
5. **`PrintQueueAdapter` só converte dados.** Nenhuma regra de impressão
   (colunas, largura, envio) vive nele.
6. **`CatalogRepository` é o único ponto que lê a `DataSource`.** Pesquisa,
   filtro e ordenação operam sempre sobre o cache em memória.
7. **Preview e impressão são pipelines independentes.** `LabelRenderer`
   nunca importa `ZplBuilder`/`PrinterService`, e vice-versa.
8. **Toda operação de impressão da fila roda em thread separada** e nunca
   perde a fila em caso de erro — só o usuário, explicitamente, decide
   limpá-la.

## 13. Dependências entre módulos

```
core/print_layout.py       ← não depende de nada do projeto
core/label_data.py          ← não depende de nada do projeto
core/zpl_builder.py         ← print_layout, label_data
core/printer.py              ← (só win32print)
core/print_item.py           ← catalog_product
core/print_queue.py           ← print_item, catalog_product
core/print_queue_adapter.py    ← print_queue, label_data
core/print_log.py               ← (só stdlib)

core/catalog_datasource.py       ← não depende de nada do projeto
core/catalog_excel_source.py      ← catalog_datasource
core/catalog_product.py            ← text_normalize
core/catalog_repository.py          ← catalog_datasource, catalog_product, catalog_settings
core/catalog_service.py              ← catalog_repository, catalog_product, catalog_settings, print_item
core/catalog_settings.py              ← não depende de nada do projeto
core/catalog_validator.py              ← catalog_datasource, catalog_settings

ui/main_window.py   ← config, excel_reader, label_renderer, printer,
                       zpl_builder, label_data, print_layout, catalog_tab
ui/catalog_tab.py    ← catalog_* (todos), print_item, print_layout,
                       print_log, print_queue, print_queue_adapter,
                       printer, zpl_builder, label_data, config
```

`ui/main_window.py` e `ui/catalog_tab.py` nunca se importam mutuamente
(o segundo é instanciado pelo primeiro, não o contrário) — por isso
qualquer constante que as duas telas precisem compartilhar deve vir de um
módulo em `core/` (ex.: `print_layout.py`), nunca de uma tela para a
outra.

## 14. Diagrama ASCII da arquitetura (resumo executivo)

```
                         ┌───────────────────┐
                         │   Excel (planilha)  │
                         └─────────┬───────────┘
                                   │
              ┌────────────────────┼────────────────────┐
              ▼                                          ▼
      ExcelReader (aba "Impressão")          ExcelCatalogSource + CatalogRepository
              │                                          │      (Catálogo Integrado)
              ▼                                          ▼
      dict de produto                          CatalogProduct (cache em memória)
              │                                          │
              │                                CatalogService (busca/filtro/ordenação)
              │                                          │
              │                                PrintItem / PrintQueue (fila)
              │                                          │
              │                                PrintQueueAdapter
              │                                          │
              └───────────────────┬──────────────────────┘
                                   ▼
                            LabelData / dict
                                   ▼
                            ZplBuilder
                       (build / build_row)
                        ▲ core/print_layout.py
                                   ▼
                            PrinterService
                             (print_raw)
                                   ▼
                          ELGIN L42PRO FULL
```
