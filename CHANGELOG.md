# CHANGELOG

## [v1.3-produtividade] - Interface congelada

Checkpoint oficial de encerramento do ciclo de produtividade da interface.
Detalhes completos em `DOCUMENTACAO_CHECKPOINT.md`, capítulo "Checkpoint
v1.3-produtividade".

### Added
- Pesquisa instantânea por código, categoria, descrição e número —
  case insensitive, ignora acentos, com `_search_blob` pré-processado para
  manter a busca rápida mesmo com milhares de produtos.
- Filtro por categoria (dinâmico, único, ordenado, com opção "Todos"),
  combinável com a pesquisa de texto.
- Contadores "Total", "Exibindo" e "Selecionados", com atualização
  automática em qualquer mudança de filtro ou seleção.
- Botão dedicado "Imprimir Selecionados", reaproveitando integralmente o
  pipeline de impressão existente (quantidade, agrupamento em 3 colunas,
  `build_row()`, `PrinterService`).
- Atalhos de produtividade: Ctrl+F, ESC, Ctrl+A, Enter (na pesquisa) e
  duplo clique.
- Seleção contínua por arraste na tabela, usando a seleção nativa do
  Treeview.

### Notes
- Interface considerada madura para uso diário — ajustes futuros de
  usabilidade somente mediante necessidade comprovada. Próximas versões
  devem priorizar confiabilidade, manutenção, funcionalidades
  administrativas, arquitetura e distribuição do sistema.
- Nenhuma alteração em `ZplBuilder`, `PrinterService`, `LabelRenderer`,
  `build()` ou `build_row()` durante todo o ciclo v1.3.

## [v1.2-layout-final] - Layout da etiqueta congelado

Checkpoint oficial após validação física completa na ELGIN L42PRO FULL.
Detalhes completos em `DOCUMENTACAO_CHECKPOINT.md`, capítulo "Checkpoint
v1.2-layout-final".

### Added
- Memória da última planilha utilizada (`last_spreadsheet`), com
  carregamento automático na abertura do programa.
- Memória da última impressora utilizada (`last_printer`).
- Impressão por quantidade (`qtd` respeitada por etiqueta).

### Changed
- Code128 do código de barras passa a usar Start Code C explícito (`>;`),
  corrigindo compactação Subset B implícita.
- Código de barras centralizado matematicamente na coluna, com ajuste
  óptico de +6 dots.
- Campo de descrição usa largura própria e ampliada (198 dots,
  `DESCRIPTION_RIGHT_MARGIN = 4`) e corte simples por quantidade de
  caracteres (`DESCRIPTION_MAX_CHARS = 26`), sem reticências e sem
  heurística de largura.
- Impressão em lote agrupada em linhas de 3 colunas via `build_row()`.
- Consolidada a chave de configuração `last_excel_path` em
  `last_spreadsheet` (única).

### Fixed
- `_load_products_into_table()`: `selection_set()` recebia um `set()` em
  vez de lista, travando com `TclError` sempre que a seleção estava vazia.

### Notes
- Layout da etiqueta oficialmente congelado — ajustes futuros somente por
  bug comprovado, mudança de hardware ou novo requisito de negócio.

## [Unreleased]

### Added
- Documented session progress in `CLAUDE.md`.
- Created `CHANGELOG.md` to track future releases.

### Fixed
- Corrected `core/printer.py` printer DC creation to use `CreateDC()` then `CreatePrinterDC()`.

### Updated
- Refined interface layout and preview behavior to support a professional Windows desktop appearance.
- Confirmed printing integration with `pywin32` and validated printer listing.

### Notes
- Current printing state may still raise "Unable to open printer" depending on Windows printer access and configuration.
