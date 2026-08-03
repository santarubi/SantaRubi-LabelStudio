# Roadmap

Versão: 2.0 (revisado por auditoria de código)

Última atualização: Julho/2026

Este documento descreve a evolução planejada do Santa Rubi Label Studio.

O roadmap serve como referência para definir prioridades e orientar
futuras implementações.

---

# Situação Atual

Versão (tag git mais recente, `git describe --tags`):

`v1.0.0`

> Nota: o histórico de tags do repositório também contém
> `v1.0-print-engine`, `v1.1-smart-print`, `v1.2-layout-final`,
> `v1.3-produtividade` e `v3.0-stable`, todas anteriores a `v1.0.0` em
> ordem cronológica real (confirmado via `git log --tags
> --simplify-by-decoration`). A tag `v1.0.0` marca, aparentemente, um
> reinício deliberado da numeração coincidindo com a integração da API
> Jueri e a reorganização das abas — não foi encontrado um documento único
> que declare isso de forma explícita (ver `ARCHITECTURE_AUDIT.md`, seção
> 17).

Status:

Estável — 541 testes automatizados passando no momento desta auditoria.

Principais funcionalidades concluídas (cada item abaixo foi confirmado
contra o código, não apenas contra um changelog anterior):

- Impressão através da Planilha Excel (aba "Planilha Excel",
  `CatalogTab`).
- Integração com API Jueri (aba "API Jueri", `MainWindow` +
  `ProductSearchDialog`), incluindo busca por texto, lista de códigos e
  intervalo de datas.
- Fila única de impressão (`core/print_queue.py`, `PrintQueue`) — uma
  única instância, compartilhada pelas duas abas.
- Conversão automática para `CatalogProduct`
  (`Product.to_catalog_product()`), tanto do Excel quanto da API Jueri.
- Busca de produtos (catálogo local e API Jueri).
- Seleção múltipla (clique/Ctrl/Shift) e seleção contínua por arraste em
  todas as tabelas relevantes.
- Favoritos de pesquisa Jueri (persistidos em `config.json`).
- Pesquisas recentes (histórico em memória, não persistido entre
  execuções).
- Persistência de configurações: credenciais Jueri, configuração do
  catálogo, última impressora, aba ativa, geometria da janela, largura de
  colunas e ordenação das tabelas.
- Feedback visual discreto (`ui/toast.py`) ao adicionar produtos à fila,
  em vez de janelas de confirmação bloqueantes.
- Resumo da fila de impressão visível na aba "API Jueri" (produtos,
  etiquetas, última atualização) sem precisar abrir a aba "Planilha
  Excel".
- Atalhos globais: F3 (pesquisar na API Jueri), Ctrl+F (pesquisar na
  Planilha Excel), Ctrl+P (imprimir fila), Ctrl+L (limpar fila); ESC/ENTER
  dentro da janela de pesquisa Jueri.
- Correção de usabilidade na Fila de Impressão: alterar quantidade
  (`[-]`/`[+]`/edição direta) não reconstrói mais a lista inteira —
  preserva posição do scroll, seleção e foco (`CatalogTab`,
  `_update_card_quantity_display`/`_end_edit_quantity`).
- Testes automatizados: 541 testes (`unittest`), cobrindo domínio,
  integração Jueri e interface.
- Estrutura de impressão consolidada: motor único (`ZplBuilder` +
  `PrinterService`), constantes físicas centralizadas
  (`core/print_layout.py`).

---

# Próxima Versão

## v1.1 — Experiência do Usuário

Objetivo:

Elevar a qualidade visual e a experiência de uso.

Funcionalidades previstas:

- Implementar de fato uma paleta de marca (hoje a interface usa uma
  paleta azul/cinza neutra — ver divergência registrada em
  `03_DESIGN_SYSTEM.md` — não a paleta `#947F5E`/`#F1EBD7` mencionada em
  versões anteriores deste roadmap).
- Splash Screen.
- Ícones padronizados (hoje a interface usa apenas caracteres Unicode
  como `★`/`☆`/`×`/`✓`, sem biblioteca de ícones).
- Melhorias visuais e padronização dos componentes.
- Refinamento da interface e microinterações.
- Revisar/remover estilos `ttk` hoje sem uso (`Sidebar.*`,
  `DetailValue.TLabel`, `Slim.Horizontal.TProgressbar` — ver
  `ARCHITECTURE_AUDIT.md`, seção 17).

Status:

Planejado.

---

## v1.2 — Produtividade

Objetivo:

Reduzir o número de ações necessárias para impressão.

Possíveis funcionalidades:

- Atalhos adicionais.
- Melhorias na fila (parte já entregue: preservação de scroll/seleção/foco
  ao alterar quantidade).
- Melhor gerenciamento de seleção.
- Histórico de impressão visível na própria interface (a base de dados já
  existe: `core/print_log.py` grava cada trabalho em
  `%LOCALAPPDATA%/Santa Rubi Label Studio/print_log.txt`, mas não há
  nenhuma tela que leia esse arquivo hoje).
- Melhor navegação.

Status:

Em estudo.

---

## v1.3 — Recursos Avançados

Objetivo:

Adicionar funcionalidades complementares sem alterar a arquitetura
principal.

Possibilidades:

- QR Code (a estrutura de `LabelData`/`ZplBuilder` foi desenhada para
  crescer com novos campos sem quebrar o pipeline existente, mas nenhum
  QR code é gerado hoje).
- Scanner.
- Estatísticas de impressão (a partir do log já existente).
- Exportações.
- Melhorias de relatórios.

Status:

Ideias.

---

# Esclarecimento sobre módulos hoje sem uso na interface

A auditoria de código (`ARCHITECTURE_AUDIT.md`) encontrou três módulos de
`core/` sem nenhum chamador em `ui/` atualmente:

- `core/excel_reader.py` (`ExcelReader`) — leitor de planilha mais simples,
  de uma versão anterior do produto.
- `core/label_renderer.py` (`LabelRenderer`) e `core/barcode.py`
  (`BarcodeGenerator`) — pipeline de pré-visualização bitmap em tela, que
  pertencia à antiga aba "Impressão".

Nenhuma decisão sobre manter, reativar ou remover esses módulos foi
encontrada em código ou documentação — qualquer decisão futura sobre eles
deve ser tratada como uma escolha de arquitetura explícita, não como uma
simples limpeza incidental.

---

# Princípios do Roadmap

Toda nova funcionalidade deve:

- respeitar a arquitetura oficial (`docs/ai/LABEL_STUDIO_GUIDE.md`);
- reutilizar componentes existentes;
- preservar os testes automatizados;
- evitar duplicação de código;
- melhorar a experiência do usuário.

---

# Fora do Escopo

O Label Studio não tem como objetivo:

- substituir o ERP Jueri;
- controlar estoque;
- realizar vendas;
- controlar financeiro;
- realizar precificação.

Essas responsabilidades pertencem a outros sistemas.

---

# Atualização do Roadmap

Este documento deve ser atualizado sempre que:

- uma versão for concluída;
- uma nova versão for planejada;
- prioridades forem alteradas;
- funcionalidades forem oficialmente aprovadas.
