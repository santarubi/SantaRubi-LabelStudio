# Santa Rubi Label Studio — v3.0-stable

**Data de lançamento:** 2026-07-21
**Tag:** `v3.0-stable`
**Status:** Arquitetura oficialmente congelada

---

## Resumo da versão

A v3.0 marca o encerramento de um ciclo completo de evolução do Santa
Rubi Label Studio: a introdução do **Catálogo Integrado** — um catálogo de
produtos permanente, configurável e com fila de impressão própria — e uma
rodada final de refinamento arquitetural que eliminou toda duplicação de
lógica e de constantes entre ele e a aba "Impressão" original.

Ao final desta versão, o sistema tem duas telas completas de impressão de
etiquetas e um único motor de impressão compartilhado entre elas, sem
nenhum caminho de código duplicado. Esta é considerada a base estável a
partir da qual o projeto deve evoluir de forma incremental — não mais por
refatoração recorrente da mesma arquitetura.

## Principais funcionalidades

### Catálogo Integrado (novo nesta versão)
- Fonte de dados própria e permanente, independente da planilha avulsa da
  aba "Impressão": seleção de arquivo, múltiplas abas, mapeamento de
  colunas (incluindo quantidade padrão de impressão), com validação via
  "Testar Configuração".
- Catálogo inteiro carregado em memória, com cache — pesquisa, filtro por
  fornecedor/categoria e ordenação por coluna nunca releem o Excel.
- Painel de configuração recolhível, para maximizar o espaço da tabela no
  dia a dia.
- **Fila de Impressão** num painel lateral: adicionar produtos
  selecionados (sem duplicar — incrementa quantidade se já existir),
  remover, limpar, ajustar quantidade pelos botões `[-]`/`[+]` ou por
  edição direta (duplo clique), atalhos de teclado DEL e Ctrl+A.
- Botão **"Imprimir Fila"**: converte a fila e envia para o mesmo motor de
  impressão da aba "Impressão", em thread separada (interface nunca
  trava), com confirmação de sucesso, opção de limpar a fila ao final, e
  tratamento de erro que nunca descarta o que foi montado.
- Log de cada trabalho de impressão da fila (`data/print_log.txt`):
  horário, produtos, etiquetas, tempo total e resultado.

### Aba "Impressão" (herdada, sem mudança de comportamento)
- Leitura de planilha Excel, pesquisa instantânea, filtro por categoria,
  seleção múltipla (clique/Ctrl/Shift/arraste), contadores em tempo real.
- Impressão unitária, de teste, em lote (todos ou por intervalo) e dos
  produtos selecionados — agrupada automaticamente em linhas de 3 colunas
  conforme a calibração física do rolo.
- Pré-visualização redimensionável, independente do motor de impressão.

## Principais decisões arquiteturais

Registradas formalmente em [`docs/DECISIONS.md`](DECISIONS.md) (ADRs
001–009). Resumo:

1. **Existe apenas um pipeline de impressão** — `ZplBuilder` +
   `PrinterService`, compartilhado pelas duas abas; nenhum motor paralelo.
2. **`PrintQueue` é a única fonte da fila** — nenhuma cópia de estado fora
   dela; toda leitura/escrita passa por seus métodos públicos.
3. **`LabelData` substitui `dict`** — etiqueta tipada e imutável na
   fronteira com o motor de impressão.
4. **`PrintLayout` centraliza todas as constantes físicas** — uma única
   fonte de calibração, importada por `ZplBuilder` e pelas duas telas.
5. **`CatalogService` concentra as regras de negócio** do catálogo — a
   interface é presentation-only.
6. **`CatalogRepository` só cuida de acesso a dados** — único ponto que
   toca a origem (Excel); cache em memória para tudo o mais.
7. **`PrintQueueAdapter` só adapta dados** — nenhuma regra de impressão
   nele.
8. **A interface nunca manipula listas internas diretamente** — sempre
   via métodos de domínio (`PrintQueue`, `CatalogService`).
9. **Arquitetura congelada na v3.0** — evoluções futuras devem ser
   incrementais sobre esta base.

## Arquitetura final

```
┌─────────────────────────────────────────────────────────────────┐
│  UI (Tkinter/ttk)                                                │
│  ui/main_window.py            ui/catalog_tab.py                  │
│  (aba "Impressão")             (aba "Catálogo Integrado")         │
└──────────────┬──────────────────────────┬────────────────────────┘
               │                          ▼
               │                 CatalogRepository → CatalogService
               │                          │
               │                          ▼
               │                 PrintItem → PrintQueue
               │                          │
               │                          ▼
               │                 PrintQueueAdapter
               │                          │
               ▼                          ▼
                    LabelData (tipado, imutável)
                              │
                              ▼
                 ZplBuilder (build / build_row)  ◄── core/print_layout.py
                              │
                              ▼
                      PrinterService.print_raw()
                              │
                              ▼
                       ELGIN L42PRO FULL
```

Em paralelo e totalmente desacoplado, o pipeline de pré-visualização
(`LabelRenderer` + `core/barcode.py`) desenha o bitmap mostrado em tela na
aba "Impressão" — nunca importa nem é importado pelo caminho de impressão
real. Detalhamento completo por módulo em
[`ARCHITECTURE.md`](../ARCHITECTURE.md).

## Pipeline definitivo

```
LabelData (um por etiqueta)
        │
        ▼
ZplBuilder.build_row(labels, column_pitch=BATCH_COLUMN_PITCH,
                      total_width=BATCH_COLUMN_PITCH * BATCH_ROW_COLUMNS)
        │   (agrupado em blocos de BATCH_ROW_COLUMNS = 3 —
        │    calibração física do rolo, em core/print_layout.py)
        ▼
   comando ZPL (^XA...^XZ)
        │
        ▼
PrinterService(printer_name).print_raw(zpl)
        │
        ▼
   spooler RAW do Windows
        │
        ▼
   ELGIN L42PRO FULL
```

`ZplBuilder.build()` (etiqueta única, usado pela impressão de teste/rápida
da aba "Impressão") mantém compatibilidade com `dict`, convertendo para
`LabelData` internamente — sem alterar nenhum cálculo, posicionamento ou
byte da saída ZPL gerada.

## Quantidade de testes

**191 testes automatizados, 100% passando** (`python -m unittest discover
-s tests`), cobrindo:
- Motor de impressão: geração de ZPL, layout, constantes centralizadas.
- Domínio de impressão: `PrintItem`, `PrintQueue`, `LabelData`,
  `PrintQueueAdapter`.
- Domínio do catálogo: repositório (com prova de cache via contagem de
  leituras), serviço, configuração, validador.
- Interface: fila visual, edição de quantidade, atalhos de teclado, fluxo
  completo de impressão com `build_row()`/`print_raw()` mocados —
  **nenhum teste envia dados para uma impressora real**.

Validação adicional: a saída de `build()`/`build_row()` foi comparada
byte a byte contra a versão anterior à centralização de constantes —
idêntica em todos os cenários testados.

## Tecnologias

- Python 3.12
- Tkinter / ttk
- openpyxl
- Pillow
- python-barcode
- reportlab
- pywin32 (`win32print`)

## Estrutura do projeto

```
SantaRubi-LabelStudio/
├── app.py
├── requirements.txt
├── README.md · CHANGELOG.md · ARCHITECTURE.md · ROADMAP.md
├── docs/
│   ├── DECISIONS.md              # ADRs 001–009
│   └── RELEASE_NOTES_v3.0.md     # este documento
├── DOCUMENTACAO_CHECKPOINT.md    # histórico detalhado de cada marco
│
├── core/
│   ├── print_layout.py            # única fonte de constantes físicas
│   ├── label_data.py               # LabelData
│   ├── zpl_builder.py              # motor de geração de ZPL
│   ├── printer.py                   # comunicação RAW com a impressora
│   ├── print_item.py · print_queue.py · print_queue_adapter.py · print_log.py
│   ├── catalog_datasource.py · catalog_excel_source.py
│   ├── catalog_repository.py · catalog_product.py
│   ├── catalog_service.py · catalog_settings.py · catalog_validator.py
│   ├── text_normalize.py
│   ├── config.py · excel_reader.py · barcode.py · label_renderer.py
│
├── ui/
│   ├── main_window.py              # janela principal + aba "Impressão"
│   └── catalog_tab.py               # aba "Catálogo Integrado" + Fila de Impressão
│
├── tests/                            # 191 testes (unittest)
├── assets/ · layouts/ · data/        # reservados / gerados em runtime
```

## Melhorias em relação às versões anteriores

| Versão | Entrega | O que a v3.0 mudou |
|---|---|---|
| `v1.0-print-engine` → `v1.3-produtividade` | Motor RAW+ZPL, impressão em lote inteligente, layout calibrado, produtividade da UI | Nenhuma mudança de comportamento — base preservada integralmente |
| Catálogo Integrado (ciclo desta versão) | Catálogo permanente + Fila de Impressão | Funcionalidade nova, construída sem duplicar o motor de impressão existente |
| Refinamento final | `PrintLayout` + `LabelData` | Eliminou a última duplicação de constantes físicas e o `list[dict]` sem tipo entre catálogo e motor de impressão |

Em relação ao estado logo após a introdução do Catálogo Integrado, a v3.0
especificamente:
- Centralizou em `core/print_layout.py` constantes que estavam
  duplicadas entre `ZplBuilder`, `ui/main_window.py` e `ui/catalog_tab.py`.
- Substituiu o `list[dict]` entre `PrintQueueAdapter` e
  `ZplBuilder.build_row()` por `LabelData`, tipado e imutável.
- Confirmou, por comparação byte a byte, que nenhuma dessas mudanças
  alterou a etiqueta impressa.

## Limitações conhecidas

- **Mensagem de erro "Unable to open printer"** ainda pode ocorrer
  dependendo de permissões/configuração local do Windows — é uma
  condição do sistema operacional/driver, não do código da aplicação, que
  já reporta o erro de forma clara ao usuário.
- **Erros de impressão são reportados de forma genérica** (texto cru da
  exceção), sem distinguir "impressora offline", "sem permissão" ou "sem
  papel".
- **Sem peso de fonte real (negrito) no ZPL** — todos os campos usam a
  mesma fonte escalável; a fonte bitmap alternativa já foi tentada duas
  vezes e revertida por instabilidade de escala no firmware da
  impressora.
- **Layout de etiqueta único e fixo** — calibrado especificamente para
  30×15mm na ELGIN L42PRO FULL; não há suporte a múltiplos modelos de
  etiqueta ou impressora.
- **Edição de quantidade direta na interface** existe apenas na Fila de
  Impressão do Catálogo Integrado — a aba "Impressão" ainda depende da
  coluna `QTD` da planilha.
- **Duplicação residual não crítica**: `APP_TITLE` é um literal repetido
  entre `ui/main_window.py` e `ui/catalog_tab.py`, e algumas fixtures de
  teste (`FakeDataSource`, `_tk_available`) se repetem em vários arquivos
  de teste — sem risco funcional, identificado na auditoria completa do
  projeto.

## Próximos passos

Detalhado em [`ROADMAP.md`](../ROADMAP.md). Candidatas priorizadas, sem
compromisso de prazo:
- Tratamento mais específico de erros de impressão.
- Edição de quantidade também na aba "Impressão".
- Distribuição do sistema como executável Windows (ex.: PyInstaller).
- Funcionalidades administrativas (histórico de impressão na própria
  interface, painel de favoritos).

---

*Para o histórico completo de decisões, ver [`docs/DECISIONS.md`](DECISIONS.md).
Para o registro detalhado de cada etapa deste ciclo, ver
[`DOCUMENTACAO_CHECKPOINT.md`](../DOCUMENTACAO_CHECKPOINT.md), capítulo
"Checkpoint v3.0-stable".*
