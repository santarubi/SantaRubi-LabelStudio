# Label Studio Architecture Guide

Versão da Arquitetura: 2.0 (revisada por auditoria de código)

Última atualização: Julho/2026

Este documento define a arquitetura oficial do Santa Rubi Label Studio,
**conferida diretamente contra o código-fonte** (não contra a versão
anterior deste guia). Divergências encontradas entre a versão anterior e o
código estão documentadas em `ARCHITECTURE_AUDIT.md`.

Toda alteração estrutural deve respeitar este documento.

Caso exista conflito entre uma solicitação futura e este guia, este guia
deve prevalecer até que seja oficialmente atualizado.

Este documento deve ser lido antes de qualquer implementação.

---

# Objetivo do Sistema

O Santa Rubi Label Studio é um sistema desktop Windows (Python 3.12,
Tkinter/ttk) desenvolvido para gerenciamento da impressão de etiquetas da
Santa Rubi Semijoias.

Seu objetivo é centralizar todas as operações relacionadas à impressão de
etiquetas de produtos provenientes da **Planilha Excel** e da **API
Jueri**.

O sistema não realiza precificação.

O sistema não substitui o ERP Jueri.

O sistema não realiza cadastro de produtos.

Seu único objetivo é organizar, preparar e imprimir etiquetas.

---

# Estrutura real da interface

O programa abre uma única janela (`ui/main_window.py`, classe
`MainWindow`), com um cabeçalho fixo (título + botão "Configurações") e um
`ttk.Notebook` com exatamente duas abas:

1. **"API Jueri"** — construída inteiramente dentro de `MainWindow`
   (`_build_jueri_tab`). Painel de status da integração, resumo da fila de
   impressão, pesquisas favoritas, pesquisas recentes e a tabela
   "Resultado da Última Pesquisa". A pesquisa em si acontece numa janela
   modal separada, `ProductSearchDialog` (`ui/product_search_dialog.py`).
2. **"Planilha Excel"** — implementada em `ui/catalog_tab.py`, classe
   `CatalogTab`, instanciada por `MainWindow`. Contém a configuração da
   fonte de dados (arquivo, abas, mapeamento de colunas), a tabela do
   catálogo e o painel **Fila de Impressão**.

Não existem mais abas chamadas "Impressão" ou "Catálogo Integrado" — essa
nomenclatura pertence a uma versão anterior do produto e não deve ser usada
como referência para código atual.

---

# Princípios da Arquitetura

## Fonte de dados

Existem apenas duas origens oficiais de produto:

- **Planilha Excel** — lida via `core/catalog_excel_source.py`
  (`ExcelCatalogSource`), orquestrada por `core/catalog_repository.py`
  (`CatalogRepository`) e `core/catalog_service.py` (`CatalogService`).
- **API Jueri** — consultada via `app/api/products.py` (`ProductsAPI`),
  através do cliente HTTP `app/api/client.py` (`JueriClient`).

Nenhuma outra origem deve ser criada sem alteração desta arquitetura.

> Nota técnica (ver `ARCHITECTURE_AUDIT.md`, seção 17): existe também
> `core/excel_reader.py` (`ExcelReader`), um segundo leitor de Excel mais
> simples, hoje sem nenhum chamador em `ui/`. Ele pertencia à antiga aba
> "Impressão" e não faz parte do fluxo atual — não deve ser confundido com
> `ExcelCatalogSource`, que é o leitor realmente usado hoje.

## Convergência para um único modelo de produto

Independentemente da origem, todo produto vira um `CatalogProduct`
(`core/catalog_product.py`) antes de qualquer outra etapa:

- Do Excel: `CatalogRepository._to_product()`.
- Da API Jueri: `Product.to_catalog_product()` (`app/api/product.py`).

A partir desse ponto, nenhuma camada seguinte (fila, adaptador, motor de
impressão) sabe ou precisa saber de onde o produto veio.

## Impressão

Toda impressão acontece exclusivamente através da `PrintQueue`
(`core/print_queue.py`) — uma única instância, criada dentro de
`CatalogTab.__init__` (`self.print_queue = PrintQueue()`) e referenciada
por `MainWindow` como `self.catalog_tab.print_queue`.

Nenhuma tela imprime diretamente. O caminho real, confirmado em código, é:

```
CatalogProduct → PrintItem → PrintQueue → PrintQueueAdapter
    → LabelData → ZplBuilder.build_row() → PrinterService.print_raw()
    → spooler RAW do Windows → impressora
```

`ZplBuilder` (`core/zpl_builder.py`) e `PrinterService`
(`core/printer.py`) são os únicos módulos que geram/enviam comandos de
impressão. Todas as constantes físicas (dimensão da etiqueta, margens,
posições, tamanhos de fonte, colunas do rolo) vêm exclusivamente de
`core/print_layout.py`.

## API Jueri

A API Jueri é utilizada apenas para consulta (`ProductsAPI.search_products`,
`search_multiple_products`, `search_all_pages`) e resolução de categoria
(`CategoriesAPI`). Não existe, em código, nenhum caminho que envie dados de
volta para a API Jueri (nenhum `POST`/`PUT` foi encontrado em uso — apenas
`JueriClient.post()` existe como método genérico, sem chamador).

Ela nunca substitui a Planilha Excel como fluxo operacional principal, e
nunca imprime diretamente: produtos escolhidos em `ProductSearchDialog` são
convertidos para `CatalogProduct` e entregues à mesma `PrintQueue` via
`CatalogTab.add_product_to_queue()`.

## Planilha Excel

A Planilha Excel continua sendo o fluxo principal de trabalho:

```
Fornecedor → Precificação → Impressão → Cadastro no Jueri
```

(Este fluxo de negócio não é verificável diretamente pelo código — é
contexto operacional da empresa, documentado em
`docs/ai/02_PROJECT_CONTEXT.md`.)

## Fluxo único

Independentemente da origem — Excel ou API Jueri —, os produtos convergem
para uma única fila de impressão (`PrintQueue`). Isso é verificável em
código: `MainWindow` nunca instancia `PrintQueue()`; sempre usa a instância
já existente em `self.catalog_tab.print_queue`.

---

# Regras Imutáveis

Nunca duplicar lógica de impressão — `ZplBuilder`/`PrinterService` são os
únicos módulos que fazem isso.

Nunca criar uma segunda fila — `PrintQueue` é única, dentro de `CatalogTab`.

Nunca permitir impressão direta pela API — todo produto Jueri passa por
`to_catalog_product()` e pela fila antes de qualquer impressão.

Nunca alterar `PrintQueue` sem revisão arquitetural.

Nunca alterar `Product` (`app/api/product.py`) e `CatalogProduct`
(`core/catalog_product.py`) para atender necessidades específicas de
interface.

Toda melhoria de UX deve preservar a arquitetura existente.

---

# Filosofia de Desenvolvimento

Toda nova funcionalidade deve:

- reutilizar componentes existentes (ex.: `core/column_sort.py`,
  `ui/treeview_selection.py`, `ui/toast.py` e `core/table_state.py` já são
  compartilhados entre a pesquisa Jueri e o catálogo — qualquer tela nova
  com tabela deve reaproveitá-los, não recriar a mesma lógica);
- evitar duplicação;
- preservar testes (541 testes em `tests/`, `unittest`, executados via
  `python -m unittest discover -s tests -p "test_*.py"`);
- preservar arquitetura;
- ser implementada em pequenas sprints;
- possuir testes automatizados.
