# CHANGELOG

Todas as versões abaixo têm o detalhamento completo em
[DOCUMENTACAO_CHECKPOINT.md](DOCUMENTACAO_CHECKPOINT.md), no capítulo/
checkpoint de mesmo nome.

## [v3.0-stable] - Catálogo Integrado + arquitetura de impressão consolidada

Checkpoint oficial de congelamento da arquitetura. Cobre todo o ciclo de
evolução construído sobre a base de `v1.3-produtividade`: a nova aba
"Catálogo Integrado" completa (da configuração à impressão), e a
refatoração final que eliminou duplicação de dados/constantes entre ela e
a aba "Impressão".

### Added
- **Catálogo Integrado** (nova aba, `ttk.Notebook`): fonte de dados própria
  e permanente, independente da planilha usada na aba "Impressão" —
  configuração de arquivo/abas/mapeamento de colunas com validação
  ("Testar Configuração"), carregamento completo em memória com cache
  (`CatalogRepository`), pesquisa/filtro por fornecedor e categoria/
  ordenação por coluna (`CatalogService`), painel de configuração
  recolhível.
- **Modelo de domínio de impressão separado do catálogo**: `CatalogProduct`
  (entidade permanente, sem quantidade) → `PrintItem` (solicitação de
  impressão, quantidade sempre normalizada e ≥ 1) → `PrintQueue` (coleção
  rica: `add/remove/clear/contains/find/update_quantity/increment/
  decrement/replace/to_list`, além de `__len__`/`__iter__`/`__contains__`).
- **Fila de Impressão** (painel lateral na aba Catálogo Integrado):
  adiciona produtos selecionados na tabela (sem duplicar — incrementa
  quantidade se já existir), remove, limpa, ajusta quantidade por
  `[-]`/`[+]` ou edição direta (duplo clique → Entry → Enter/perda de
  foco), atalhos DEL (remover selecionado) e Ctrl+A (selecionar tudo na
  tabela).
- **Integração com o pipeline de impressão existente**: `PrintQueueAdapter`
  converte `PrintQueue` para o formato do motor de impressão; botão
  "Imprimir Fila" roda em thread separada, desabilita os controles durante
  a impressão, pergunta confirmação de sucesso e se deve limpar a fila ao
  final, e nunca descarta a fila em caso de erro.
- **Log de impressão** (`data/print_log.txt`): horário, produtos,
  etiquetas, tempo total e resultado de cada trabalho da fila.
- `core/print_layout.py`: única fonte de todas as constantes físicas de
  layout (etiqueta, margens, código de barras, rolo de 3 colunas) —
  `ZplBuilder` e as duas telas passam a importar dali, eliminando a
  duplicação de constantes que existia entre `ui/main_window.py` e
  `ui/catalog_tab.py`.
- `core/label_data.py`: `LabelData` (dataclass tipada e imutável) substitui
  o `list[dict]` solto entre `PrintQueueAdapter` e `ZplBuilder.build_row()`.

### Changed
- `ZplBuilder.build_row()` passa a aceitar `list[LabelData]` em vez de
  `list[dict]`. `ZplBuilder.build()` mantém o contrato público (`dict`)
  inalterado, convertendo internamente para `LabelData`.
- `ui/main_window.py` (aba "Impressão") passa a construir `LabelData` ao
  montar o lote de impressão, e a importar `BATCH_ROW_COLUMNS`/
  `BATCH_COLUMN_PITCH` de `core/print_layout.py` em vez de declarar
  localmente.

### Notes
- **Nenhuma regressão de comportamento**: a saída ZPL de `build()` e
  `build_row()` foi comparada byte a byte com a versão anterior à
  refatoração (commit congelado em `v1.3-produtividade`) — idêntica em
  todos os cenários testados.
- Suíte de testes: 191 testes, 100% passando.
- Arquitetura final do pipeline de impressão:
  `PrintQueue → PrintQueueAdapter → LabelData → ZplBuilder.build_row() →
  PrinterService → RAW → ELGIN`. Existe apenas um motor de impressão,
  usado pelas duas abas.
- Esta é a última refatoração arquitetural prevista antes do congelamento
  oficial da versão `v3.0`.

## [v1.3-produtividade] - Interface congelada

Checkpoint oficial de encerramento do ciclo de produtividade da interface.

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

## [v1.1-smart-print] - Impressão em lote inteligente

Sobre a base estável de `v1.0-print-engine`, resolveu a limitação de
enviar um job ZPL de coluna única por produto — o que, no rolo físico
calibrado para 3 colunas, arriscava replicar a etiqueta e ignorava a
quantidade de cada produto.

### Added
- Memória da última impressora utilizada, com fallback automático para a
  impressora padrão do Windows caso a salva não exista mais.
- Impressão em lote agrupada por linha de 3 colunas (`_run_batch_print`):
  a lista de produtos é expandida por quantidade e agrupada em blocos de
  até 3 etiquetas físicas, cada bloco enviado como **um único** job
  `ZplBuilder.build_row()`.
- `tests/test_zpl_builder.py` (novo): cobre `build_row()` com 1, 2 e 3
  produtos, confirmando ausência de campos/resíduos em colunas vazias.

### Changed
- `ZplBuilder.build_row()` ganha o parâmetro opcional `total_width`, que
  desacopla a largura física do job (sempre a largura calibrada do rolo)
  da quantidade de produtos realmente fornecidos — colunas sem produto
  correspondente ficam em branco, sem nenhum campo ZPL residual.

### Notes
- Validado fisicamente na ELGIN L42PRO FULL em todos os cenários (1, 2 e 3
  colunas, agrupamento automático cruzando múltiplas linhas, quantidade
  por etiqueta, alinhamento, código de barras) — nenhuma regressão.
- Nenhuma mudança tocou `PrinterService.print_raw` nem `LabelRenderer`
  (preview permanece independente).
- A partir desta versão, o módulo de impressão é considerado estável e
  concluído — mudanças futuras devem ser evolução incremental, não
  refatoração.

## [v1.0-print-engine] - Migração para impressão RAW + ZPL

Primeira versão consolidada da arquitetura de impressão: substitui por
completo a tentativa inicial de impressão via driver gráfico (GDI) do
Windows, que esbarrava num teto físico do driver da ELGIN (~20 dots de
margem de segurança perdidos de cada lado da etiqueta, fora do controle do
código) e produzia etiquetas cortadas/tortas. Histórico completo da
investigação em `DOCUMENTACAO_CHECKPOINT.md`, capítulo 2.

### Added
- `core/zpl_builder.py` (`ZplBuilder`): monta o comando ZPL (texto puro
  `^XA...^XZ`) da etiqueta a partir do dicionário de produto — sem
  nenhuma dependência de Pillow, Tkinter ou GDI.
- `PrinterService.print_raw()`: envia o comando ZPL como dado bruto
  (`RAW`) direto para o spooler do Windows, contornando o driver gráfico
  por completo. Correção da criação do Device Context via `CreateDC()` +
  `CreatePrinterDC()`.
- Suíte de testes automatizados inicial (leitura de planilha, seleção de
  lote, dimensão do preview) — 100% passando.

### Changed
- Os três pontos de impressão da interface (teste, impressão rápida e
  impressão em lote) passam a usar exclusivamente `ZplBuilder` +
  `PrinterService.print_raw()`.
- Pré-visualização em tela deliberadamente mantida independente, via
  `LabelRenderer` (bitmap Pillow) — os dois pipelines (impressão e
  preview) nunca se importam um ao outro.

### Removed
- Todo o caminho de impressão via GDI: `print_image()`,
  `_build_label_devmode()`, constantes de papel/DEVMODE customizado, e os
  imports `win32con`/`win32gui`/`win32ui`/`ImageWin` que ele exigia.

### Notes
- Motivação: teto de área útil imposto pelo driver GDI da ELGIN,
  confirmado fisicamente e evidenciado por outro sistema de PDV na mesma
  máquina/impressora que conseguia usar 100% da etiqueta (sinal de que
  não passava pelo driver tradicional).
- A partir deste ponto, qualquer evolução da impressão parte de uma base
  limpa, testada e documentada.
