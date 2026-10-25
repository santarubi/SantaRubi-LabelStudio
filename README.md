# Santa Rubi Label Studio

Sistema desktop para Windows, feito para a Santa Rubi, que lê o cadastro de
produtos (planilhas Excel) e imprime etiquetas de 30×15mm numa impressora
térmica ELGIN L42PRO FULL, via comando ZPL nativo (RAW), sem depender do
driver gráfico do Windows.

**Versão atual homologada em produção:** `v1.2.0`. Ver
[CHANGELOG.md](CHANGELOG.md) para o histórico completo de versões,
[ARCHITECTURE.md](ARCHITECTURE.md) para a documentação técnica e
[docs/RELEASE_v1.1.2.md](docs/RELEASE_v1.1.2.md) para o processo de release.

## Visão geral

A aplicação tem duas abas de origem de produtos e uma fila universal:

- **API Jueri** — pesquisa por código/descrição e datas, filtros de estoque e
  categoria, ordenação, favoritos e pesquisas recentes.
- **Planilha Excel** — catálogo permanente configurável, com múltiplas abas,
  mapeamento de colunas, pesquisa e filtros locais.
- **Fila de Impressão Universal** — permanece visível à direita das duas abas e
  recebe itens de ambas as origens no mesmo `PrintQueue`. Permite ajustar
  quantidade, remover um ou vários itens, limpar com confirmação e imprimir.

As duas abas convergem no mesmo motor de impressão (`ZplBuilder` +
`PrinterService`), o que garante que qualquer correção ou calibração física
feita em um lugar vale para as duas.

## Funcionalidades

**Aba "Impressão"**
- Leitura de planilha Excel (`.xlsx`) com detecção automática de colunas
  (`CODIGO`, `CATEGORIA`, `DESCRICAO`, `PRECO`, `NUMERO`, `QTD`).
- Pesquisa instantânea (case/acento-insensível) e filtro por categoria.
- Seleção múltipla na tabela (clique, Ctrl, Shift, arraste contínuo).
- Contadores de Total / Exibindo / Selecionados sempre atualizados.
- Impressão unitária, impressão de teste, impressão em lote (todos ou por
  intervalo) e impressão apenas dos produtos selecionados.
- Pré-visualização da etiqueta redimensionável (bitmap, independente do
  motor de impressão).
- Atalhos: Ctrl+F, ESC, Ctrl+A, Enter, duplo clique.
- Memória da última planilha e da última impressora usadas.

**Aba "Catálogo Integrado"**
- Configuração de fonte de dados própria: arquivo, abas selecionáveis e
  mapeamento de colunas (com quantidade padrão de impressão), validável via
  "Testar Configuração".
- Catálogo carregado inteiramente em memória (cache), com pesquisa, filtro
  por fornecedor/categoria e ordenação por coluna — nunca relê o Excel a
  cada pesquisa, só ao clicar em "Recarregar Catálogo".
- Painel de configuração recolhível, para maximizar o espaço da tabela.
- **Fila de Impressão** num painel lateral: adicionar produtos selecionados
  (sem duplicar — incrementa a quantidade se o produto já estiver na fila),
  remover, limpar, ajustar quantidade (`[-]`/`[+]` ou edição direta por
  duplo clique), atalho DEL para remover o item selecionado.
- Botão "Imprimir Fila": converte a fila para o motor de impressão existente
  em uma thread separada (interface nunca trava), com confirmação de
  sucesso, opção de limpar a fila ao final, e tratamento de erro que nunca
  descarta a fila.
- Log de cada trabalho de impressão (`data/print_log.txt`): horário,
  produtos, etiquetas, tempo total e resultado.

## Requisitos

- Windows (testado com impressora ELGIN L42PRO FULL via spooler `RAW`).
- Python 3.12.
- Uma impressora térmica instalada e visível no Windows (`win32print`).

## Instalação

1. Clone ou copie o projeto para a máquina.
2. Crie e ative um ambiente virtual:

   ```
   python -m venv venv
   venv\Scripts\activate
   ```

3. Instale as dependências:

   ```
   pip install -r requirements.txt
   ```

## Como executar

```
python app.py
```

Isso abre a janela principal com as abas "API Jueri" e "Planilha Excel". A fila
universal permanece visível na lateral direita ao alternar entre elas.

## Build de produção

A release v1.2.0 é gerada separadamente dos artefatos de desenvolvimento:

```
python -m pip install -r requirements-release.txt
python scripts/build_release.py
```

O resultado fica em `release/v1.2.0/` e contém somente o EXE
destinado ao usuário e o relatório `RELEASE_INFO.txt`. Artefatos de versões
anteriores na raiz de `release/` não são sobrescritos. O Launcher continua
exclusivo do ambiente de desenvolvimento e não faz parte do pacote de produção.

## Estrutura do projeto

```
SantaRubi-LabelStudio/
│
├── app.py                        # Ponto de entrada (cria a janela e chama mainloop)
├── requirements.txt               # openpyxl, Pillow, python-barcode, reportlab, pywin32
├── README.md                      # Este arquivo
├── CHANGELOG.md                   # Histórico de versões
├── ARCHITECTURE.md                # Documentação técnica de arquitetura
├── ROADMAP.md                     # O que já foi feito e o que vem a seguir
├── DOCUMENTACAO_CHECKPOINT.md     # Registro histórico detalhado de cada marco/checkpoint
├── CLAUDE.md                      # Regras de desenvolvimento do projeto
│
├── core/                          # Lógica de negócio — sem Tkinter
│   ├── config.py                  # Preferências em %LOCALAPPDATA%/Santa Rubi Label Studio
│   ├── excel_reader.py            # Leitura/validação da planilha da aba "Impressão"
│   ├── barcode.py                 # Código de barras para o preview (bitmap)
│   ├── label_renderer.py          # Renderização bitmap da etiqueta (SOMENTE preview)
│   ├── print_layout.py            # Única fonte de constantes físicas de layout
│   ├── label_data.py              # LabelData — etiqueta tipada para o motor de impressão
│   ├── zpl_builder.py             # Geração do comando ZPL (SOMENTE impressão)
│   ├── printer.py                 # Comunicação com a impressora Windows (RAW/ZPL)
│   ├── print_item.py              # PrintItem — uma solicitação de impressão
│   ├── print_queue.py             # PrintQueue — fila de impressão (coleção rica)
│   ├── print_queue_adapter.py     # PrintQueueAdapter — PrintQueue -> list[LabelData]
│   ├── print_log.py               # Log de trabalhos de impressão da fila
│   ├── catalog_datasource.py      # DataSource (interface abstrata do catálogo)
│   ├── catalog_excel_source.py    # ExcelCatalogSource — implementação concreta
│   ├── catalog_repository.py      # Cache em memória + carregamento do catálogo
│   ├── catalog_product.py         # CatalogProduct — entidade permanente do catálogo
│   ├── catalog_service.py         # Busca, filtro, ordenação, estatísticas
│   ├── catalog_settings.py        # Configuração persistida do Catálogo Integrado
│   ├── catalog_validator.py       # Validação da configuração (arquivo/abas/colunas)
│   └── text_normalize.py          # Normalização de texto para busca (acento/caixa)
│
├── ui/                             # Telas Tkinter/ttk
│   ├── main_window.py              # Janela principal + aba "Impressão"
│   └── catalog_tab.py              # Aba "Catálogo Integrado" + Fila de Impressão
│
├── tests/                          # Suíte de testes automatizados (unittest)
├── assets/                         # Ícones/imagens (reservado)
├── layouts/                        # Templates de layout futuros (reservado)
└── data/                           # Reservado para dados de desenvolvimento
```

Ver [ARCHITECTURE.md](ARCHITECTURE.md) para a responsabilidade detalhada de
cada módulo e o fluxo completo de dados entre eles.

## Tecnologias utilizadas

- Python 3.12
- Tkinter / ttk (interface gráfica)
- openpyxl (leitura de planilhas Excel)
- Pillow (renderização do preview em bitmap)
- python-barcode (código de barras do preview)
- reportlab
- pywin32 (`win32print` — comunicação RAW com a impressora Windows)
