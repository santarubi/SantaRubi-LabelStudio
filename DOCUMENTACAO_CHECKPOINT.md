# Santa Rubi Label Studio — Documentação Oficial de Arquitetura

**Checkpoint:** Migração definitiva do motor de impressão para RAW + ZPL
**Data:** 2026-07-21
**Status:** Arquitetura de impressão consolidada, testes automatizados passando, código legado removido.

Este documento é a fonte oficial de arquitetura do sistema. Qualquer
desenvolvedor deve conseguir continuar o projeto a partir daqui sem precisar
ter acompanhado o histórico de sessões anteriores.

---

## 1. Estado atual do projeto

O Santa Rubi Label Studio é uma aplicação desktop Windows (Python 3.12 +
Tkinter/ttk) para impressão de etiquetas de 30×15mm em impressora térmica
ELGIN L42PRO FULL, a partir de uma planilha Excel de produtos.

O projeto está em um marco estável e consolidado:

- **Arquitetura de impressão consolidada.** Existe hoje um único caminho de
  impressão em produção: geração de comando ZPL (`ZplBuilder`) enviado como
  dado bruto (`RAW`) para o spooler do Windows (`PrinterService.print_raw`).
  Não existe mais nenhum caminho de impressão via driver GDI.
- **Impressão totalmente funcional via RAW + ZPL.** Os três pontos de
  impressão da interface (teste, impressão rápida e impressão em lote) usam
  exclusivamente `ZplBuilder` + `PrinterService.print_raw()`. O layout foi
  calibrado fisicamente contra impressões reais na ELGIN L42PRO FULL.
- **Preview independente.** A pré-visualização em tela continua sendo gerada
  por `LabelRenderer` (bitmap Pillow desenhado num `Canvas` Tkinter) e não
  depende, em nenhum nível, do código de impressão. Preview e impressão são
  hoje dois pipelines paralelos e desacoplados, que só compartilham o mesmo
  dicionário de produto como entrada.
- **Testes automatizados passando.** 7 testes unitários cobrindo leitura de
  planilha, seleção de lote e renderização do preview — suíte 100% verde.
- **Código legado removido.** Todo o caminho de impressão via GDI
  (`print_image`, `_build_label_devmode`, DEVMODE customizado, constantes de
  papel, imports `win32con`/`win32gui`/`win32ui`/`ImageWin`) foi removido de
  `core/printer.py` após confirmação de que nenhum ponto da UI ainda o
  utilizava. Um método morto (`_build_label_image`) também foi removido de
  `ui/main_window.py`.
- Todos os scripts temporários de diagnóstico (`temp_*.py`) e imagens de
  calibração geradas durante o processo (`label_*.png`, `debug_*.png`) foram
  removidos do repositório — eram todos arquivos não versionados, criados
  apenas para os testes físicos desta migração.

O projeto está pronto para evoluir sobre uma base limpa: um módulo de
impressão de ~70 linhas com responsabilidade única, um construtor de ZPL
isolado e testável, e um preview que pode ganhar funcionalidades (múltiplos
layouts, histórico, favoritos) sem nunca arriscar quebrar a impressão.

---

## 2. Histórico completo

### 2.1 Ponto de partida: impressão via GDI

A primeira versão funcional da impressão usava o caminho tradicional do
Windows: `LabelRenderer` desenhava a etiqueta como uma imagem Pillow
240×120px (203 DPI ≈ 8 dots/mm para 30×15mm), e `PrinterService.print_image()`
enviava essa imagem para a impressora via GDI (`win32gui.CreateDC` +
`win32ui.CreateDCFromHandle` + `PIL.ImageWin.Dib`), usando um DEVMODE
customizado (`_build_label_devmode()`) para forçar o tamanho de papel
30×15mm (`PaperWidth=300`, `PaperLength=150` em décimos de mm, `FormName`
customizado).

### 2.2 Problemas encontrados

- **"Unable to open printer"**: erro intermitente do Windows relacionado a
  permissão/acesso à impressora, que motivou a primeira rodada de
  investigação de todo o pipeline (criação de DC, DEVMODE, nome da
  impressora selecionada).
- **Corte de conteúdo na lateral direita da etiqueta**: mesmo depois de
  corrigir a criação do DC (`CreateDC()` + `CreatePrinterDC()`), o conteúdo
  desenhado próximo à borda direita da imagem era cortado na impressão física.
- **Etiqueta "torta"** e elementos posicionados incorretamente em relação ao
  layout exigido pelo cliente (código de barras grande colado no topo,
  código do produto logo abaixo, categoria à direita, descrição centralizada,
  número à esquerda e preço à direita na última linha).

### 2.3 Diagnósticos realizados

Foi escrito um teste temporário isolado que consultava diretamente
`hdc.GetDeviceCaps()` (via `win32ui`) comparando `HORZRES`/`VERTRES` (área
realmente utilizável reportada pelo driver) contra `PHYSICALWIDTH`/
`PHYSICALHEIGHT` (dimensão física total do papel). Esse teste foi rodado
explicitamente contra a impressora correta (ELGIN L42PRO FULL, não a Kyocera
usada por engano na primeira tentativa).

### 2.4 Descoberta do limite do driver Windows

O diagnóstico confirmou um teto físico do driver: de 240 dots de largura
nominal da etiqueta, o driver GDI da ELGIN só reportava com segurança
~220 dots de área utilizável (`HORZRES` bem abaixo de `PHYSICALWIDTH`). Ou
seja, **~20 dots de cada lado eram sacrificados como margem de segurança
imposta pelo próprio driver**, independentemente de como a imagem era
desenhada em Python.

Isso foi confirmado como um limite real do driver (não um bug de código)
quando o usuário relatou que **outro sistema de PDV instalado na mesma
máquina, usando a mesma impressora física, conseguia usar 100% da área útil
da etiqueta**. Isso só é possível se aquele sistema não estivesse passando
pelo driver GDI da forma tradicional — ou seja, provavelmente enviando
comandos nativos da impressora diretamente.

### 2.5 Decisão de abandonar o GDI

Depois de várias rodadas de calibração de margem sem conseguir superar o
teto de ~220/240px do driver, e com a evidência de que outro sistema usava
a etiqueta inteira na mesma impressora, foi tomada a decisão explícita de
abandonar completamente o caminho GDI/DEVMODE e migrar para **impressão RAW**:
enviar comandos ZPL (Zebra Programming Language) diretamente para a fila de
impressão, com `pDatatype="RAW"`, contornando o driver Windows por completo.
O firmware da própria impressora passa a ser responsável por desenhar
código de barras, texto e posicionamento na resolução nativa (203 dpi).

### 2.6 Criação do `ZplBuilder`

Foi criado o módulo `core/zpl_builder.py`, responsável por montar o comando
ZPL (texto puro) a partir do dicionário de produto — sem nenhuma dependência
de Pillow, Tkinter ou GDI. O layout foi recalibrado do zero, fisicamente,
contra fotos de etiquetas reais impressas pelo usuário: margens, tamanhos de
fonte, altura do código de barras, alinhamento de cada campo e truncamento
defensivo de texto foram ajustados em múltiplas rodadas (detalhes completos
no Capítulo 7).

Durante essa recalibração surgiu um problema de replicação: como o rolo de
etiquetas está calibrado para 3 colunas por linha, enviar 3 jobs `^XA...^XZ`
separados (um por produto) fazia a impressora repetir cada job nas 3
colunas físicas (3 produtos → 9 etiquetas impressas). A solução foi o método
`ZplBuilder.build_row()`, que monta um único `^XA...^XZ` cobrindo a largura
total das N colunas, deslocando os campos de cada produto por
`x_offset = index * column_pitch`.

Também foi tentado, e revertido, o uso da fonte ZPL "D" (bitmap) para
diferenciar campos em negrito dos campos sem negrito — a fonte D não
escalou de forma confiável no firmware desta impressora (sobreposição de
texto em duas tentativas seguidas, mesmo após reduzir o tamanho pedido). A
decisão foi reverter para a fonte "0" (escalável) em todos os campos, em vez
de arriscar mais uma etiqueta física em uma terceira tentativa às cegas —
ver Capítulo 13 para a lição geral por trás dessa decisão.

### 2.7 Migração da UI

Com o layout ZPL validado fisicamente (inclusive o teste de 3 colunas), a
interface (`ui/main_window.py`) foi migrada para usar exclusivamente
`ZplBuilder` + `PrinterService.print_raw()` nos três pontos que antes
chamavam `LabelRenderer.render_image()` + `PrinterService.print_image()`:
impressão de teste, impressão em lote e impressão rápida. A
pré-visualização foi deliberadamente **mantida intacta e independente**,
continuando a usar `LabelRenderer` apenas para desenhar o bitmap mostrado em
tela.

### 2.8 Remoção do código legado

Só depois de confirmar (por busca em todo o repositório) que nenhum ponto da
UI ainda chamava `print_image()`, o código exclusivo do caminho GDI foi
removido de `core/printer.py`: o método `print_image()`, o método
`_build_label_devmode()`, as constantes `LABEL_PAPER_WIDTH`/
`LABEL_PAPER_LENGTH`/`LABEL_FORM_NAME` e os imports `win32con`/`win32gui`/
`win32ui`/`PIL.Image`/`PIL.ImageWin`. Um método morto equivalente do lado da
UI (`_build_label_image`, que já não tinha nenhum chamador antes mesmo desta
migração) também foi removido. Ver Capítulo 9 para o detalhamento completo.

### 2.9 Arquitetura final

O resultado é a arquitetura descrita no Capítulo 3: dois pipelines paralelos
e independentes — um puramente textual (ZPL → RAW → spooler → impressora)
para impressão, e um puramente bitmap (Pillow → Canvas Tkinter) para
pré-visualização — que só se encontram no dicionário de produto que os
alimenta.

---

## 3. Arquitetura atual

A aplicação tem hoje dois fluxos totalmente independentes a partir do mesmo
dado de entrada (o dicionário de produto):

### 3.1 Fluxo de impressão (RAW + ZPL)

```
                Produto
                    │
                    ▼
              ZplBuilder
                    │
                    ▼
            PrinterService
                    │
                    ▼
             Spooler RAW
                    │
                    ▼
             ELGIN L42 PRO
```

### 3.2 Fluxo de pré-visualização (bitmap)

```
                Produto
                    │
                    ▼
             LabelRenderer
                    │
                    ▼
              Preview Tkinter
```

### 3.3 Por que são independentes

Não existe nenhuma chamada entre os dois fluxos: `ZplBuilder` nunca importa
`LabelRenderer` (nem `Pillow`), e `LabelRenderer` nunca importa
`ZplBuilder` (nem `win32print`). `core/printer.py` hoje só sabe falar
`RAW`/ZPL com a impressora — não sabe desenhar nada. `core/label_renderer.py`
só sabe desenhar um bitmap — não sabe nada sobre impressoras.

Essa separação é intencional: ela garante que ajustes no layout impresso
(ex.: recalibrar uma margem em dots ZPL) nunca podem quebrar acidentalmente
a pré-visualização em tela, e vice-versa. O preço dessa independência é que
os dois módulos mantêm cada um seu próprio conjunto de constantes de layout
(margens, tamanhos de fonte, posições Y) — eles descrevem visualmente a
*mesma* etiqueta, mas em duas unidades e mecanismos de renderização
diferentes (dots ZPL vs. pixels Pillow). Isso é uma duplicação deliberada,
não um descuido — ver Capítulo 8.

---

## 4. Estrutura do projeto

```
core/
├── barcode.py        # Geração da imagem do código de barras (para o preview)
├── config.py          # Persistência simples de preferências do usuário (JSON)
├── excel_reader.py    # Leitura e validação da planilha Excel de produtos
├── label_renderer.py  # Renderização bitmap da etiqueta (SOMENTE preview)
├── printer.py         # Comunicação com a impressora Windows (RAW/ZPL)
└── zpl_builder.py      # Geração do comando ZPL (SOMENTE impressão)
ui/
└── main_window.py     # Interface Tkinter/ttk completa (única janela)
tests/
├── test_batch_flow.py       # Fluxo de obtenção de produtos para impressão em lote
├── test_batch_selection.py # Seleção de produtos por intervalo/todos
├── test_excel_reader.py     # Leitura e validação de planilha
└── test_label_renderer.py  # Dimensão do bitmap de preview (240×120)
app.py                  # Ponto de entrada (cria a janela e chama mainloop)
requirements.txt        # openpyxl, Pillow, python-barcode, reportlab, pywin32
assets/ layouts/ data/  # Reservados pela arquitetura (CLAUDE.md); ainda vazios
```

### Detalhamento por arquivo

**`app.py`**
- Responsabilidade: único ponto de entrada do programa. Cria a `tk.Tk()`
  raiz, instancia `MainWindow` e chama `root.mainloop()`.
- Dependências: `ui.main_window.MainWindow`.
- Quem usa: executado diretamente (`python app.py`).

**`core/excel_reader.py` (`ExcelReader`)**
- Responsabilidade: abrir um `.xlsx`, validar cabeçalhos obrigatórios
  (`CODIGO`, `CATEGORIA`, `DESCRICAO`, `PRECO`, com aliases para variações de
  nome/acentuação), e permitir buscar um produto por código
  (`buscar_produto()`). É uma camada de leitura/consulta pura — nunca
  desenha nem imprime nada.
- Dependências: `openpyxl`.
- Quem usa: `ui/main_window.py` (importação e listagem de produtos).

**`core/config.py` (`ConfigManager`)**
- Responsabilidade: carregar/salvar preferências do usuário em
  `data/config.json` (sem banco de dados).
- Dependências: apenas biblioteca padrão (`json`, `pathlib`).
- Quem usa: `ui/main_window.py`.

**`core/barcode.py` (`BarcodeGenerator`)**
- Responsabilidade: gerar a imagem Pillow (`RGBA`) de um código de barras
  Code128, calculando módulo/altura para caber num tamanho pedido em pixels.
- Dependências: `python-barcode` (`Code128`, `ImageWriter`), `Pillow`.
- Quem usa: **somente** `core/label_renderer.py` (o preview). O caminho de
  impressão (`ZplBuilder`) gera o código de barras via comando nativo
  `^BCN` da própria impressora — não usa esta classe.

**`core/label_renderer.py` (`LabelRenderer`)**
- Responsabilidade: desenhar a etiqueta completa como uma imagem Pillow
  240×120 (código de barras, código, categoria, descrição, número, preço),
  usada exclusivamente para a pré-visualização em tela.
- Dependências: `Pillow` (`Image`, `ImageDraw`, `ImageFont`),
  `core/barcode.py`.
- Quem usa: `ui/main_window.py`, apenas nos métodos de preview
  (`_render_preview_image` e afins). **Não é usado por nenhum código de
  impressão.**

**`core/zpl_builder.py` (`ZplBuilder`)**
- Responsabilidade: montar o comando ZPL (texto puro `^XA...^XZ`) de uma
  etiqueta a partir do dicionário de produto, incluindo truncamento
  defensivo de campos que não caberiam no espaço calculado. Não desenha nada
  — apenas gera texto que a própria impressora interpreta.
- Dependências: nenhuma biblioteca externa (só `typing.Any`).
- Quem usa: `ui/main_window.py`, nos três pontos de impressão (teste, lote,
  rápida).

**`core/printer.py` (`PrinterService`)**
- Responsabilidade: toda a comunicação com o spooler de impressão do
  Windows — listar impressoras (`list_printers`), obter a impressora padrão
  (`get_default_printer`) e enviar dados brutos/ZPL (`print_raw`).
- Dependências: `win32print` (único submódulo de `pywin32` ainda necessário
  neste arquivo).
- Quem usa: `ui/main_window.py`.

**`ui/main_window.py` (`MainWindow`)**
- Responsabilidade: toda a interface Tkinter/ttk — tabela de produtos,
  pesquisa em tempo real, seleção múltipla, preview redimensionável,
  impressão de teste/rápida/lote, seleção de impressora.
- Dependências: `core.config`, `core.excel_reader`, `core.label_renderer`
  (preview), `core.printer` (impressão), `core.zpl_builder` (impressão).
- Quem usa: `app.py`.

**`tests/*`**
- `test_label_renderer.py` valida que `LabelRenderer.render_image()` sempre
  retorna uma imagem 240×120 — cobre exclusivamente o pipeline de preview.
- `test_excel_reader.py` valida leitura/validação de planilha, inclusive com
  os cabeçalhos reais do Santa Rubi.
- `test_batch_selection.py` / `test_batch_flow.py` validam a montagem da
  lista de produtos para impressão em lote (intervalo, todos, quantidade
  padrão) — não tocam em impressão nem em preview.
- **Não existe ainda** um teste automatizado para `ZplBuilder` (ver
  Capítulo 12, alta prioridade).

---

## 5. Fluxo de impressão

O fluxo de impressão, hoje, é inteiramente textual — não existe nenhuma
imagem envolvida entre o produto e a impressora.

1. **Geração do ZPL** — `ZplBuilder.build(product)` recebe o dicionário do
   produto (`codigo`, `categoria`, `descricao`, `numero`, `preco`) e monta
   uma string ZPL completa: cabeçalho (`^XA`, `^CI28` para UTF-8, `^PW240`,
   `^LL120`), o comando de código de barras (`^BCN`) e um comando `^FO` +
   `^FB` (field block, para justificar texto sem medir largura em Python) +
   `^A0` (fonte) + `^FD...^FS` por campo de texto. Antes de montar cada
   campo, `_truncate()` corta defensivamente o texto que não caberia no
   espaço calculado — necessário porque a impressora **não** faz elipse
   automática: um campo que excede a largura do `^FB` (com `lines=1`) fica
   sobreposto/ilegível em vez de simplesmente cortado.
2. **`print_raw()`** — `PrinterService.print_raw(data)` recebe essa string,
   codifica em UTF-8 e abre a impressora via `win32print.OpenPrinter()`. O
   job é declarado explicitamente como `pDatatype="RAW"` em
   `StartDocPrinter`, o que instrui o spooler do Windows a **não** processar
   os dados através do driver da impressora — eles são passados adiante
   como estão.
3. **Spooler RAW** — o Windows Print Spooler recebe o payload e o repassa
   integralmente para a porta da impressora (USB/rede), sem qualquer
   tradução, redimensionamento ou reamostragem.
4. **Comunicação com a impressora** — a ELGIN L42PRO FULL recebe o texto ZPL
   bruto pela porta de impressão e o interpreta com seu próprio firmware.
5. **Por que o driver GDI não participa mais** — o driver Windows da
   impressora (e o DEVMODE que ele exige) só entra em jogo quando se desenha
   uma imagem via GDI (`CreateDC`, `ImageWin.Dib`, etc.). Ao declarar o job
   como `RAW`, o spooler contorna completamente essa camada: não há
   `DocumentProperties`, não há `PaperSize`/`FormName` customizado, não há
   nenhuma reamostragem de imagem — e, portanto, não existe mais o teto de
   ~220/240px de área útil que o driver GDI impunha (Capítulo 2.4). O
   firmware da impressora desenha diretamente na resolução nativa de 203
   dpi, usando 100% dos 240×120 dots físicos da etiqueta.

### Impressão de múltiplas colunas (`build_row`)

O rolo físico de etiquetas usado é calibrado para 3 colunas por linha.
`ZplBuilder.build_row(products, column_pitch=264)` monta um único
`^XA...^XZ` cobrindo a largura das N colunas, deslocando os campos de cada
produto por `x_offset = index * column_pitch` — isso evita o bug de
replicação descrito no Capítulo 2.6 (enviar jobs `^XA` separados faz a
impressora repetir cada um em todas as colunas físicas da linha).

**Estado atual, importante:** os três pontos de impressão em
`ui/main_window.py` (teste, lote, rápida) usam hoje `ZplBuilder.build()`
— ou seja, **um job de coluna única por produto**, inclusive na impressão em
lote (`_run_batch_print`, um `print_raw()` por produto em sequência).
`build_row()` existe e foi validado fisicamente em scripts temporários
durante a calibração, mas **ainda não está conectado a nenhum fluxo da UI**.
Isso é documentado explicitamente como problema conhecido no Capítulo 11 —
imprimir um lote de produtos diferentes sequencialmente nesse rolo de 3
colunas pode reproduzir o mesmo bug de replicação por linha física do rolo,
e isso ainda não foi validado com hardware real neste formato de lote.

---

## 6. Fluxo da pré-visualização

A pré-visualização é um pipeline totalmente separado do fluxo de impressão,
e não depende dele em nenhum nível:

```
        UI
         │
         ▼
 LabelRenderer
         │
         ▼
     Bitmap
         │
         ▼
 Canvas Tkinter
```

`ui/main_window.py` chama `LabelRenderer.render_image(product)` (métodos
`_render_preview_image`, `_draw_label_preview`, `_draw_preview_placeholder`,
disparados também por `_on_preview_resize` ao redimensionar a janela).
`LabelRenderer` desenha uma imagem Pillow 240×120 usando `ImageDraw` e as
fontes TrueType em negrito disponíveis no sistema, colando a imagem do
código de barras gerada por `BarcodeGenerator`. Essa imagem é então
redimensionada preservando proporção e desenhada no `Canvas` via
`ImageTk.PhotoImage`.

Em nenhum ponto desse caminho há chamada a `PrinterService`, a
`ZplBuilder` ou a qualquer API do Windows Spooler. O preview pode, por
construção, ser usado, testado e evoluído (ex.: suporte a múltiplos
layouts) sem qualquer risco de afetar o que é efetivamente impresso.

---

## 7. Layout da etiqueta

O layout impresso (ZPL, `core/zpl_builder.py`) e o layout do preview
(bitmap, `core/label_renderer.py`) descrevem visualmente a mesma etiqueta,
mas são definidos de forma independente, em unidades diferentes.

### 7.1 Layout de impressão (`ZplBuilder`) — fonte da verdade física

Etiqueta de 30×15mm a 203 dpi = **240×120 dots** exatos (`LABEL_WIDTH_DOTS`,
`LABEL_HEIGHT_DOTS`).

| Elemento | Parâmetro | Valor |
|---|---|---|
| Margem esquerda | `LEFT_MARGIN` | 38 dots |
| Margem direita | `RIGHT_MARGIN` | 12 dots |
| Largura útil de conteúdo | `content_width` | `240 - 38 - 12 = 190` dots |
| Código de barras — topo | `BARCODE_TOP` | 6 dots |
| Código de barras — altura | `BARCODE_HEIGHT` | 30 dots |
| Código de barras — módulo | `BARCODE_MODULE_WIDTH` | 2 |
| Código do produto — linha Y | `CODE_ROW_Y` | 44 |
| Código do produto — fonte | `CODE_FONT_SIZE` | 20, negrito, centralizado |
| Categoria — linha Y | `CATEGORY_ROW_Y` | 66 |
| Categoria — fonte | `CATEGORY_FONT_SIZE` | 13, sem negrito, alinhada à direita |
| Descrição — linha Y | `DESCRIPTION_ROW_Y` | 81 |
| Descrição — fonte | `DESCRIPTION_FONT_SIZE` | 15, sem negrito, centralizada |
| Última linha (número + preço) | `LAST_ROW_Y` | 98 |
| Número — fonte / largura da coluna | `NUMBER_FONT_SIZE` / `NUMBER_COLUMN_WIDTH` | 13, sem negrito, alinhado à esquerda / 55 dots |
| Preço — fonte | `PRICE_FONT_SIZE` | 18, negrito, alinhado à direita |
| Colunas do rolo físico | — | 3 colunas |
| Espaçamento entre colunas (pitch) | `column_pitch` (parâmetro de `build_row`) | 264 dots (240 + 24 dots ≈ 3mm de gap medido fisicamente) |

**Fontes**: todos os campos usam a fonte ZPL escalável `"0"`
(`BOLD_FONT = REGULAR_FONT = "0"`). Não há diferenciação real de peso entre
"negrito" e "sem negrito" hoje — apenas de tamanho — porque a fonte
bitmap `"D"` (que permitiria negrito real) não escalou de forma confiável
neste firmware (ver Capítulo 2.6 e Capítulo 13). O destaque visual dos
campos "em negrito" (código, preço) vem do tamanho de fonte maior (20/18)
em relação aos campos regulares (13/15).

**Truncamento**: `_truncate()` calcula
`max_chars = field_width_dots / (font_size * ratio)`, com
`BOLD_CHAR_WIDTH_RATIO = REGULAR_CHAR_WIDTH_RATIO = 0.55` — valor
comprovadamente seguro depois de testar 0.6 (curto demais, cortava texto que
caberia) e 0.45 (sobrepôs texto, ficou ilegível). Textos que excedem
`max_chars` são cortados e recebem sufixo `"..."`. Esse truncamento é
necessário porque um campo ZPL `^FB` com `lines=1` não faz elipse
automática — apenas sobrepõe/quebra visualmente o texto que não cabe.

**Alinhamentos** (via parâmetro de justificação do `^FB`):
- Código do produto: `C` (centralizado), linha própria.
- Categoria: `R` (direita), linha própria abaixo do código.
- Descrição: `C` (centralizado), linha própria.
- Número: `L` (esquerda) e Preço: `R` (direita), dividindo a última linha.

### 7.2 Layout de preview (`LabelRenderer`) — aproximação visual em bitmap

Também 240×120px, mas com sua própria área segura (`SAFE_LEFT=45`,
`SAFE_RIGHT=218`) calibrada separadamente contra cortes observados no antigo
caminho GDI. Usa fontes TrueType em negrito (`DejaVuSans-Bold.ttf` e
variantes) para todos os campos — diferente do ZPL, que usa fonte "0" única
— e aplica um threshold duro preto/branco (sem anti-aliasing) para simular
visualmente o resultado da impressão térmica. Esses valores **não**
precisam (nem devem) ser mantidos numericamente idênticos aos do
`ZplBuilder`: o objetivo do preview é dar uma ideia fiel do resultado, não
ser pixel-a-dot idêntico ao ZPL.

### 7.3 Decisões de layout

- Código de barras colado no topo e com a maior altura possível: é o
  elemento mais crítico para a leitura por leitor óptico no PDV.
  - Código do produto: linha própria, centralizado, tamanho grande — segundo
  elemento mais lido (conferência manual).
- Categoria à direita e descrição centralizada: layout explicitamente
  pedido pelo usuário, replicando a etiqueta física de referência do
  negócio.
- Número (tamanho/variante) à esquerda e preço à direita na última linha:
  permite compará-los rapidamente lado a lado, e o preço em destaque
  (fonte 18) por ser a informação mais importante para o cliente final.

---

## 8. Decisões arquiteturais

**✓ Por que usamos RAW.** Enviar dados como `RAW` no spooler do Windows
contorna completamente o driver da impressora, que nesta ELGIN impunha um
teto de ~220 de 240 dots de largura útil (Capítulo 2.4). RAW elimina
DEVMODE, `DocumentProperties`, `PaperSize`/`FormName` customizado e qualquer
reamostragem de imagem pelo driver — dando acesso a 100% da área física da
etiqueta, confirmado fisicamente.

**✓ Por que usamos ZPL.** ZPL é a linguagem nativa do firmware desta
impressora térmica. Enviar comandos ZPL (em vez de uma imagem bitmap) faz o
próprio firmware desenhar texto e código de barras na resolução nativa
(203 dpi), sem nenhuma camada de tradução/reamostragem no meio — e sem
depender de fontes TrueType instaladas no Windows.

**✓ Por que o preview continua bitmap.** O preview precisa ser desenhado
dentro de um `Canvas` Tkinter, que só sabe exibir imagens — não há como
"pré-visualizar" um comando ZPL diretamente na tela sem um interpretador ZPL
embutido (o que seria uma dependência desproporcional só para preview).
Manter o preview como bitmap Pillow, reaproveitando o `LabelRenderer` já
existente, foi a solução mais simples e barata — desde que ele não precise
imprimir nada.

**✓ Por que impressão e preview são independentes.** Essa separação
significa que qualquer ajuste fino no layout impresso (calibração física de
margem, fonte, truncamento em dots ZPL) não pode, por construção, quebrar a
pré-visualização — e vice-versa. O custo é manter duas fontes de verdade
visuais (uma em dots ZPL, outra em pixels Pillow) para a mesma etiqueta, mas
esse custo foi considerado aceitável frente ao risco de acoplar impressão
física a uma camada (Tkinter/Pillow) que não tem nenhuma relação com o
protocolo de impressão.

**✓ Por que eliminamos completamente o GDI.** Depois de múltiplas rodadas de
calibração de margem sem superar o teto físico do driver, e com a evidência
concreta de que outro sistema usava 100% da etiqueta na mesma impressora
via um caminho diferente do GDI tradicional, ficou claro que **nenhuma
calibração de software resolveria uma limitação do driver**. A decisão foi
architetural, não cosmética: parar de lutar contra o driver e usar o
protocolo nativo da impressora.

---

## 9. Código removido

A remoção só foi feita **depois** que todos os pontos da UI já estavam
usando `ZplBuilder` + `print_raw()` — nunca antes, para evitar remover um
caminho de impressão que ainda estivesse em uso ativo. Antes de cada
remoção, foi feita uma busca (`grep`) em todo o repositório confirmando zero
referências restantes.

| Item removido | Local original | Motivo | Benefício |
|---|---|---|---|
| `print_image()` | `core/printer.py` | Caminho de impressão via GDI, substituído integralmente por `print_raw()` | Remove ~30 linhas de manipulação de DC/DEVMODE que não são mais chamadas |
| `_build_label_devmode()` | `core/printer.py` | Só existia para configurar o DEVMODE usado por `print_image()` | Elimina a fonte histórica do teto de margem de driver e de boa parte dos bugs de "Unable to open printer" |
| `LABEL_PAPER_WIDTH`, `LABEL_PAPER_LENGTH`, `LABEL_FORM_NAME` | `core/printer.py` | Só usadas por `_build_label_devmode()` | Remove configuração de papel que não tem efeito no caminho RAW |
| `_build_label_image()` | `ui/main_window.py` | Método sem nenhum chamador (já estava morto antes mesmo desta migração) | Remove código morto que confundiria um leitor futuro |
| Imports `win32con`, `win32gui`, `win32ui`, `PIL.Image`, `PIL.ImageWin` | `core/printer.py` | Usados exclusivamente por `print_image()`/`_build_label_devmode()` | `core/printer.py` passa a depender apenas de `win32print` — superfície de import mínima e coerente com sua única responsabilidade (falar RAW com o spooler) |
| 11 scripts `temp_*.py` e 11 PNGs de calibração | raiz do projeto | Artefatos temporários de diagnóstico/calibração física, nunca versionados | Repositório limpo, sem scripts de uso único misturados ao código de produção |

`core/printer.py` caiu de 156 para 73 linhas (**-53%**) nesta limpeza.
`LabelRenderer` e `BarcodeGenerator` foram deliberadamente **mantidos
intactos** — continuam sendo a única implementação do preview.

---

## 10. Testes executados

Após a remoção do código legado, a seguinte checklist de validação foi
executada e confirmada:

| Verificação | Resultado |
|---|---|
| ✓ Suíte automatizada (`python -m unittest discover -s tests`) | **7/7 passando** |
| ✓ Compilação de todos os módulos `.py` do projeto (`py_compile`) | Sem erros |
| ✓ Busca por referências quebradas (`print_image`, `_build_label_devmode`, constantes de papel, `_build_label_image`, `win32con`/`win32gui`/`win32ui`/`ImageWin`) | Zero ocorrências restantes em todo o repositório |
| ✓ Abertura da aplicação | `MainWindow` instanciada de ponta a ponta (Tk real) sem exceções |
| ✓ Pré-visualização | `LabelRenderer.render_image()` retorna bitmap 240×120 corretamente, sem tocar em `PrinterService` |
| ✓ Impressão de teste | `_on_test_print()` gera ZPL válido (`^XA...^XZ`) e chama `print_raw()` uma vez |
| ✓ Impressão em lote | `_run_batch_print()` chama `print_raw()` uma vez por produto, cada chamada com ZPL válido |

Os itens de impressão de teste/lote foram validados com `print_raw`
substituído por um stub que apenas registra a chamada (em vez de gravar na
porta real), para confirmar a fiação (wiring) do código sem gastar
etiquetas físicas a cada rodada de validação automatizada. **Isso confirma
que o ZPL é gerado e enviado corretamente pelo código** — não substitui um
teste físico de impressão na ELGIN real, que continua sendo a validação
final de qualquer ajuste de layout (Capítulo 7).

---

## 11. Problemas conhecidos

Apenas problemas reais, ainda não resolvidos, permanecem listados aqui.

- **Impressão em lote não agrupa por coluna do rolo físico.** Os três
  pontos de impressão da UI (incluindo `_run_batch_print`) usam
  `ZplBuilder.build()` — um job de coluna única por produto — e não
  `ZplBuilder.build_row()`. O rolo físico usado é calibrado para 3 colunas
  por linha, e o bug de replicação descrito no Capítulo 2.6 (job de coluna
  única sendo repetido nas 3 colunas físicas) foi observado justamente
  nesse cenário. Imprimir um lote de vários produtos diferentes em sequência
  ainda **não foi validado fisicamente** com o agrupamento de
  `build_row()`/`column_pitch` — existe risco de o mesmo bug de replicação
  se manifestar produto a produto no rolo físico de 3 colunas. Ver Capítulo
  12 (alta prioridade).
- **Sem diferenciação real de peso de fonte no ZPL.** Todos os campos usam a
  fonte "0" (escalável); "negrito" hoje é simulado apenas por tamanho maior
  de fonte (código/preço), não por um peso de fonte real. A fonte bitmap
  "D" foi tentada duas vezes para isso e revertida por instabilidade de
  escala (sobreposição de texto).
- **Sem cobertura de teste automatizado para `ZplBuilder`.** Toda a
  validação do layout ZPL até hoje foi feita fisicamente (fotos de
  etiquetas impressas), sem nenhum teste unitário que garanta, por exemplo,
  que `_truncate()` continue truncando corretamente após uma futura
  alteração de margem ou fonte.
- **Mensagem de erro "Unable to open printer"** ainda pode ocorrer
  dependendo de permissões/configuração local do Windows para acessar a
  impressora — isso é uma condição do sistema operacional/driver, não do
  código de impressão em si, e não tem uma correção definitiva do lado da
  aplicação além de reportar o erro claramente ao usuário (o que já é
  feito).

---

## 12. Roadmap

### Alta prioridade
- [ ] Conectar `ZplBuilder.build_row()` (com `column_pitch=264`) ao fluxo de
  impressão em lote, agrupando produtos em lotes de 3 por job, para evitar o
  bug de replicação por coluna física do rolo (Capítulo 11).
- [ ] Validar fisicamente a impressão em lote de produtos diferentes na
  ELGIN real, com o rolo de 3 colunas.
- [ ] Criar testes unitários para `ZplBuilder` (geração de campos,
  truncamento, `build_row` com múltiplos produtos e `x_offset` correto).

### Média prioridade
- [x] ~~Migrar toda a UI para o fluxo `ZplBuilder` + `print_raw()`~~ —
  concluído nesta migração.
- [x] ~~Remover código legado do caminho GDI~~ — concluído nesta migração.
- [ ] Suporte a múltiplos layouts de etiqueta (parametrizar `ZplBuilder` e
  `LabelRenderer` para aceitar um "modelo" de layout, em vez de constantes
  fixas de classe).
- [ ] Estruturar o painel direito da interface para histórico, favoritos e
  seleção de impressora persistente (via `ConfigManager`, já existente).
- [ ] Tratamento mais robusto e específico de erros de impressão (distinguir
  "impressora offline", "sem permissão", "sem papel", em vez de uma
  mensagem genérica de exceção).

### Baixa prioridade
- [ ] Popular os diretórios reservados `assets/`, `layouts/`, `data/`
  conforme a arquitetura definida em `CLAUDE.md`, à medida que
  funcionalidades que os utilizem forem implementadas.
- [ ] Avaliar necessidade real de peso de fonte diferenciado no ZPL
  (retomar fonte "D" ou equivalente somente se houver uma exigência forte de
  negrito real, dado o histórico de instabilidade).

---

## 13. Lições aprendidas

- **Não lute contra o driver do Windows.** Quando uma limitação se repete
  de forma consistente e independente de como o código é ajustado (aqui: o
  teto de ~220/240px, medido via `GetDeviceCaps`), é sinal de uma barreira
  arquitetural do driver, não um bug de calibração. Continuar ajustando
  margens em Python contra esse tipo de teto é tempo gasto sem chance real
  de sucesso. A confirmação de que outro sistema usava 100% da etiqueta na
  mesma impressora foi o dado decisivo para abandonar esse caminho.
- **Quando usar ZPL (ou a linguagem nativa do dispositivo).** Sempre que o
  hardware de destino tiver uma linguagem de comando nativa (ZPL, ESC/POS,
  etc.) e o driver genérico do sistema operacional impuser limitações que a
  linguagem nativa não tem, vale a pena considerar enviar comandos RAW
  diretamente — trocando a conveniência do driver genérico por controle
  total sobre a área física do dispositivo.
- **Separação de responsabilidades entre impressão e apresentação.** Manter
  o preview (bitmap/Tkinter) e a impressão (ZPL/RAW) como dois pipelines
  paralelos, sem dependência cruzada, evita que uma mudança em um afete o
  outro por acidente. O custo (duas fontes de verdade visuais) é pequeno
  frente ao risco evitado.
- **Arquitetura limpa como investimento, não burocracia.** Isolar a geração
  de ZPL num módulo sem nenhuma dependência de Pillow/Tkinter/GDI
  (`core/zpl_builder.py`) tornou possível testar e validar esse módulo
  isoladamente, e tornou trivial a migração da UI depois — bastou trocar a
  chamada em três lugares.
- **Importância de validar antes de remover código legado.** A primeira
  suposição, ao ser pedido para "remover o fluxo antigo", foi de que
  `LabelRenderer`/`print_image()` já estariam mortos — uma busca simples
  (`grep`) mostrou que a UI inteira ainda dependia deles para o preview.
  Presumir que um código parece "legado" sem confirmar todos os chamadores
  quase causou a remoção de um caminho ainda em uso ativo. A regra seguida
  desde então foi: **nunca remover sem antes buscar e confirmar zero
  referências restantes**, e só remover depois que a migração que o torna
  desnecessário estiver completa e validada.
- **Importância da documentação.** Um projeto que passou por uma mudança
  arquitetural completa (GDI → RAW/ZPL) só continua compreensível para um
  desenvolvedor novo se o *porquê* de cada decisão for registrado, não só o
  *o quê*. Este documento existe para que ninguém precise redescobrir, por
  tentativa e erro, que o driver GDI desta impressora tem um teto de
  ~220/240px — informação que custou várias rodadas de calibração física
  para ser descoberta da primeira vez.
- **Cada tentativa física custa uma etiqueta real.** Ao calibrar contra
  hardware físico (margens, tamanho de fonte, fonte "D"), cada rodada de
  ajuste custa uma etiqueta impressa e o tempo do usuário para fotografar o
  resultado. Isso mudou a forma de iterar: depois de duas tentativas
  falhas seguidas com a fonte "D", a decisão foi reverter para o último
  estado comprovadamente estável em vez de arriscar uma terceira tentativa
  às cegas — errar rápido tem limite quando o custo de cada iteração é
  físico, não computacional.

---

## 14. Estatísticas da migração

| Métrica | Valor |
|---|---|
| Linhas removidas em `core/printer.py` | 83 (156 → 73, **-53%**) |
| Linhas removidas em `ui/main_window.py` (código morto) | 10 |
| Arquivos de produção alterados nesta migração | `core/printer.py`, `ui/main_window.py` |
| Módulo novo criado | `core/zpl_builder.py` (175 linhas, zero dependências externas) |
| Scripts temporários removidos | 11 (`temp_*.py`) |
| Imagens de calibração removidas | 11 PNGs |
| Métodos removidos | `print_image()`, `_build_label_devmode()`, `_build_label_image()` |
| Constantes removidas | `LABEL_PAPER_WIDTH`, `LABEL_PAPER_LENGTH`, `LABEL_FORM_NAME` |
| Imports eliminados de `core/printer.py` | `win32con`, `win32gui`, `win32ui`, `PIL.Image`, `PIL.ImageWin` (restou apenas `win32print`) |
| Pontos de impressão migrados na UI | 3 (`_on_test_print`, `_run_batch_print`, `_on_print` modo rápido) |
| Testes automatizados | 7/7 passando (sem regressão) |
| Caminhos de impressão em produção | 1 (RAW/ZPL) — antes eram 2 (GDI + RAW coexistindo apenas em scripts temporários) |
| Redução de complexidade | `core/printer.py` passa a ter uma única responsabilidade (falar RAW com o spooler) e uma única dependência externa (`win32print`), em vez de misturar dois protocolos de impressão (GDI + RAW) e cinco dependências Windows/Pillow |

**Ganho de arquitetura**: o módulo de impressão deixou de ser o ponto onde
dois protocolos incompatíveis coexistiam (um funcional e usado pela UI, um
validado mas preso a scripts temporários) para ser um módulo único, coeso e
com responsabilidade única — refletindo hoje exatamente o que está em
produção, sem código morto ou caminhos alternativos não utilizados.

---

## 15. Marco da versão

Este checkpoint marca a **primeira versão consolidada da arquitetura de
impressão** do Santa Rubi Label Studio: impressão 100% via RAW + ZPL,
preview 100% independente via bitmap, código legado do caminho GDI
completamente removido, e suíte de testes automatizados passando sem
regressão.

Recomenda-se marcar o commit desta migração com a tag:

```
v1.0-print-engine
```

Esta tag é sugerida porque este momento representa a estabilização de um
componente central do sistema — o motor de impressão — depois de uma
mudança arquitetural completa, motivada por uma limitação real de hardware/
driver descoberta e confirmada em campo (Capítulo 2.4), e validada
fisicamente em impressora real ao longo de múltiplas rodadas de calibração.
A partir deste ponto, qualquer evolução futura da impressão (múltiplos
layouts, impressão em lote agrupada por coluna, novos modelos de
impressora) parte de uma base limpa, testada e documentada — não mais de um
protocolo de impressão que lutava contra os limites do driver Windows.

*(A criação da tag em si não foi executada por este documento — é uma
recomendação para o desenvolvedor/mantenedor confirmar e aplicar após
revisar e commitar as mudanças.)*

---

## 16. Marco v1.1-smart-print

**Commit da funcionalidade:** `530a2a89876e9bd458e67aa51bb7214b31652d8b`
**Tag:** `v1.1-smart-print`

### Objetivo da evolução

Sobre a base estável de [v1.0-print-engine](#15-marco-da-versão), esta fase
resolveu a limitação conhecida documentada no Capítulo 11 da versão
anterior: a impressão em lote enviava um job ZPL de coluna única por
produto, o que, no rolo físico calibrado para 3 colunas, arriscava
reproduzir o bug de replicação (Capítulo 2.6) e ignorava a quantidade (`qtd`)
de cada produto. O objetivo foi tornar a impressão "inteligente" o
suficiente para agrupar corretamente qualquer volume de etiquetas nas
colunas físicas do rolo, sem exigir nenhuma alteração no pipeline RAW+ZPL
já consolidado.

### Funcionalidades implementadas

- **Memória da última impressora utilizada**: `_load_printer_list()` passa a
  restaurar `last_printer` de `config.json` (via `ConfigManager`, já
  existente) e a salvar a escolha automaticamente ao trocar de impressora
  (`_on_printer_selected`, ligado a `<<ComboboxSelected>>`). Se a impressora
  salva não existir mais, cai para a padrão do Windows e atualiza a
  configuração.
- **Respeito à quantidade do produto**: os pontos de impressão passam a
  usar a quantidade (`qtd`) de cada produto para determinar quantas
  etiquetas realmente sair da impressora, em vez de sempre uma por produto.
- **Impressão em lote agrupada por linha de 3 colunas** (`_run_batch_print`):
  a lista de produtos é expandida por quantidade e agrupada em blocos de
  até 3 "etiquetas físicas", cada bloco enviado como **um único** job
  `ZplBuilder.build_row()` — em vez de um job por produto.
- **`build_row()` refinado para aceitar 1, 2 ou 3 produtos sem preenchimento
  fictício**: novo parâmetro opcional `total_width` desacopla a largura
  física do job (sempre a largura calibrada do rolo) da quantidade de
  produtos realmente fornecidos. Colunas sem produto correspondente não
  recebem nenhum campo ZPL — nem mesmo o resíduo `"R$"` que a abordagem
  anterior (preencher com `{}`) produzia.
- **Cobertura de teste para `ZplBuilder`**: `tests/test_zpl_builder.py`
  (novo) cobre `build_row()` com 1, 2 e 3 produtos, confirmando ausência de
  campos/residuais em colunas vazias — fechando a lacuna de testes
  registrada no roadmap da versão anterior.

### Validação física realizada

Testado fisicamente na ELGIN L42PRO FULL, com resultado confirmado pelo
usuário para todos os cenários:

| Cenário | Resultado |
|---|---|
| Impressão em 1 coluna | OK |
| Impressão em 2 colunas | OK |
| Impressão em 3 colunas | OK |
| Agrupamento automático (quantidades que cruzam múltiplas linhas de 3) | OK |
| Quantidades (`qtd` respeitada por etiqueta) | OK |
| Alinhamento | OK |
| Código de barras | OK |
| Layout geral | OK |
| Regressões | Nenhuma observada |

### Preservação da arquitetura

Nenhuma mudança tocou o pipeline RAW+ZPL em si (`PrinterService.print_raw`
permanece idêntico), nem o mecanismo de preview (`LabelRenderer`
inalterado, preview continua independente). A única mudança em
`core/zpl_builder.py` foi a adição do parâmetro opcional `total_width` em
`build_row()` — retrocompatível, sem alterar `build()` nem o formato ZPL
gerado para etiquetas já existentes. Toda a lógica de agrupamento por linha
vive em `ui/main_window.py`, mantendo `ZplBuilder` e `PrinterService` como
módulos de responsabilidade única, sem duplicação de lógica.

### Conclusão

Com a validação física confirmando todos os cenários de coluna, quantidade
e agrupamento sem regressão, **o módulo de impressão do Santa Rubi Label
Studio passa a ser considerado estável e concluído** nesta versão. Futuras
mudanças no módulo de impressão devem ser tratadas como evolução incremental
sobre `v1.1-smart-print`, seguindo o mesmo princípio que preservou
`v1.0-print-engine`: preservar a arquitetura consolidada, evitar
refatorações, e validar fisicamente somente quando uma funcionalidade
estiver completa.

---

# Checkpoint v1.2-layout-final

**Tag:** `v1.2-layout-final`
**Status:** layout da etiqueta validado fisicamente na ELGIN L42PRO FULL e **oficialmente aprovado e congelado**.

Este checkpoint registra o fechamento do ciclo de ajustes finos sobre a base
`v1.1-smart-print`: refinamentos de codificação do código de barras,
alinhamento visual e aproveitamento da largura útil da etiqueta para a
descrição do produto — todos validados fisicamente, em rodadas incrementais
de um único parâmetro por vez.

## Impressão

- Impressão RAW via ZPL, sem qualquer participação do driver GDI do Windows.
- Remoção completa do caminho GDI (`print_image`, `_build_label_devmode`,
  constantes de papel, imports `win32con`/`win32gui`/`win32ui`/`ImageWin`) —
  consolidada desde `v1.0-print-engine`.
- Impressão inteligente em até 3 colunas: lote agrupado em linhas via
  `ZplBuilder.build_row()`, sem preenchimento fictício de colunas vazias —
  consolidada em `v1.1-smart-print`.
- Impressão por quantidade: cada produto imprime exatamente `qtd` etiquetas
  (via expansão da lista antes do agrupamento em linhas), incluindo o caso
  `qtd=0` (zero etiquetas, sem clamping para 1).
- Compatibilidade validada fisicamente com a impressora **ELGIN L42PRO FULL**
  em todos os cenários: 1, 2 e 3 colunas, agrupamento automático e
  quantidades variadas.

## Código de barras

- Code128 com **Start Code C explícito** (`>;` no campo `^FD`), garantindo
  compactação em Subset C (2 dígitos por símbolo) para os códigos numéricos
  de 6 dígitos da Santa Rubi — corrigindo um Subset B implícito que estava
  em uso desde a migração original (ZPL usa Subset B por padrão quando
  nenhum start code é informado, conforme o Zebra ZPL II Programming Guide).
- **Centralização matemática**: a largura real do símbolo Code128 é
  calculada a partir da contagem exata de módulos da estrutura Code128
  (start + dados em pares + checksum + stop) multiplicada pela largura do
  módulo (`^BY`), e usada para centralizar o código de barras dentro da
  coluna — sem medir/estimar visualmente.
- **Ajuste óptico de +6 dots** (`BARCODE_VISUAL_OFFSET_X`): desloca o bloco
  código de barras + código impresso abaixo dele horizontalmente, mantendo
  o alinhamento relativo entre os dois, para melhorar o centro visual
  percebido.
- Leitura e alinhamento validados fisicamente na impressora real.

## Interface

- Memória da última impressora utilizada (`last_printer` em `config.json`,
  via `ConfigManager` já existente), restaurada automaticamente na
  abertura e salva a cada troca de impressora.
- Memória da última planilha utilizada (`last_spreadsheet`), consolidada
  como chave única (a antiga `last_excel_path` foi removida — zero
  referências restantes no projeto).
- Carregamento automático da última planilha na abertura do programa:
  valida se o arquivo ainda existe, carrega produtos e atualiza tabela e
  pré-visualização sem nenhuma ação do usuário; se o arquivo não existir
  mais, limpa a chave do `config.json` e avisa o usuário, sem travar a
  abertura.
- Corrigido, como efeito colateral necessário dessa funcionalidade, um bug
  pré-existente em `_load_products_into_table()` (`selection_set()` recebia
  um `set()` do Python em vez de lista, travando com `TclError` sempre que
  a seleção estava vazia — inclusive na seleção manual de planilha).

## Layout da etiqueta

- Layout validado fisicamente em múltiplas rodadas, uma variável por vez.
- Código de barras: **aprovado**.
- Código do produto: **aprovado**.
- Categoria: **aprovada**.
- Número: **aprovado**.
- Preço: **aprovado**.
- Descrição do produto: usando largura ampliada e dedicada de **198 dots**
  (`DESCRIPTION_RIGHT_MARGIN = 4`, contra os 12 dots de margem direita
  compartilhados por código/categoria — a descrição não divide linha com
  nenhum outro campo, então pôde ganhar uma margem direita própria e menor,
  sem risco de invadir os demais elementos; a margem esquerda, 38 dots,
  é zona morta de hardware confirmada fisicamente e não foi reduzida).
- `DESCRIPTION_MAX_CHARS = 26`: corte simples por quantidade de caracteres
  (`descricao[:DESCRIPTION_MAX_CHARS]`), **sem qualquer heurística de
  largura, cálculo em dots ou classificação de caracteres** — a impressora
  decide o resultado real; o valor foi calibrado fisicamente subindo de 25
  para 26 depois que a largura do campo foi ampliada.
- Corte da descrição **sem reticências**: nenhum indicador é adicionado; o
  texto que excede `DESCRIPTION_MAX_CHARS` é simplesmente interrompido.
- Sem sobreposição de texto em nenhum campo.
- Aproveitamento máximo da área útil disponível na etiqueta, respeitando as
  zonas mortas de hardware já confirmadas.

**Produto utilizado na validação física:**
```
BRINCO PINO FLOR CRAVEJADA
```
**Resultado:** descrição impressa integralmente (26 caracteres), sem corte,
sem sobreposição — layout aprovado.

## Layout Congelado

Este layout foi aprovado após diversos testes físicos e passa a ser a
**versão oficial do projeto**.

Alterações futuras no layout somente deverão ocorrer em caso de:

- correção de bugs comprovados;
- mudança de hardware;
- novo requisito de negócio.

Pequenos ajustes estéticos não deverão mais ser realizados.

---

# Checkpoint v1.3-produtividade

**Tag:** `v1.3-produtividade`

## Objetivo

Encerrar o ciclo de melhorias de produtividade da interface, mantendo
totalmente preservado o motor de impressão validado no `v1.2-layout-final`.

## Funcionalidades implementadas

### Pesquisa instantânea

- Pesquisa por código.
- Pesquisa por descrição.
- Pesquisa por categoria.
- Pesquisa por número.
- Busca case insensitive.
- Busca ignorando acentos.
- Pesquisa em tempo real (dispara a cada tecla, via `trace_add` na
  `StringVar` de pesquisa).
- Otimização utilizando `_search_blob` pré-processado: cada produto tem seu
  texto pesquisável (código + categoria + descrição + número) normalizado
  uma única vez na carga da planilha, não a cada tecla digitada — validado
  com 5.001 produtos filtrando em ~3,8 ms por tecla.

### Filtro por categoria

- Categorias carregadas automaticamente da planilha (nunca uma lista fixa).
- Categorias únicas (sem repetição).
- Ordenação alfabética.
- Opção "Todos" sempre como primeira opção e padrão ao carregar planilha nova.
- Funcionamento combinado com a pesquisa: categoria e texto pesquisado se
  aplicam simultaneamente sobre a mesma lista (`_apply_filters`).

### Contadores

- **Total** de produtos carregados.
- **Exibindo** — produtos visíveis após os filtros.
- **Selecionados** — produtos marcados na tabela.

Atualização automática em toda alteração de filtro (categoria ou pesquisa) e
de seleção (clique, duplo clique, Ctrl+A, arraste), sem nenhuma ação manual
adicional do usuário.

### Impressão de selecionados

- Botão dedicado "Imprimir Selecionados".
- Reutilização integral do pipeline de impressão já existente — nenhuma
  lógica de impressão nova ou duplicada.
- Mesma expansão por quantidade (`qtd` respeitada por etiqueta).
- Mesmo agrupamento em linhas de 3 colunas.
- Mesmo `build_row()`.
- Mesmo `PrinterService`.

### Produtividade

Atalhos de teclado implementados:

- **Ctrl+F** — foco imediato no campo de pesquisa, com o texto existente
  selecionado.
- **ESC** — limpa a pesquisa, mantendo a categoria selecionada.
- **Ctrl+A** (tabela em foco) — seleciona todos os produtos exibidos após
  os filtros (nunca os ocultos).
- **Enter** (campo de pesquisa) — aciona "Imprimir Selecionados" quando há
  seleção; mantém o aviso existente quando não há.
- **Duplo clique** — alterna a seleção da linha.
- **Seleção contínua por arraste** — ver detalhamento abaixo.

### Seleção contínua por arraste

- Utiliza a seleção **nativa** do Treeview (`selection_set`) — não cria
  nenhuma estrutura de seleção paralela.
- O contador de selecionados atualiza automaticamente durante o arraste,
  porque tudo passa pelo mesmo caminho já existente (`<<TreeviewSelect>>` →
  `_on_table_select` → `_refresh_counts`).
- Compatível com todos os recursos existentes: Ctrl+Clique, Ctrl+A, duplo
  clique, clique simples na coluna de seleção e impressão de selecionados —
  todos validados funcionando em conjunto após a implementação.
- Nenhuma regressão encontrada; um bug de condição de corrida entre o clique
  simples e a seleção nativa do Treeview foi identificado e corrigido
  durante a própria validação desta funcionalidade, antes de ser
  considerada concluída.

## Arquitetura

Toda a versão v1.3 foi implementada **exclusivamente na camada de
interface** (`ui/main_window.py`), preservando completamente o núcleo do
sistema.

Nenhum dos componentes abaixo foi alterado durante todo o ciclo v1.3:

- `ZplBuilder`
- `PrinterService`
- `LabelRenderer`
- `build()`
- `build_row()`

## Resultado

O software passa a oferecer uma operação significativamente mais rápida e
confortável no dia a dia — busca instantânea, filtro por categoria,
contadores sempre visíveis, impressão seletiva e atalhos de teclado —
mantendo **exatamente o mesmo comportamento de impressão** validado
fisicamente no checkpoint `v1.2-layout-final`.

---

# Interface Congelada

A interface atual foi considerada **madura para uso diário**.

Novas versões deverão priorizar:

- confiabilidade;
- manutenção;
- funcionalidades administrativas;
- arquitetura;
- distribuição do sistema.

Pequenos ajustes de usabilidade somente deverão ocorrer mediante
necessidade comprovada.
