# ARCHITECTURE_AUDIT.md — Santa Rubi Label Studio

**Tipo de documento:** auditoria técnica descritiva, gerada por leitura direta do
código-fonte (não do histórico de commits, não da documentação anterior).
**Branch analisada:** `feature/v3.1` (HEAD em `9201af6`, tag mais recente
`v1.0.0`, working tree com alterações não commitadas).
**Método:** leitura integral de todos os módulos de `core/`, `ui/`, `app/`,
`scripts/`, de todos os 43 arquivos de teste, dos 2 arquivos `.spec` do
PyInstaller, dos 2 scripts `.bat`, e da documentação existente na raiz e em
`docs/`.
**Regra seguida:** toda afirmação abaixo é rastreável a um arquivo, classe,
método ou comentário real do código. Onde isso não foi possível, a seção 17
declara explicitamente a lacuna.

> Divergência importante encontrada logo de saída: a documentação existente
> na raiz do projeto (`README.md`, `ARCHITECTURE.md`, `ROADMAP.md`,
> `CHANGELOG.md`) descreve uma versão anterior do sistema — duas abas
> chamadas "Impressão" e "Catálogo Integrado". **Essa versão não existe mais
> no código.** As abas atuais (ver `ui/main_window.py`) chamam-se **"API
> Jueri"** e **"Planilha Excel"**. Esta auditoria descreve exclusivamente o
> que está no código hoje.

---

## 1. Visão Geral

O Santa Rubi Label Studio é uma aplicação desktop Windows, escrita em Python
3.12 com Tkinter/ttk, cujo único propósito é **preparar e imprimir etiquetas
de produto** (30×15mm, impressora térmica ELGIN L42PRO FULL) a partir de duas
origens de dados:

1. Uma **planilha Excel** de catálogo permanente, configurável pelo usuário
   (múltiplas abas, mapeamento de colunas) — aba **"Planilha Excel"**
   (`ui/catalog_tab.py`, classe `CatalogTab`).
2. A **API Jueri** (sistema ERP externo da empresa), consultada via HTTP —
   aba **"API Jueri"** (parte de `ui/main_window.py`, classe `MainWindow`).

Produtos vindos de qualquer uma das duas origens convergem para a **mesma
fila de impressão** (`core/print_queue.py`, classe `PrintQueue`), e a
impressão em si acontece sempre pelo mesmo motor (`core/zpl_builder.py` +
`core/printer.py`), gerando comandos ZPL enviados como dado bruto (`RAW`)
direto ao spooler do Windows — sem passar pelo driver gráfico (GDI).

O ponto de entrada é `app.py`, que cria uma única janela Tkinter
(`ui.main_window.MainWindow`) contendo um `ttk.Notebook` com as duas abas
citadas. Não há banco de dados: toda persistência é um único arquivo
`config.json` em `%LOCALAPPDATA%/Santa Rubi Label Studio/` (ver seção 14).

Existe também uma ferramenta de desenvolvimento separada, o **Launcher**
(`scripts/launcher.py`), que recompila o executável automaticamente quando o
código-fonte muda e depois abre o programa — não faz parte do produto final
para o usuário, é uma conveniência de desenvolvimento/build.

---

## 2. Estrutura de Pastas

Levantada diretamente do sistema de arquivos (não de um índice antigo):

```
SantaRubi-LabelStudio/
├── app.py                          # Ponto de entrada (cria MainWindow e chama mainloop)
├── requirements.txt                 # openpyxl, Pillow, python-barcode, reportlab, pywin32
├── CLAUDE.md                        # Regras de desenvolvimento do projeto (para IAs/devs)
├── README.md / ARCHITECTURE.md /
│   ROADMAP.md / CHANGELOG.md /
│   DOCUMENTACAO_CHECKPOINT.md       # Documentação legada — descreve uma versão anterior
│                                     # do produto (abas "Impressão"/"Catálogo Integrado").
│                                     # Ver nota de divergência no topo deste documento.
├── ARCHITECTURE_AUDIT.md            # Este documento
├── Santa Rubi Label Studio.spec     # Spec do PyInstaller para o app principal
├── Santa Rubi Launcher.spec         # Spec do PyInstaller para o Launcher de desenvolvimento
│
├── app/                              # Integração com sistemas externos
│   ├── __init__.py
│   └── api/                           # Cliente da API Jueri
│       ├── __init__.py                 # Reexporta a API pública do pacote
│       ├── auth.py                      # JueriCredentials (config.json, chave "jueri")
│       ├── client.py                     # JueriClient — HTTP via urllib (stdlib)
│       ├── exceptions.py                  # Hierarquia de exceções JueriError
│       ├── connection_test.py              # test_connection() — usado em Configurações
│       ├── categories.py                    # CategoriesAPI — resolve nome de categoria
│       ├── product.py                        # Product, ProductPrice (modelo da API)
│       ├── products.py                        # ProductsAPI — busca de produtos
│       ├── date_filters.py                    # Conversão de datas BR -> ISO para a API
│       └── debug_log.py                       # Log opcional de diagnóstico HTTP
│
├── core/                              # Lógica de negócio — nenhum import de Tkinter aqui
│   ├── config.py                       # ConfigManager — persistência em config.json
│   ├── catalog_datasource.py            # DataSource — interface abstrata
│   ├── catalog_excel_source.py           # ExcelCatalogSource — implementação sobre .xlsx
│   ├── catalog_repository.py              # CatalogRepository — cache em memória
│   ├── catalog_product.py                  # CatalogProduct — entidade permanente do catálogo
│   ├── catalog_service.py                   # CatalogService — busca/filtro/ordenação/estatística
│   ├── catalog_settings.py                   # CatalogSettings — config. persistida do catálogo
│   ├── catalog_validator.py                   # CatalogConfigurationValidator
│   ├── print_item.py                           # PrintItem — solicitação de impressão
│   ├── print_queue.py                           # PrintQueue — fila de impressão (coleção rica)
│   ├── print_queue_adapter.py                    # PrintQueueAdapter -> list[LabelData]
│   ├── print_log.py                               # Log de trabalhos de impressão
│   ├── print_layout.py                             # Única fonte de constantes físicas de layout
│   ├── label_data.py                                # LabelData — etiqueta tipada (frozen)
│   ├── zpl_builder.py                                # ZplBuilder — geração do comando ZPL
│   ├── printer.py                                     # PrinterService — win32print RAW
│   ├── text_normalize.py                               # normalize_search_text/parse_multiple_codes
│   ├── column_sort.py                                   # ColumnSorter/sort_items (ordenação genérica)
│   ├── table_state.py                                    # Persistência de largura/ordenação de tabela
│   ├── queue_feedback.py                                  # Mensagem de feedback da fila (texto puro)
│   ├── excel_reader.py                                     # ExcelReader — ⚠ ver seção 17 (órfão)
│   ├── barcode.py                                           # BarcodeGenerator — ⚠ ver seção 17 (órfão)
│   └── label_renderer.py                                     # LabelRenderer — ⚠ ver seção 17 (órfão)
│
├── ui/                                 # Interface Tkinter/ttk
│   ├── main_window.py                    # MainWindow — janela raiz + aba "API Jueri"
│   ├── catalog_tab.py                     # CatalogTab — aba "Planilha Excel" + Fila de Impressão
│   ├── product_search_dialog.py            # ProductSearchDialog — janela modal de pesquisa Jueri
│   ├── settings_dialog.py                   # SettingsDialog — configuração da integração Jueri
│   ├── treeview_selection.py                 # enable_drag_selection — seleção por arraste (Treeview)
│   └── toast.py                               # Toast — feedback discreto e temporário
│
├── scripts/                             # Ferramentas de build/desenvolvimento
│   ├── launcher.py                        # Janela do Launcher de desenvolvimento
│   ├── build_runner.py                     # Executa scripts/build.bat sem janela de CMD
│   ├── project_signature.py                 # Hash do código-fonte, decide se precisa recompilar
│   ├── build.bat                             # Build do app principal (PyInstaller)
│   └── build_launcher.bat                     # Build do Launcher (PyInstaller)
│
├── tests/                              # 43 arquivos de teste (unittest), ~541 testes
├── data/                                # config.json / print_log.txt — ⚠ ver seção 17 (parece não usado)
├── assets/                              # Vazio (só .gitkeep) — reservado
├── layouts/                             # Vazio (só .gitkeep) — reservado
├── build/ , dist/                       # Saída do PyInstaller (gerada, não versionada)
└── docs/
    ├── DECISIONS.md                       # ADRs históricos (válidos até v3.0-stable)
    ├── RELEASE_NOTES_v3.0.md               # Notas da versão v3.0-stable (histórico)
    └── ai/                                  # Documentação voltada a uso por IA (reescrita na Etapa 3)
```

---

## 3. Arquitetura Geral

Arquitetura em camadas, sem framework de injeção de dependência — as
dependências são passadas explicitamente pelo construtor (composição manual).

```
┌───────────────────────────────────────────────────────────────────┐
│  UI (Tkinter/ttk) — ui/                                             │
│  MainWindow (aba "API Jueri")     CatalogTab (aba "Planilha Excel")  │
│  ProductSearchDialog · SettingsDialog · Toast · treeview_selection    │
└───────────┬──────────────────────────────────┬───────────────────────┘
            │                                  │
            ▼                                  ▼
   ┌──────────────────┐              ┌──────────────────────┐
   │ Integração Jueri   │              │  Domínio do catálogo   │
   │ app/api/*           │              │  CatalogRepository       │
   │ (Product, ProductsAPI│              │  CatalogService            │
   │  CategoriesAPI, ...)  │              │  CatalogProduct              │
   └─────────┬────────────┘              └──────────┬───────────────────┘
             │  Product.to_catalog_product()          │
             └─────────────────┬───────────────────────┘
                                ▼
                     ┌────────────────────┐
                     │  Domínio de impressão│
                     │  PrintItem             │
                     │  PrintQueue              │
                     └──────────┬───────────────┘
                                ▼
                     ┌────────────────────┐
                     │  PrintQueueAdapter    │
                     └──────────┬────────────┘
                                ▼
                     ┌────────────────────┐
                     │  LabelData (tipado)   │
                     └──────────┬────────────┘
                                ▼
                     ┌────────────────────┐
                     │  ZplBuilder           │◄── core/print_layout.py
                     │  (build_row)           │    (constantes físicas)
                     └──────────┬────────────┘
                                ▼
                     ┌────────────────────┐
                     │  PrinterService       │
                     │  (print_raw, win32print)│
                     └──────────┬────────────┘
                                ▼
                        Spooler RAW do Windows
                                ▼
                        ELGIN L42PRO FULL
```

Ponto arquitetural central, confirmado em código (não apenas em comentário):
**os dois pontos de entrada de produto (planilha Excel e API Jueri) convergem
para o mesmo `CatalogProduct`**. `Product.to_catalog_product()`
(`app/api/product.py`) converte um produto vindo da API Jueri para um
`CatalogProduct` idêntico, campo a campo, ao que vem do Excel — a partir
desse ponto, nenhum código a jusante (fila, adaptador, impressão) sabe ou
precisa saber de onde o produto veio.

### 3.1 Camadas e regra de dependência

- `core/` nunca importa `tkinter` nem `ui/` (confirmado por leitura de todos
  os arquivos de `core/` — nenhum `import tkinter` encontrado).
- `app/api/` não importa `ui/` nem `tkinter`. Importa apenas `core/`
  (`app/api/product.py` importa `core.catalog_product.CatalogProduct`).
- `ui/` importa de `core/` e de `app/api/`, nunca o inverso.
- `ui/main_window.py` e `ui/catalog_tab.py` **nunca se importam
  mutuamente** — `CatalogTab` é instanciado por `MainWindow`
  (`self.catalog_tab = CatalogTab(self.catalog_tab_frame, ...)`), nunca o
  contrário. Qualquer constante/estado que as duas telas precisem
  compartilhar vem de `core/` (ex.: `core/print_layout.py`) ou é passado
  explicitamente (ex.: `CatalogTab.add_product_to_queue()`, chamado por
  `MainWindow`).

---

## 4. Fluxos

### 4.1 Fluxo "Planilha Excel" (fluxo operacional principal)

```
Usuário configura: arquivo .xlsx, abas, mapeamento de colunas
        │ (CatalogTab._on_select_file / _load_sheets / column_comboboxes)
        ▼
"Testar Configuração" → CatalogConfigurationValidator.validate()
        │ (valida arquivo/abas/colunas sem carregar produtos)
        ▼
"Recarregar Catálogo" → CatalogService.reload() → CatalogRepository.reload()
        │ (única operação que efetivamente lê o Excel — ExcelCatalogSource)
        ▼
CatalogProduct[] em cache de memória (CatalogRepository._products)
        │
        ▼
Pesquisa/filtro/ordenação em tempo real (CatalogService.apply_filters())
        │ (nunca relê o Excel — só filtra a lista em memória)
        ▼
Usuário seleciona linhas → "Adicionar à Fila" (CatalogTab._on_add_to_queue)
        │ CatalogService.create_print_item(product) → PrintItem
        │ PrintQueue.add_or_increment(product, quantity)
        ▼
Fila de Impressão (painel lateral, cartões Tk, não Treeview)
        │ usuário ajusta quantidade ([-]/[+]/edição direta), remove, limpa
        ▼
"Imprimir Fila (Ctrl+P)" → CatalogTab._on_print_queue()
        │ roda em thread separada (_run_queue_print_job)
        ▼
PrintQueueAdapter.to_label_data(queue) → list[LabelData]
        ▼
ZplBuilder.build_row(labels, column_pitch=BATCH_COLUMN_PITCH, ...)
        ▼
PrinterService(printer_name).print_raw(zpl)
        ▼
core.print_log.log_print_job(...) registra o resultado
```

### 4.2 Fluxo "API Jueri"

```
Usuário clica "Pesquisar Produtos (F3)" (MainWindow._on_search_jueri_product)
        │ valida JueriCredentials.from_config(config).enabled
        ▼
Abre ProductSearchDialog (janela modal, grab_set())
        │ ao abrir, já dispara uma busca sem filtro (_run_search)
        │ usuário digita texto, cola lista de códigos, ou usa Data
        │   Inicial/Final + botões "Hoje"/"Ontem"
        ▼
ProductsAPI.search_products() / search_multiple_products() / search_all_pages()
        │ (JueriClient → HTTP GET /api/v1/{cliente_sistema}/produto)
        ▼
Product[] renderizados na tabela do diálogo (ordenável, seleção múltipla,
        seleção por arraste)
        │ usuário seleciona e clica "Adicionar Selecionados"
        ▼
Product.to_catalog_product(categories_api) → CatalogProduct
        │ (para cada produto selecionado)
        ▼
MainWindow._on_jueri_products_selected()
        │  → CatalogTab.add_product_to_queue(catalog_product)
        │    (mesma PrintQueue da aba "Planilha Excel" — nenhuma fila nova)
        │  → espelha o resultado completo da última pesquisa na tabela
        │    "Resultado da Última Pesquisa" da própria aba API Jueri
        │  → NÃO muda de aba automaticamente
        │  → atualiza o resumo "Fila de Impressão" (Produtos/Etiquetas)
        │  → mostra um Toast (não um messagebox) confirmando a adição
        ▼
Usuário decide quando ir manualmente para "Planilha Excel" para imprimir
```

O diálogo de pesquisa (`ProductSearchDialog`) **nunca fecha sozinho** ao
adicionar — só ao clicar "Cancelar" ou pressionar ESC. Isso permite repetir
pesquisa → adicionar quantas vezes o usuário quiser antes de fechar.

### 4.3 Fluxo de impressão (comum às duas origens, a partir da fila)

Ver diagrama da seção 3 — é o mesmo pipeline independentemente de o produto
ter vindo do Excel ou da API Jueri, porque ambos já viraram `CatalogProduct`
antes de chegar na `PrintQueue`.

### 4.4 Fluxo de build/execução (desenvolvimento)

```
scripts/launcher.py (executável de desenvolvimento)
    │ project_signature.compute_signature() — SHA-256 de todo .py/.spec/.txt
    │ compara com dist/build_info.json (signature do último build)
    ▼
Se mudou (ou nunca buildou, ou o .exe sumiu):
    build_runner.run_build() → subprocess "cmd /c scripts/build.bat"
        (CREATE_NO_WINDOW — nenhuma janela de CMD aparece;
         stdin=DEVNULL — não trava no `pause` do .bat)
    ▼ scripts/build.bat → python -m PyInstaller "Santa Rubi Label Studio.spec"
    ▼
Salva dist/build_info.json {version (git describe), built_at, duration, signature}
    ▼
Abre dist/Santa Rubi Label Studio.exe e fecha o Launcher
```

---

## 5. Componentes

Lista dos componentes com estado próprio (classes com responsabilidade
identificável), por camada:

**UI (`ui/`)**
- `MainWindow` — janela raiz; dona do `ttk.Notebook`; implementa a aba "API
  Jueri" inteira (painéis de integração/resumo da fila/favoritos/recentes/
  resultado); orquestra atalhos globais e persistência de interface.
- `CatalogTab` — aba "Planilha Excel"; configuração da fonte de dados,
  tabela do catálogo, painel "Fila de Impressão".
- `ProductSearchDialog` — janela modal de pesquisa de produtos Jueri.
- `SettingsDialog` — janela modal de configuração da integração Jueri
  (habilitar, cliente_sistema, token, testar conexão).
- `Toast` (`ui/toast.py`) — controla um `tk.Label` existente para mostrar
  uma mensagem que se apaga sozinha (usado no lugar de `messagebox`).
- `enable_drag_selection` (`ui/treeview_selection.py`) — função, não classe;
  liga seleção contínua por clique+arraste a qualquer `ttk.Treeview`.

**Domínio do catálogo (`core/`)**
- `CatalogRepository` — cache em memória; único ponto que lê `DataSource`.
- `CatalogService` — busca, filtro, ordenação, estatísticas,
  `create_print_item()`.
- `CatalogProduct` — entidade permanente (dataclass).
- `CatalogSettings` — configuração persistida (dataclass).
- `CatalogConfigurationValidator` / `ValidationReport` / `ValidationIssue`.
- `DataSource` (ABC) / `ExcelCatalogSource` (implementação concreta).

**Domínio de impressão (`core/`)**
- `PrintItem` — solicitação de impressão (produto + quantidade).
- `PrintQueue` — coleção rica da fila.
- `PrintQueueAdapter` — conversão `PrintQueue` → `list[LabelData]`.
- `LabelData` — etiqueta tipada e imutável.
- `ZplBuilder` — geração do comando ZPL.
- `PrinterService` — comunicação com o spooler Windows.

**Integração Jueri (`app/api/`)**
- `JueriClient` — cliente HTTP genérico (urllib).
- `JueriCredentials` — credenciais persistidas.
- `ProductsAPI` / `ProductSearchResult` — busca de produtos.
- `CategoriesAPI` — resolve nome de categoria/subcategoria por id.
- `Product` / `ProductPrice` — modelo de produto da API.
- Hierarquia `JueriError` (`JueriDisabledError`, `JueriAuthenticationError`,
  `JueriConnectionError`, `JueriTimeoutError`, `JueriAPIError`).

**Utilitários genéricos reutilizados por mais de uma tela (`core/`)**
- `ColumnSorter` / `sort_items` / `SortDirection` / `numeric_or_text`
  (`core/column_sort.py`) — ordenação de colunas, usada por
  `ProductSearchDialog`, `CatalogTab` (indiretamente, via `CatalogService`)
  e pela tabela "Resultado da Última Pesquisa" de `MainWindow`.
- `get_column_widths` / `apply_column_widths` / `get_sorter_state` /
  `apply_sorter_state` (`core/table_state.py`) — persistência de estado de
  tabela.
- `describe_queue_addition` (`core/queue_feedback.py`) — texto do `Toast`
  ao adicionar produtos à fila.

**Ferramentas de build (`scripts/`)**
- `LauncherWindow` — janela do Launcher.
- `run_build` / `BuildResult` (`build_runner.py`).
- `compute_signature` / `needs_rebuild` / `load_build_info` /
  `save_build_info` / `current_git_version` (`project_signature.py`).

---

## 6. Dependências

### 6.1 Bibliotecas externas (`requirements.txt`)

```
openpyxl        # leitura de planilhas .xlsx (core/excel_reader.py, core/catalog_excel_source.py)
Pillow          # imagens (core/label_renderer.py, core/barcode.py — ver seção 17, hoje órfãos na UI)
python-barcode  # geração do código de barras do preview (core/barcode.py — idem)
reportlab       # presente no requirements.txt; nenhum import de "reportlab" foi encontrado em
                # nenhum arquivo .py do projeto (ver seção 17)
pywin32         # win32print (core/printer.py) — comunicação RAW com a impressora Windows
```

Bibliotecas da própria stdlib usadas de forma relevante: `tkinter`/`ttk`
(toda a UI), `urllib` (`app/api/client.py` — cliente HTTP da API Jueri,
deliberadamente sem `requests` para não adicionar dependência nova, conforme
comentário no próprio arquivo), `subprocess`, `hashlib`, `json`, `threading`.

### 6.2 Dependências internas entre módulos (resumo)

```
core/print_layout.py        ← nada do projeto
core/label_data.py           ← nada do projeto
core/zpl_builder.py           ← print_layout, label_data
core/printer.py                ← (só win32print)
core/print_item.py              ← catalog_product
core/print_queue.py               ← print_item, catalog_product
core/print_queue_adapter.py         ← print_queue, label_data
core/print_log.py                     ← config (APP_DATA_DIR)
core/column_sort.py                     ← text_normalize
core/table_state.py                       ← column_sort
core/queue_feedback.py                      ← nada do projeto

core/catalog_datasource.py     ← nada do projeto
core/catalog_excel_source.py     ← catalog_datasource
core/catalog_product.py            ← text_normalize
core/catalog_repository.py           ← catalog_datasource, catalog_excel_source (normalize_header),
                                        catalog_product, catalog_settings
core/catalog_service.py                ← catalog_product, catalog_repository, catalog_settings,
                                          column_sort, print_item, text_normalize
core/catalog_validator.py                ← catalog_datasource, catalog_excel_source, catalog_settings

app/api/auth.py                 ← exceptions
app/api/client.py                 ← auth, exceptions
app/api/debug_log.py                ← config (APP_DATA_DIR), exceptions
app/api/connection_test.py            ← auth, client, debug_log, exceptions
app/api/categories.py                   ← client
app/api/product.py                        ← catalog_product, categories
app/api/products.py                         ← client, product
app/api/date_filters.py                       ← nada do projeto (só stdlib)

ui/toast.py                      ← nada do projeto
ui/treeview_selection.py           ← nada do projeto
ui/settings_dialog.py                ← app.api.auth, app.api.connection_test, core.config
ui/product_search_dialog.py            ← app.api.date_filters, app.api.exceptions, app.api.product,
                                          app.api.products, core.column_sort, core.text_normalize,
                                          ui.treeview_selection
ui/catalog_tab.py                        ← core.catalog_* (todos), core.print_item, core.print_layout,
                                            core.print_log, core.print_queue, core.print_queue_adapter,
                                            core.printer, core.queue_feedback, core.table_state,
                                            core.zpl_builder, ui.toast, ui.treeview_selection
ui/main_window.py                          ← app.api.* (auth, categories, client, connection_test,
                                              date_filters, product, products), core.column_sort,
                                              core.config, core.queue_feedback, core.table_state,
                                              ui.catalog_tab, ui.product_search_dialog,
                                              ui.settings_dialog, ui.toast, ui.treeview_selection
```

`core/excel_reader.py`, `core/label_renderer.py` e `core/barcode.py` não
aparecem nas cadeias acima porque, hoje, **nenhum módulo de `ui/` os
importa** — ver seção 17.

---

## 7. Módulos

Ver a tabela completa de responsabilidades na seção 8. Contagem por pasta
(arquivos `.py`, sem contar testes): `core/` = 24, `ui/` = 6, `app/api/` = 9
(+ `app/__init__.py`), `scripts/` = 3 (+ 2 `.bat`), raiz = 1 (`app.py`).
Total de 43 módulos de produção (`core/ + ui/ + app/ + scripts/`, contagem
por `find ... -name "*.py" | wc -l`), mais 43 arquivos de teste.

---

## 8. Responsabilidades

### 8.1 `core/` — domínio, sem Tkinter

| Módulo | Classe/função principal | Responsabilidade |
|---|---|---|
| `config.py` | `ConfigManager` | Ler/gravar `config.json` em `%LOCALAPPDATA%/Santa Rubi Label Studio/`. |
| `catalog_datasource.py` | `DataSource` (ABC) | Contrato abstrato de origem de dados do catálogo. |
| `catalog_excel_source.py` | `ExcelCatalogSource`, `normalize_header` | Implementação concreta de `DataSource` sobre `.xlsx` via `openpyxl`. |
| `catalog_repository.py` | `CatalogRepository` | Único ponto que efetivamente lê a `DataSource`; mantém `CatalogProduct[]` em cache de memória. |
| `catalog_product.py` | `CatalogProduct` | Entidade permanente do produto do catálogo — **nunca tem quantidade**. |
| `catalog_service.py` | `CatalogService`, `CatalogStatistics` | Busca (texto ou lista de códigos), filtro (fornecedor/categoria), ordenação por coluna, estatísticas, `create_print_item()`. |
| `catalog_settings.py` | `CatalogSettings` | Configuração persistida do catálogo (`config.json`, chave `catalog_integrado`). |
| `catalog_validator.py` | `CatalogConfigurationValidator`, `ValidationReport`, `ValidationIssue` | Valida arquivo/abas/colunas mapeadas sem carregar produtos. |
| `print_item.py` | `PrintItem`, `normalize_quantity` | Uma solicitação de impressão (produto + quantidade, sempre inteiro ≥ 1). |
| `print_queue.py` | `PrintQueue` | Fila de impressão — única classe que manipula os itens; igualdade por `codigo`. |
| `print_queue_adapter.py` | `PrintQueueAdapter` | `PrintQueue` → `list[LabelData]` (sem nenhuma regra de impressão). |
| `print_log.py` | `log_print_job` | Grava uma linha por trabalho de impressão em `print_log.txt`. |
| `print_layout.py` | (só constantes) | Única fonte de todas as constantes físicas de layout da etiqueta/rolo. |
| `label_data.py` | `LabelData` (frozen) | Etiqueta tipada pronta para o motor de impressão. |
| `zpl_builder.py` | `ZplBuilder` | Monta o comando ZPL (`build()`/`build_row()`). |
| `printer.py` | `PrinterService` | Comunicação com o spooler Windows (`win32print`), `print_raw()`. |
| `text_normalize.py` | `normalize_search_text`, `parse_multiple_codes` | Normalização de texto para busca; detecção de lista de códigos colada. |
| `column_sort.py` | `ColumnSorter`, `sort_items`, `SortDirection`, `numeric_or_text` | Ordenação de colunas type-aware (número como número, texto sem acento, vazio sempre por último), compartilhada entre telas. |
| `table_state.py` | `get_column_widths`, `apply_column_widths`, `get_sorter_state`, `apply_sorter_state` | Persistência de largura de colunas e ordenação ativa de uma tabela. |
| `queue_feedback.py` | `describe_queue_addition` | Texto de feedback (usado pelo `Toast`) ao adicionar produtos à fila. |
| `excel_reader.py` | `ExcelReader` | ⚠ Ver seção 17 — sem chamador em `ui/` hoje. |
| `barcode.py` | `BarcodeGenerator` | ⚠ Ver seção 17 — sem chamador em `ui/` hoje. |
| `label_renderer.py` | `LabelRenderer` | ⚠ Ver seção 17 — sem chamador em `ui/` hoje. |

### 8.2 `app/api/` — integração Jueri

| Módulo | Classe/função principal | Responsabilidade |
|---|---|---|
| `auth.py` | `JueriCredentials` | Credenciais (`enabled`, `cliente_sistema`, `token`), persistidas em `config.json` (chave `jueri`). |
| `client.py` | `JueriClient` | Cliente HTTP genérico via `urllib` — monta headers, trata erros HTTP/timeout/conexão. |
| `exceptions.py` | `JueriError` e subclasses | Hierarquia de erros da integração; `JueriAPIError.describe()` extrai mensagem amigável do corpo da resposta. |
| `connection_test.py` | `test_connection` | Usado por "Testar conexão" em `SettingsDialog`; chama `GET /api/v1/{cliente}/revendedor/nivel`. |
| `categories.py` | `CategoriesAPI` | Resolve `fk_categoria_id`/`fk_subcategoria_id` → nome, com cache em memória após a primeira chamada. |
| `product.py` | `Product`, `ProductPrice` | Modelo de produto da API; `to_catalog_product()` é a ponte para o domínio do catálogo. |
| `products.py` | `ProductsAPI`, `ProductSearchResult` | `search_products` (uma página), `search_multiple_products` (lista de códigos), `search_all_pages` (paginação completa). |
| `date_filters.py` | `build_date_range_filter`, `today_br`, `yesterday_br`, `br_date_to_iso` | Converte datas BR digitadas pelo usuário para o formato ISO exigido pela API. |
| `debug_log.py` | `log_jueri_api_error` | Log opcional (`JUERI_DEBUG_LOG=1`) de respostas HTTP brutas, para suporte técnico. |

### 8.3 `ui/` — apresentação

| Módulo | Responsabilidade |
|---|---|
| `main_window.py` | Janela raiz (`MainWindow`): cabeçalho fixo (título + "Configurações"), `ttk.Notebook`, aba "API Jueri" completa, atalhos globais (F3/Ctrl+F/Ctrl+P/Ctrl+L), persistência de interface (aba ativa, geometria da janela, colunas/ordenação da tabela Jueri, favoritos). |
| `catalog_tab.py` | `CatalogTab`: aba "Planilha Excel" — configuração da fonte de dados, tabela do catálogo, painel "Fila de Impressão" (cartões, `[-]`/`[+]`, edição direta, atalhos DEL/Ctrl+A), disparo da impressão. Camada de apresentação pura — nenhuma regra de negócio do catálogo ou de impressão vive aqui. |
| `product_search_dialog.py` | `ProductSearchDialog`: janela modal de pesquisa de produtos Jueri — busca por texto/lista de códigos/intervalo de datas, seleção múltipla/arraste, ordenação, ESC fecha, ENTER pesquisa. |
| `settings_dialog.py` | `SettingsDialog`: habilitar integração Jueri, `cliente_sistema`, `token`, testar conexão. |
| `treeview_selection.py` | `enable_drag_selection(tree)`: liga seleção contínua por clique+arraste a um `ttk.Treeview`, preservando Ctrl/Shift-clique nativos. |
| `toast.py` | `Toast`: feedback textual temporário sobre um `tk.Label` já existente — nunca usa `messagebox`. |

### 8.4 `scripts/` — build e desenvolvimento

| Módulo | Responsabilidade |
|---|---|
| `launcher.py` | `LauncherWindow` — decide se precisa recompilar (via `project_signature`), roda o build em thread separada, abre o `.exe` e se fecha. |
| `build_runner.py` | `run_build()` — executa `scripts/build.bat` via `subprocess.Popen` com `CREATE_NO_WINDOW` (nenhuma janela de CMD) e `stdin=DEVNULL` (não trava no `pause` do `.bat`). |
| `project_signature.py` | `compute_signature()` — SHA-256 de nome+conteúdo de todo `.py`/`.spec`/`.txt` do projeto (fora de `build/dist/venv/.git/__pycache__`); `needs_rebuild()` decide se o hash mudou desde o último build salvo. |
| `build.bat` | Roda `python -m PyInstaller "Santa Rubi Label Studio.spec"`; não abre mais a pasta `dist/` ao final (comportamento removido). |
| `build_launcher.bat` | Roda `python -m PyInstaller "Santa Rubi Launcher.spec"`; deliberadamente não limpa `build/`/`dist/` antes (pastas compartilhadas com o app principal). |

---

## 9. Build

- **Ferramenta:** PyInstaller, via dois arquivos `.spec` na raiz do projeto:
  `Santa Rubi Label Studio.spec` (entry point `app.py`) e
  `Santa Rubi Launcher.spec` (entry point `scripts/launcher.py`).
- Ambos os `.spec` são praticamente idênticos em estrutura: `Analysis` sem
  `binaries`/`datas`/`hiddenimports` extras, `console=False` (nenhuma janela
  de terminal visível para o usuário final), `upx=True`.
- `scripts/build.bat` limpa `build/`/`dist/` antes de compilar o app
  principal (`if exist build rmdir /S /Q build`); `scripts/build_launcher.bat`
  **não** limpa essas pastas (comentário explícito no arquivo: são
  compartilhadas com o app principal e com `dist/build_info.json`).
- O Launcher (`scripts/launcher.py`) é a via normal de desenvolvimento local:
  ele decide sozinho, via `project_signature.needs_rebuild()`, se precisa
  rodar `build.bat` antes de abrir o executável — o desenvolvedor não
  precisa rodar `build.bat` manualmente no dia a dia.
- Versão do build vem de `git describe --tags --always --dirty`
  (`current_git_version()`), a mesma convenção de tags já usada no
  histórico do projeto (`v1.0-print-engine`, `v1.1-smart-print`, ...,
  `v3.0-stable`, `v1.0.0`).
- `dist/build_info.json` registra `{version, built_at, duration_seconds,
  signature}` do último build bem-sucedido.

---

## 10. Inicialização

Sequência real de `app.py`:

```python
root = tk.Tk()
MainWindow(root)
root.mainloop()
```

Dentro de `MainWindow.__init__` (`ui/main_window.py`):

1. `self.config_manager = ConfigManager()`; `self.config =
   self.config_manager.load()` — lê `config.json` uma única vez.
2. Restaura estado de janela: `window_state` (`"zoomed"` por padrão) e
   `window_geometry` (tamanho/posição salvos, se existirem).
3. Inicializa estado da aba "API Jueri" em memória: categorias Jueri (cache
   `None` até a primeira pesquisa), histórico de pesquisas recentes
   (`jueri_search_history`, não persistido), favoritos
   (`jueri_favorite_searches`, carregado de `config["jueri_favorites"]`),
   o `ColumnSorter` da tabela de resultado.
4. `_setup_style()` — configura o tema `ttk` (`"clam"`) e os estilos
   nomeados usados em toda a interface (`Title.TLabel`, `Subtitle.TLabel`,
   `Card.TFrame`, `App.TButton`, `Primary.TButton`, etc.).
5. `_build_widgets()` — monta cabeçalho fixo, `ttk.Notebook`, constrói a
   aba "API Jueri" (`_build_jueri_tab`) e instancia `CatalogTab` para a aba
   "Planilha Excel" (`_build_catalog_tab`); aplica o estado persistido da
   `CatalogTab` (`apply_persisted_state`); restaura a última aba ativa;
   liga os atalhos globais (`_bind_shortcuts`); registra
   `WM_DELETE_WINDOW` para salvar o estado da interface ao fechar
   (`_on_close` → `_save_interface_state`).

Dentro de `CatalogTab.__init__` (`ui/catalog_tab.py`): lê `CatalogSettings`
do config, monta os widgets, carrega a lista de impressoras
(`_load_printer_list`), e — **se já houver uma configuração completa salva**
(arquivo + abas + todas as colunas mapeadas) — carrega o catálogo
automaticamente (`_try_initial_load`), silenciando qualquer erro para não
interromper a abertura do programa.

---

## 11. Sistema de Impressão

### 11.1 Motor único

Confirmado em código: existe **um único caminho de impressão real** no
sistema — `ZplBuilder` (geração de texto ZPL) + `PrinterService.print_raw`
(envio bruto ao spooler). Não existe nenhum caminho de impressão via GDI,
`ImageWin`, ou API de desenho do Windows atualmente ativo em `ui/`.

- `ZplBuilder.build(product: dict)` — etiqueta única, aceita um `dict` por
  compatibilidade (converte para `LabelData` internamente via
  `_to_label_data`). **Não há hoje nenhum chamador de `build()` em `ui/`**
  — ver seção 17.
- `ZplBuilder.build_row(products: list[LabelData], column_pitch=...,
  total_width=...)` — uma ou mais etiquetas lado a lado num único
  `^XA...^XZ`, usado pela impressão em lote da fila
  (`CatalogTab._run_queue_print_job`).
- Todas as constantes físicas (dimensão da etiqueta, margens, tamanhos de
  fonte, posição de cada linha, parâmetros do Code128, colunas do rolo)
  vêm exclusivamente de `core/print_layout.py`, calibradas fisicamente
  contra impressões reais na ELGIN L42PRO FULL (comentário explícito no
  arquivo).
- `PrinterService` (`core/printer.py`) usa `win32print` diretamente:
  `list_printers()`, `get_default_printer()`, `print_raw(data, copies=1)`
  (abre a impressora, `StartDocPrinter`/`StartPagePrinter`/`WritePrinter`/
  `EndPagePrinter`/`EndDocPrinter`/`ClosePrinter`, job tipo `"RAW"`).

### 11.2 Do catálogo até a impressora

`CatalogTab._on_print_queue()` → valida fila não vazia e impressora
selecionada → `PrintQueueAdapter.to_label_data(self.print_queue)` (expande
cada `PrintItem` em N `LabelData`, N = quantidade) → roda
`_run_queue_print_job` **em thread separada** (`threading.Thread`, daemon):
agrupa os `LabelData` em blocos de `BATCH_ROW_COLUMNS` (3) via
`ZplBuilder.build_row(row, column_pitch=BATCH_COLUMN_PITCH, total_width=...)`
e chama `PrinterService.print_raw(zpl)` para cada bloco. Ao final:

- Sucesso → `core.print_log.log_print_job(..., "sucesso")`, e a interface
  **pergunta duas vezes** ao usuário (via `messagebox.askyesno`): se a
  impressão foi concluída com sucesso, e se deseja limpar a fila.
- Erro → `log_print_job(..., "falha")`, mostra `messagebox.showerror` com o
  texto da exceção, e **nunca limpa a fila** (usuário pode corrigir e
  tentar de novo).

### 11.3 Etiqueta física

- 30×15mm, resolução nativa 203dpi → 240×120 dots (`LABEL_WIDTH_DOTS`/
  `LABEL_HEIGHT_DOTS` em `core/print_layout.py`).
- Código de barras Code128, **Start Code C explícito** (`>;` no ZPL) —
  comentário no código confirma que os códigos da Santa Rubi são sempre
  numéricos de 6 dígitos, permitindo compactação 2 dígitos/símbolo.
- Rolo físico calibrado para **3 colunas por linha**
  (`BATCH_ROW_COLUMNS = 3`, `BATCH_COLUMN_PITCH = 264`) — enviar um job
  mais estreito que essa largura faz a impressora repetir o conteúdo nas
  colunas restantes (comentário explícito em `print_layout.py`).
- Fonte ZPL usada em todos os campos: `"0"` (nem negrito real nem fonte
  `D` — comentário no código relata tentativa de usar a fonte `D` e
  reversão por instabilidade de escala na impressora).

---

## 12. Integração Jueri

- **Ativação:** `JueriCredentials.from_config(config)` — chave `"jueri"` em
  `config.json`, com `enabled` (bool), `cliente_sistema`, `token`. Editável
  em `SettingsDialog`.
- **Cliente HTTP:** `JueriClient` (`app/api/client.py`) — usa `urllib`
  puro (sem `requests`), `User-Agent` forçado para
  `"Mozilla/5.0 (Windows NT 10.0; Win64; x64)"` porque, segundo comentário
  no código, a API roda atrás de Cloudflare e bloqueia o `User-Agent`
  padrão do `urllib` (HTTP 403, corpo `"error code: 1010"`).
- **Base URL:** `https://jueri.com.br/sis` (`JUERI_BASE_URL`, em
  `app/api/connection_test.py`).
- **Endpoints usados:**
  - `GET /api/v1/{cliente_sistema}/produto` — busca de produtos
    (`ProductsAPI.search_products`), com filtros `search`, `status`,
    `categoria_id`, `subcategoria_id`, datas de criação/alteração,
    paginação.
  - `GET /api/v1/{cliente_sistema}/produto/categoria` — lista de
    categorias/subcategorias (`CategoriesAPI`), cacheada em memória após a
    primeira chamada.
  - `GET /api/v1/{cliente_sistema}/revendedor/nivel` — usado só para
    "Testar conexão" (não há endpoint dedicado de autenticação na
    documentação oficial, segundo comentário em `connection_test.py`).
- **Tratamento de erro:** hierarquia `JueriError` — desabilitada,
  credenciais ausentes, timeout, falha de conexão, erro HTTP.
  `JueriAPIError.describe()` tenta extrair uma mensagem amigável do corpo
  da resposta (JSON com chave `message`/`error`/`erro`, ou detecção
  específica do bloqueio Cloudflare) antes de cair numa mensagem genérica.
- **Log de diagnóstico opcional:** `JUERI_DEBUG_LOG=1` (variável de
  ambiente) grava requisições/respostas brutas de erro em
  `%LOCALAPPDATA%/Santa Rubi Label Studio/jueri_debug.log` — desabilitado
  por padrão.
- **Conversão para o catálogo:** `Product.to_catalog_product(categories)`
  — mapeia `codigo_barras → codigo`, `descricao`, `preco_principal → preco`
  (preço do tipo exatamente `"Varejo"`, sem fallback para outro tipo),
  categoria resolvida via `CategoriesAPI`, `numero_peca → numeracao`,
  `fornecedor = "Jueri"` (fixo), e guarda `quantidade` (estoque atual) em
  `attributes["default_quantity"]`.
- **Fluxo de UI:** ver seção 4.2. Pesquisas recentes (sessão, não
  persistidas) e favoritas (persistidas em `config["jueri_favorites"]`) são
  reexecutáveis com um clique, reabrindo `ProductSearchDialog` já
  preenchido (`initial_query`/`initial_data_inicial`/`initial_data_final`).

---

## 13. Integração Excel

Há **duas implementações de leitura de Excel completamente independentes**
no código — confirmado por leitura direta, não é suposição:

1. **`core/catalog_excel_source.py` (`ExcelCatalogSource`)** — a implementação
   realmente usada hoje pela aba "Planilha Excel". Implementa a interface
   `DataSource` (`core/catalog_datasource.py`): `list_sheets()`,
   `get_headers()`, `count_rows()`, `read_rows()`. Suporta **múltiplas
   abas simultâneas** (cada linha lida carrega um campo interno `_sheet`,
   usado como `fornecedor` do `CatalogProduct`). Usa `openpyxl.load_workbook`
   com `data_only=True, read_only=True`.
2. **`core/excel_reader.py` (`ExcelReader`)** — leitor mais simples, com
   colunas fixas (`CODIGO`, `CATEGORIA`, `DESCRICAO`, `PRECO`, `NUMERO`,
   `QTD`) e aliases de cabeçalho pré-definidos, e um método
   `buscar_produto(codigo)`. **Hoje sem nenhum chamador em `ui/`** — ver
   seção 17.

O fluxo real de configuração (via `ExcelCatalogSource`):

```
CatalogTab._on_select_file() → file_path_var
        ▼
CatalogTab._load_sheets() → CatalogRepository.list_sheets() → checkboxes de aba
        ▼
Usuário mapeia cada campo interno (codigo/descricao/preco/categoria/
numeracao/quantidade) para um cabeçalho real da planilha (comboboxes)
        ▼
"Testar Configuração" → CatalogConfigurationValidator.validate(settings)
        (verifica arquivo, abas existentes, todas as colunas mapeadas
         localizáveis, conta produtos — sem carregar produtos de fato)
        ▼
"Recarregar Catálogo" → CatalogService.reload() → CatalogRepository.reload()
        → CatalogRepository._to_product() converte cada linha crua em
          CatalogProduct (campos textuais via _as_text, preço via _as_float,
          quantidade padrão de impressão guardada em
          attributes["default_quantity"])
```

A normalização de cabeçalho (`normalize_header`, em
`catalog_excel_source.py`) ignora caixa, espaços extras e quebras de linha,
mas **preserva acentuação** — diferente de
`text_normalize.normalize_search_text` (usada na busca de produtos), que
também remove acentos. O próprio código documenta essa distinção
explicitamente.

---

## 14. Persistência

Único mecanismo de persistência do sistema: um arquivo JSON, gerenciado por
`core/config.py` (`ConfigManager`):

```python
APP_DATA_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "Santa Rubi Label Studio"
CONFIG_FILE = APP_DATA_DIR / "config.json"
```

Ou seja, o arquivo real fica em
`%LOCALAPPDATA%\Santa Rubi Label Studio\config.json` — **não** na pasta
`data/` do repositório (ver divergência na seção 17). `ConfigManager.load()`
retorna `{}` se o arquivo não existir ou não puder ser lido;
`ConfigManager.save()` sobrescreve o arquivo inteiro a cada chamada
(`json.dumps(config, indent=2, ensure_ascii=False)`), silenciando qualquer
exceção de escrita.

Chaves conhecidas dentro de `config.json` (levantadas por leitura direta de
quem lê/escreve cada uma):

| Chave | Escrito/lido por | Conteúdo |
|---|---|---|
| `jueri` | `app/api/auth.JueriCredentials` | `{enabled, cliente_sistema, token}` |
| `catalog_integrado` | `core/catalog_settings.CatalogSettings` | `{file_path, selected_sheets, column_map, version, last_reload, configuration_expanded}` |
| `last_printer` | `ui/catalog_tab.py` (`CatalogTab._on_queue_printer_selected`) | Nome da última impressora selecionada. |
| `jueri_favorites` | `ui/main_window.py` (`_save_jueri_favorites`) | Lista de `{label, query, data_inicial, data_final}`. |
| `last_tab_index` | `ui/main_window.py` (`_save_interface_state`) | Índice da última aba ativa (0 = API Jueri, 1 = Planilha Excel). |
| `window_state` / `window_geometry` | `ui/main_window.py` | Estado (`"zoomed"`/`"normal"`) e geometria da janela principal. |
| `jueri_results_column_widths` / `jueri_results_sort` | `ui/main_window.py` | Largura de colunas e ordenação da tabela "Resultado da Última Pesquisa". |
| `catalog_state` | `ui/main_window.py` (delega a `CatalogTab.get_persisted_state()`) | `{column_widths, sort}` da tabela do catálogo. |

Persistência é salva em dois momentos distintos: **imediatamente** para
ações discretas do usuário (favoritar/desfavoritar, mudar configuração do
catálogo, trocar impressora, mudar credenciais Jueri), e **de uma vez só ao
fechar o programa** (`MainWindow._on_close` → `_save_interface_state`) para
o estado de interface (aba ativa, geometria, colunas, ordenação).

Além do `config.json`, existe `core/print_log.py`, que grava (append-only,
uma linha por trabalho de impressão) em
`%LOCALAPPDATA%\Santa Rubi Label Studio\print_log.txt`.

Log opcional de diagnóstico HTTP (`app/api/debug_log.py`), só se
`JUERI_DEBUG_LOG=1`, em
`%LOCALAPPDATA%\Santa Rubi Label Studio\jueri_debug.log`.

---

## 15. Testes

- Framework: `unittest` da biblioteca padrão (nenhum `pytest` encontrado
  em `requirements.txt` nem em imports).
- Execução real confirmada nesta auditoria: `python -m unittest discover -s
  tests -p "test_*.py"` → **541 testes, 100% passando** no momento desta
  auditoria (branch `feature/v3.1`, working tree com alterações não
  commitadas).
- 43 arquivos de teste em `tests/`, um por módulo/funcionalidade na maior
  parte dos casos (ex.: `test_print_queue.py`, `test_catalog_service.py`,
  `test_zpl_builder.py`, `test_jueri_client.py` não existe isoladamente —
  a integração HTTP é testada via `test_products_api.py`,
  `test_categories_api.py`, `test_jueri_auth.py`,
  `test_jueri_connection_test.py`, `test_jueri_debug_log.py`,
  `test_jueri_exceptions.py`).
- Testes de UI (Tkinter real) usam `@unittest.skipUnless(_tk_available(), ...)`
  para pular graciosamente em ambientes sem display — padrão repetido em
  praticamente todo teste que abre uma janela real (`tests/test_catalog_tab_*`,
  `tests/test_main_window_*`, `tests/test_product_search_dialog.py`,
  `tests/test_toast.py`, `tests/test_treeview_selection.py`).
- Padrão de teste de UI: `FakeConfigManager`/`FakeDataSource` (duplicados
  em vários arquivos de teste, não compartilhados via um módulo comum de
  fixtures) simulam a origem de dados sem tocar o Excel real nem o
  `config.json` real do usuário.
- Não há testes end-to-end reais contra a impressora física nem contra a
  API Jueri real (todos os testes de rede usam fakes/mocks — confirmado
  por leitura de `tests/test_products_api.py`, `tests/test_jueri_client.py`
  etc., que não fazem nenhuma chamada HTTP real).
- Módulos sem teste próprio identificado: nenhum encontrado — todo módulo
  de `core/`, `app/api/` e `ui/` tem pelo menos um arquivo de teste
  correspondente, incluindo os três módulos hoje órfãos da UI
  (`core/excel_reader.py` → `tests/test_excel_reader.py`,
  `core/barcode.py`/`core/label_renderer.py` →
  `tests/test_label_renderer.py`).

---

## 16. Decisões Arquiteturais encontradas

Decisões abaixo foram inferidas de comentários/docstrings explícitos no
próprio código-fonte (não de suposição):

1. **Um único motor de impressão.** Comentário em `core/print_queue_adapter.py`
   e `core/zpl_builder.py`: qualquer nova origem de produto deve ser
   *adaptada* ao formato que `ZplBuilder`/`PrinterService` já aceitam,
   nunca ganhar um pipeline de impressão paralelo. Também documentado
   formalmente em `docs/DECISIONS.md` (ADR 001, histórico).
2. **`CatalogProduct` nunca tem quantidade.** Docstring da própria classe:
   quantidade é sempre uma propriedade de `PrintItem` (a solicitação de
   impressão), nunca do produto. A quantidade padrão vinda do Excel/estoque
   Jueri fica temporariamente em `attributes["default_quantity"]`.
3. **`PrintQueue` é a única fonte de verdade da fila**, com igualdade de
   item sempre por `codigo` do produto (nunca por identidade de objeto) —
   docstring da classe.
4. **Constantes físicas de layout só existem em `core/print_layout.py`.**
   Comentário no topo do arquivo e em `zpl_builder.py`: "nenhum outro
   módulo declara esses valores".
5. **`core/` nunca depende de `ui/`.** Comentário explícito em
   `core/text_normalize.py`: "mora em core/ porque core/ nunca pode
   depender de ui/, mas ambos podem depender de core/".
6. **`ui/main_window.py` e `ui/catalog_tab.py` nunca se importam
   mutuamente.** Confirmado por leitura: `CatalogTab` é instanciado dentro
   de `MainWindow._build_catalog_tab()`; nenhum import reverso existe.
7. **Duas fontes de Excel deliberadamente independentes.** Docstring de
   `core/catalog_excel_source.py`: "Deliberadamente independente do
   ExcelReader usado pela impressão manual (aba existente) — as duas
   fontes de dados não compartilham código, para que uma nunca afete o
   comportamento da outra." (Nota desta auditoria: a "aba existente" citada
   já não existe mais — ver seção 17.)
8. **Conversão Jueri → Catálogo sem lógica de fila nova.** Docstring de
   `Product.to_catalog_product()`: depois de convertido, um produto Jueri
   é "indistinguível de um produto do Excel para o resto do sistema".
9. **Não usar `messagebox` para feedback de rotina.** `ui/toast.py` e seu
   uso em `MainWindow`/`CatalogTab`: confirmações de "produto adicionado à
   fila" usam um rótulo temporário (`Toast`), não uma janela modal —
   avisos de erro/validação (ex.: "selecione um produto") continuam usando
   `messagebox`.
10. **Componentes de tabela (ordenação, seleção por arraste, persistência
    de estado) são deliberadamente compartilhados.** `core/column_sort.py`,
    `ui/treeview_selection.py` e `core/table_state.py` são usados tanto
    pela tabela de resultado da pesquisa Jueri quanto (indiretamente) pela
    tabela do catálogo — evita duplicar a mesma lógica em duas telas.
11. **Build sem janela de console.** `scripts/build_runner.py`: uso
    explícito de `CREATE_NO_WINDOW` e `stdin=DEVNULL`, comentado como
    necessário para nunca mostrar uma janela de CMD ao usuário e nunca
    travar no `pause` do `.bat`.
12. **Impressão da fila sempre em thread separada, nunca descarta a fila
    em erro.** Comentário em `CatalogTab._run_queue_print_job`/
    `_on_print_job_error`: "erro nunca apaga a fila... o usuário pode
    corrigir e tentar novamente sem perder o que já montou."

---

## 17. Pontos que não puderam ser determinados / divergências encontradas

Estes pontos são reportados explicitamente, conforme exigido — nenhum foi
inventado ou assumido.

1. **`core/excel_reader.py` (`ExcelReader`) parece órfão.** Buscado em todo
   o projeto (`grep`); só é referenciado por `core/excel_reader.py` (a si
   mesmo) e por `tests/test_excel_reader.py`. Nenhum arquivo em `ui/`
   importa `ExcelReader`. A própria classe existe para uma "aba
   Impressão" que não existe mais no código atual (ver nota de divergência
   no topo). Não foi possível determinar, só pela leitura do código, se
   isso é intencional (módulo mantido por segurança/compatibilidade) ou um
   resíduo esquecido do redesenho de interface.
2. **`core/label_renderer.py` (`LabelRenderer`) e `core/barcode.py`
   (`BarcodeGenerator`) parecem órfãos pelo mesmo motivo** — pipeline de
   pré-visualização bitmap da antiga aba "Impressão". Sem chamador em
   `ui/main_window.py` nem `ui/catalog_tab.py` hoje. Isso significa que a
   dependência de `python-barcode` do `requirements.txt` só é exercitada
   pelos testes desses dois módulos, não pela aplicação em uso normal —
   não foi possível confirmar se isso é aceitável para o projeto ou não.
3. **`reportlab` está em `requirements.txt` mas não foi encontrado nenhum
   `import reportlab` (nem `from reportlab`) em nenhum arquivo `.py` do
   projeto.** Não foi possível determinar seu propósito atual só pelo
   código.
4. **`data/config.json` e `data/print_log.txt` existem no repositório**,
   mas `core/config.py` e `core/print_log.py` apontam explicitamente para
   `%LOCALAPPDATA%/Santa Rubi Label Studio/`, não para a pasta `data/` do
   projeto. Não foi possível confirmar, só pelo código, se os arquivos em
   `data/` são resíduo de uma implementação anterior, cópia manual de
   depuração, ou se algum script/processo externo ao código Python (não
   encontrado nesta auditoria) ainda os utiliza.
5. **`assets/` e `layouts/`** contêm apenas um `.gitkeep` cada — reservados,
   sem nenhum uso identificado no código atual.
6. **Documentação legada na raiz (`README.md`, `ARCHITECTURE.md`,
   `ROADMAP.md`, `CHANGELOG.md`, `DOCUMENTACAO_CHECKPOINT.md`) descreve uma
   versão anterior do produto** (abas "Impressão"/"Catálogo Integrado", sem
   integração Jueri). Não foi possível determinar, só pelo código, se esses
   arquivos devem ser atualizados, arquivados ou mantidos como histórico —
   a tarefa desta auditoria não pediu para alterá-los, então foram apenas
   citados como divergência, não corrigidos.
7. **`docs/ai/03_DESIGN_SYSTEM.md` (antes desta auditoria) descrevia uma
   paleta de cores (`#947F5E`/`#F1EBD7`) e fonte de logo ("Amsterdam Four")
   que não aparecem em nenhum lugar do código.** As cores efetivamente
   usadas em `ui/main_window.py` (`_setup_style`) são tons de azul/cinza
   (`#0f172a`, `#64748b`, `#1d4ed8`, `#2563eb`, `#f4f6f8`, `#ffffff`,
   `#dbe2ea`), fonte `"Segoe UI"` em toda a interface. Não foi encontrado
   nenhum arquivo de logo, ícone customizado ou definição de fonte
   "Amsterdam Four" no repositório. Esta divergência foi corrigida na
   reescrita do documento (Etapa 3), reportando a paleta real.
8. **Versão "oficial" do produto é ambígua.** A tag git mais recente é
   `v1.0.0` (mais nova, cronologicamente, que `v3.0-stable` — confirmado
   via `git log --tags --simplify-by-decoration`), sugerindo um reset
   deliberado de numeração de versão coincidindo com a integração Jueri.
   `docs/ai/04_ROADMAP.md` (antes desta auditoria) já assumia "v1.0.0" como
   versão atual. Não foi encontrado nenhum arquivo único e inequívoco que
   declare "esta é a versão oficial atual" — a inferência acima é a mais
   consistente com as evidências de `git`, mas não é uma certeza absoluta.
9. **Ícone do executável / instalador.** Nenhum arquivo `.ico` nem
   configuração de ícone foi encontrado nos dois `.spec` do PyInstaller
   (`icon=` não é passado a `EXE(...)` em nenhum dos dois arquivos) —
   não foi possível confirmar se isso é intencional.
10. **Comportamento em ambiente não-Windows.** `core/printer.py` e
    `app/api` fazem `try/except ImportError` para `win32print`, e testes
    usam `_tk_available()`/`skipUnless` para tolerar ambientes sem display
    — indício de que o projeto é desenvolvido/testado ocasionalmente fora
    do Windows, mas o produto final é exclusivamente Windows (`win32print`
    é obrigatório para imprimir de fato). Não há documentação explícita
    sobre requisitos mínimos de SO além do que já está em `README.md`
    ("Windows, testado com impressora ELGIN L42PRO FULL").
11. **Estilos `ttk` definidos em `MainWindow._setup_style()` mas sem
    nenhum widget que os use hoje:** `Sidebar.TFrame`, `Sidebar.TLabel`,
    `Sidebar.TRadiobutton`, `DetailValue.TLabel` e
    `Slim.Horizontal.TProgressbar` (confirmado por busca: nenhum
    `style="Sidebar..."`, `style="DetailValue..."` nem `ttk.Progressbar`
    em `ui/`). Resíduo provável da antiga aba "Impressão" (que tinha barra
    de progresso de impressão em lote e um painel lateral escuro),
    removida do código atual.
12. **`ARCHITECTURE_AUDIT.md` (este arquivo) não tem um lar formal
    definido pelo usuário** — foi colocado na raiz do projeto, ao lado dos
    demais documentos técnicos (`ARCHITECTURE.md`, `CHANGELOG.md`,
    `ROADMAP.md`), por ser o padrão já estabelecido no repositório.

---

*Fim da auditoria. Nenhum arquivo de código foi alterado para produzir este
documento.*
