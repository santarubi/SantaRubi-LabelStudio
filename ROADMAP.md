# Roadmap — Santa Rubi Label Studio

Este roadmap reflete o estado logo após o congelamento da `v3.0-stable`.
Para o que já foi entregue em detalhe, ver [CHANGELOG.md](CHANGELOG.md) e
[DOCUMENTACAO_CHECKPOINT.md](DOCUMENTACAO_CHECKPOINT.md).

## Concluído

- **Motor de impressão RAW + ZPL** (`v1.0-print-engine`) — substituiu por
  completo o caminho via driver GDI do Windows.
- **Impressão em lote inteligente** (`v1.1-smart-print`) — agrupamento
  correto em colunas do rolo físico, quantidade por produto, memória da
  última impressora.
- **Layout físico da etiqueta calibrado e congelado** (`v1.2-layout-final`)
  — validado fisicamente na ELGIN L42PRO FULL.
- **Produtividade da interface** (`v1.3-produtividade`) — busca, filtro,
  contadores, impressão de selecionados, atalhos, seleção contínua.
- **Catálogo Integrado completo** — fonte de dados própria e permanente,
  configuração validável, cache em memória, busca/filtro/ordenação, painel
  recolhível.
- **Domínio de impressão desacoplado do catálogo** — `CatalogProduct`
  (entidade) separado de `PrintItem`/`PrintQueue` (solicitação de
  impressão), com `PrintQueue` como coleção rica (`increment`/`decrement`/
  `update_quantity`/protocolos Python).
- **Fila de Impressão visual e editável** — adicionar, remover, limpar,
  ajustar quantidade (`[-]`/`[+]` e edição direta), atalhos DEL/Ctrl+A.
- **Integração da fila com o pipeline de impressão existente** — via
  `PrintQueueAdapter`, em thread separada, com confirmação de sucesso,
  limpeza opcional e tratamento de erro que nunca descarta a fila.
- **Eliminação de duplicação arquitetural** (`v3.0-stable`) — constantes
  físicas centralizadas em `core/print_layout.py`; `LabelData` tipado
  substitui o `list[dict]` entre `PrintQueueAdapter` e `ZplBuilder`.

## Em desenvolvimento

Nenhuma frente de código aberta no momento — a `v3.0-stable` acaba de ser
congelada e esta rodada de documentação é o fechamento oficial do ciclo.

## Próximas versões

Sem compromisso de ordem ou prazo; candidatas priorizadas pelo que já foi
identificado como lacuna real:

- **Tratamento mais específico de erros de impressão** — distinguir
  "impressora offline", "sem permissão", "sem papel" em vez de uma
  mensagem genérica de exceção (`_on_print_job_error` hoje mostra o texto
  cru da exceção).
- **Edição de quantidade também na aba "Impressão"** (hoje só a Fila de
  Impressão do Catálogo Integrado permite ajustar quantidade diretamente
  na interface).
- **Distribuição do sistema** — empacotar como executável Windows
  (ex.: PyInstaller), eliminando a necessidade de ambiente Python/venv na
  máquina do usuário final.
- **Funcionalidades administrativas** — histórico de impressões na
  própria interface (a base já existe em `data/print_log.txt`), painel de
  favoritos/atalhos de produtos mais impressos.

## Ideias futuras

Sem compromisso — candidatas a avaliar somente diante de necessidade real
comprovada, não por antecipação:

- Suporte a múltiplos layouts/modelos de etiqueta (hoje o layout é fixo,
  calibrado para 30×15mm na ELGIN L42PRO FULL).
- Campos adicionais em `LabelData` (código de barras próprio, coleção,
  peso, fornecedor, QR code, marca) — a estrutura já foi desenhada para
  crescer sem quebrar o pipeline existente.
- Peso de fonte real no ZPL (negrito verdadeiro) — já tentado com a fonte
  bitmap "D" e revertido por instabilidade de escala; só retomar diante de
  exigência forte de negócio.
- Importação/exportação de filas de impressão (`PrintQueue.replace()` já
  foi desenhado pensando nesse cenário).
- Suporte a mais de uma impressora simultânea / múltiplas estações de
  trabalho compartilhando o mesmo catálogo.
