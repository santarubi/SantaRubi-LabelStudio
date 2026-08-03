# Roadmap — Santa Rubi Label Studio

Este roadmap reflete o marco oficial `v1.0.1 — Estabilidade Consolidada`.
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
- **Estabilidade Consolidada** (`v1.0.1`) — integração completa com API
  Jueri, fluxo único via `PrintQueue`, integração Planilha Excel + API,
  Launcher, persistência, favoritos, pesquisas recentes, seleção múltipla,
  busca por múltiplos códigos e por data, rolagem durante seleção e
  tratamento definitivo de descrições longas sem reticências.
- **Qualidade automatizada** — todos os testes automatizados aprovados no
  fechamento do marco.

## Camada de negócio congelada

A partir da `v1.0.1`, os componentes abaixo não devem sofrer alterações
durante a implementação do Design System, salvo bug crítico ou solicitação
explícita:

- `PrintQueue`;
- `Product`;
- `CatalogProduct`;
- `PrinterService`;
- `ZplBuilder`;
- API Jueri;
- fluxo de impressão;
- fluxo Excel;
- conversões;
- persistência;
- Launcher.

O congelamento abrange regras de negócio, arquitetura e fluxos existentes.

## Em desenvolvimento

Nenhuma alteração de negócio está aberta. O próximo ciclo é exclusivamente
visual.

## Próxima versão

### v1.1.0 — Design System Santa Rubi

Objetivo: modernizar exclusivamente a interface do sistema.

Escopo:

- layout;
- cores;
- ícones;
- Splash Screen;
- componentes;
- UX;
- microinterações.

Restrições do ciclo: não alterar regras de negócio, arquitetura ou fluxos.

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
