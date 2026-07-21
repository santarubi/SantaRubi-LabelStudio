# Santa Rubi Label Studio

Sistema desktop para Windows, feito para a Santa Rubi, que lê o cadastro de
produtos (planilhas Excel) e imprime etiquetas de 30×15mm numa impressora
térmica ELGIN L42PRO FULL, via comando ZPL nativo (RAW), sem depender do
driver gráfico do Windows.

**Versão atual:** `v3.0-stable` — arquitetura de impressão e catálogo
consolidadas. Ver [CHANGELOG.md](CHANGELOG.md) para o histórico completo de
versões e [ARCHITECTURE.md](ARCHITECTURE.md) para a documentação técnica.

## Visão geral

A aplicação tem duas telas (abas), cada uma resolvendo um problema diferente
do dia a dia da loja:

- **Aba "Impressão"** — fluxo original e mais direto: carrega uma planilha
  Excel, permite pesquisar/filtrar/selecionar produtos na tabela e imprimir
  (unitária, em lote ou apenas os selecionados). Congelada desde a versão
  `v1.3-produtividade`.
- **Aba "Catálogo Integrado"** — um catálogo permanente e configurável
  (múltiplas abas/planilhas, mapeamento de colunas), com uma **Fila de
  Impressão** própria: o usuário monta a fila (adicionar, remover, ajustar
  quantidade pelo `[-]`/`[+]` ou edição direta) e imprime tudo de uma vez,
  reaproveitando integralmente o mesmo motor de impressão da aba
  "Impressão" — nenhum código de impressão é duplicado entre as duas.

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

Isso abre a janela principal com as duas abas ("Impressão" e "Catálogo
Integrado"). Cada aba é independente: comece pela que fizer sentido para a
tarefa (impressão pontual a partir de uma planilha, ou o catálogo permanente
configurado uma vez e reutilizado no dia a dia).

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
│   ├── config.py                  # Persistência de preferências (data/config.json)
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
└── data/                           # config.json, print_log.txt (gerados em tempo de execução)
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
