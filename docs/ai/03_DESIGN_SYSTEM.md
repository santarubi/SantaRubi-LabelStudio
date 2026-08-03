# Design System

Versão: 2.0 (revisado por auditoria de código — substitui integralmente a
versão anterior)

Última atualização: Julho/2026

Este documento descreve o sistema visual **efetivamente implementado** no
código (`ui/main_window.py`, método `_setup_style`, mais os pontos onde
cada tela usa cor/fonte diretamente). Ele não descreve mais uma paleta de
marca aspiracional — ver nota de divergência abaixo.

> **Divergência encontrada e corrigida nesta revisão:** a versão anterior
> deste documento definia uma paleta oficial `#947F5E` (cor principal) /
> `#F1EBD7` (fundo) e a fonte de logo "Amsterdam Four". Nenhuma dessas
> cores ou fonte foi encontrada em nenhum arquivo `.py` do projeto, nem
> qualquer arquivo de logo/ícone no repositório. O sistema implementado
> hoje usa uma paleta azul/cinza neutra e a fonte "Segoe UI" em toda a
> interface (ver seção 2). Se a paleta de marca `#947F5E`/`#F1EBD7` for
> uma decisão de negócio pendente de implementação, ela deve ser tratada
> como um item de roadmap (`04_ROADMAP.md`), não como o estado atual.

---

# Objetivo

O Label Studio deve transmitir a mesma percepção de qualidade da marca
Santa Rubi.

A interface deve parecer um software profissional desenvolvido
exclusivamente para a empresa.

Não deve lembrar um ERP antigo.

Não deve utilizar elementos visuais exagerados.

A prioridade é elegância, simplicidade e produtividade.

---

# 1. Base técnica

- **Tema `ttk`:** `"clam"` (`ttk.Style(self.root).theme_use("clam")`, em
  `MainWindow._setup_style`) — com fallback silencioso (`try/except
  TclError`) caso o tema não esteja disponível no ambiente.
- **Fonte única em toda a interface:** `"Segoe UI"`. Nenhuma outra família
  de fonte foi encontrada em nenhum arquivo de `ui/`.
- **Fundo da janela principal:** `#f4f6f8` (`self.root.configure(bg=...)`).

# 2. Paleta de cores realmente implementada

| Uso | Cor | Onde |
|---|---|---|
| Texto de título | `#0f172a` | `Title.TLabel` |
| Texto secundário/legenda | `#64748b` | `Subtitle.TLabel`; também `fg` do código do produto nos cartões da fila |
| Fundo de cabeçalho/cartão | `#ffffff` | `Header.TFrame`, `Card.TFrame`, canvas da fila (`queue_canvas`) |
| Fundo de conteúdo | `#f4f6f8` | `Content.TFrame`, janela principal |
| Ação primária (fundo) | `#1d4ed8` (padrão) / `#2563eb` (hover/`active`) | `Primary.TButton` |
| Texto sobre ação primária | `#ffffff` | `Primary.TButton` |
| Borda discreta de cartão | `#dbe2ea` | `highlightbackground` dos cartões da Fila de Impressão |
| Item selecionado (fila) | `#dbeafe` | fundo do cartão selecionado em `CatalogTab._render_queue_cards` |
| Feedback de sucesso (Toast) | texto `#166534` sobre fundo `#dcfce7` | `ui/toast.py`, `Toast.SUCCESS` |
| Feedback informativo (Toast) | texto `#1d4ed8` sobre fundo `#dbeafe` | `ui/toast.py`, `Toast.INFO` |

Estilos `ttk` **definidos mas sem nenhum widget que os use atualmente**
(confirmado por busca em todo `ui/`): `Sidebar.TFrame`/`Sidebar.TLabel`/
`Sidebar.TRadiobutton` (fundo `#111827`, texto `#f8fafc`),
`DetailValue.TLabel` (`#334155` sobre `#ffffff`), e
`Slim.Horizontal.TProgressbar`. Prováveis resíduos de uma tela anterior
(a antiga aba "Impressão", com painel lateral escuro e barra de progresso
de impressão em lote) removida do código atual. Não devem ser usados como
referência para telas novas sem antes confirmar se serão reativados.

# 3. Tipografia

| Papel | Tamanho / peso |
|---|---|
| Título de janela/seção (`Title.TLabel`) | Segoe UI 18, negrito |
| Título de painel (ex.: "Integração Jueri", "Fila de Impressão") | Segoe UI 12–13, negrito (aplicado diretamente via `font=(...)` em cada `ttk.Label`, não um estilo nomeado) |
| Texto padrão (`TLabel`) | Segoe UI 10 |
| Texto secundário (`Subtitle.TLabel`) | Segoe UI 10, cor `#64748b` |
| Botões (`App.TButton` / `Primary.TButton`) | Segoe UI 10 (negrito no `Primary.TButton`) |
| Valor em destaque de estatística (ex.: "Habilitada", contagem de produtos) | Segoe UI 11, negrito |
| Mensagem do Toast | Segoe UI 9, negrito |

# 4. Componentes

## Botões

Dois estilos nomeados, usados de forma consistente em toda a interface
(`MainWindow`, `CatalogTab`, `ProductSearchDialog`, `SettingsDialog`):

- **`App.TButton`** — ação secundária/neutra (ex.: "Nova Pesquisa",
  "Limpar Resultado", "Selecionar Todos", "Testar Configuração").
- **`Primary.TButton`** — ação principal da tela (ex.: "Pesquisar Produtos
  (F3)", "Adicionar Selecionados à Fila", "Imprimir Fila (Ctrl+P)",
  "Recarregar Catálogo"). Fundo azul (`#1d4ed8`/`#2563eb` no hover), texto
  branco, negrito.

Botões que têm atalho de teclado equivalente mostram o atalho no próprio
rótulo entre parênteses (ex.: `"Pesquisar Produtos (F3)"`,
`"Imprimir Fila (Ctrl+P)"`, `"Limpar Fila (Ctrl+L)"`) — padrão introduzido
na rodada de atalhos globais e seguido desde então.

## Cards (`Card.TFrame`)

Fundo branco (`#ffffff`), usados para agrupar um bloco de informação com
`padding` generoso (12–16px) — painel "Integração Jueri", painel "Fila de
Impressão" (resumo, na aba API Jueri) e o painel lateral da Fila de
Impressão em "Planilha Excel". Não há sombra nem borda configurada
explicitamente nesses cards — a separação visual vem do espaçamento e do
contraste com o fundo `Content.TFrame` (`#f4f6f8`) ao redor.

Os **cartões individuais da Fila de Impressão** (um por produto, em
`CatalogTab._render_queue_cards`) são `tk.Frame` (não `ttk`) com borda
discreta de 1px (`#dbe2ea`) e fundo branco, ou azul claro (`#dbeafe`)
quando selecionados.

## Tabelas (`ttk.Treeview`)

Usadas em três lugares: tabela de resultado da pesquisa Jueri
(`MainWindow.jueri_results_tree`), tabela do catálogo
(`CatalogTab.catalog_tree`) e tabela de resultados de
`ProductSearchDialog.results_tree`. As três compartilham o mesmo
comportamento, via componentes reutilizáveis:

- Ordenação por coluna (clique no cabeçalho, 1º clique = crescente, 2º =
  decrescente) via `core/column_sort.py` (`ColumnSorter`) — número como
  número, texto sem acento/caixa, vazio sempre por último.
- Seleção múltipla por clique+Ctrl+Shift **e** por clique+arraste contínuo,
  via `ui/treeview_selection.py` (`enable_drag_selection`).
- Nenhuma cor de seleção customizada — usa o destaque padrão do tema
  `ttk`/Windows.

A **Fila de Impressão** de `CatalogTab` **não é uma Treeview**: é uma lista
de cartões `tk.Frame` dentro de um `tk.Canvas` com scrollbar (necessário
para os botões `[-]`/`[+]`/edição direta de cada item).

## Campos de pesquisa

Sempre um `ttk.Entry` associado a uma `tk.StringVar` com `trace_add`, que
dispara filtragem/busca a cada tecla (com debounce de 300ms em
`ProductSearchDialog`, sem debounce na busca local do catálogo, que é só
filtro em memória).

## Notificações (feedback discreto)

`ui/toast.py` (`Toast`) — controla um `tk.Label` já posicionado pela tela:
mostra uma mensagem colorida (verde para sucesso, azul para informativo) e
a apaga sozinha depois de alguns segundos (`DEFAULT_DURATION_MS = 3500`).
Usado em vez de `messagebox` para confirmações de rotina (ex.: "✓ 8
produtos adicionados à fila."). `messagebox` continua sendo usado para
avisos que exigem atenção do usuário (ex.: "selecione ao menos um produto",
erros de impressão, confirmação de fila vazia após imprimir).

## Abas (`ttk.Notebook`)

Duas abas fixas: "API Jueri" e "Planilha Excel". Nenhuma cor customizada
foi encontrada para o próprio `ttk.Notebook` — usa a aparência padrão do
tema `clam`.

## Cabeçalho

`Header.TFrame` (fundo branco), fixo no topo da janela, fora do
`Notebook` — contém o título da aplicação (`Title.TLabel`) e o botão
"Configurações" (`App.TButton`), visível independentemente da aba ativa.

---

# 5. Ícones

Nenhuma biblioteca de ícones foi encontrada em uso. Os únicos "ícones" da
interface são caracteres Unicode usados como texto simples: `★`/`☆`
(favoritar/desfavoritar pesquisas), `×` (remover), `✓` (mensagens de
sucesso no Toast), `▼`/`▶` (expandir/recolher o painel de configuração do
catálogo).

# 6. Espaçamentos

Não há uma escala numérica de espaçamento formalmente declarada em código
(nenhuma constante tipo `SPACING_SM`/`SPACING_MD` foi encontrada). Os
valores de `padding`/`pady`/`padx` são literais, repetidos por convenção:
`padding=12` ou `padding=16` para painéis/cards, `pady=(0, 12)` entre
seções empilhadas verticalmente, `padx=(0, 8)` entre botões numa mesma
linha.

# 7. Experiência do Usuário

Toda alteração deve buscar reduzir cliques.

Toda ação importante deve fornecer feedback visual — no código atual, isso
é implementado via `Toast` (ações de rotina) ou `messagebox` (avisos que
bloqueiam o fluxo até serem reconhecidos).

A interface deve parecer rápida — pesquisa/filtro/ordenação do catálogo
nunca releem a planilha (`CatalogRepository` mantém cache em memória).

O usuário nunca deve perder contexto durante uma operação — por isso
adicionar produtos à fila pela aba "API Jueri" **não muda mais de aba
automaticamente** (decisão explícita, revertendo um comportamento anterior
do próprio sistema).

---

# Princípios

Sempre preservar:

- simplicidade
- produtividade
- consistência
- elegância
- estabilidade

A experiência do operador é prioridade.
