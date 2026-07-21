"""Constantes físicas do layout da etiqueta e do rolo — único módulo
responsável por esses valores. ZplBuilder e as telas que montam trabalhos
de impressão em lote (aba "Impressão" e Catálogo Integrado) importam tudo
daqui; nenhum valor físico deve ser redeclarado em outro módulo.

Estes números vêm de calibração física validada em impressões reais na
ELGIN L42PRO FULL (etiqueta de 30x15mm, 203dpi) — não são estimativas.
"""

from __future__ import annotations

# --- Etiqueta (resolução nativa 203dpi = 240x120 dots para 30x15mm) ---
LABEL_WIDTH_DOTS = 240
LABEL_HEIGHT_DOTS = 120

# Estimativa de largura média de caractere, como fração do parâmetro de
# largura pedido — usada só para truncar com segurança em Python, já que a
# impressora não faz "..." sozinha, e um campo que não cabe no ^FB (lines=1)
# fica sobreposto/ilegível em vez de simplesmente cortar.
# 0,6 ficou curto demais; 0,45 sobrepôs; 0,55 é o meio-termo comprovadamente
# seguro (validado em várias impressões).
BOLD_CHAR_WIDTH_RATIO = 0.55
REGULAR_CHAR_WIDTH_RATIO = 0.55

# Tentativa de usar a fonte D para tirar o negrito de categoria/descrição/
# número sobrepôs texto DUAS vezes seguidas, mesmo depois de reduzir bastante
# o tamanho pedido — a fonte D não escala de forma confiável nessa
# impressora. Revertido para a fonte 0 em tudo (estado validado antes desse
# pedido) em vez de arriscar mais uma etiqueta em outra tentativa às cegas.
BOLD_FONT = "0"
REGULAR_FONT = "0"

# --- Margens e posicionamento dos campos ---
LEFT_MARGIN = 38
RIGHT_MARGIN = 12

BARCODE_TOP = 6
BARCODE_HEIGHT = 30
BARCODE_MODULE_WIDTH = 2

# Ajuste fino de alinhamento visual: desloca só o bloco código de barras +
# código impresso abaixo dele, mantendo o alinhamento relativo entre os
# dois. Não afeta os demais campos nem a largura calculada do símbolo.
BARCODE_VISUAL_OFFSET_X = 6

# Estrutura fixa de um símbolo Code128: cada caractere (start, dados,
# checksum) ocupa 11 módulos; o stop ocupa 13 (11 + barra de terminação
# de 2 módulos) — Zebra ZPL II Programming Guide, comando ^BC.
CODE128_SYMBOL_MODULES = 11
CODE128_STOP_MODULES = 13

# Código: centralizado em linha própria, logo abaixo do barcode.
CODE_ROW_Y = 44
CODE_FONT_SIZE = 20

# Categoria: linha própria, abaixo do código, alinhada à direita.
CATEGORY_ROW_Y = 66
CATEGORY_FONT_SIZE = 13

DESCRIPTION_ROW_Y = 81
DESCRIPTION_FONT_SIZE = 15
# Corte por quantidade de caracteres, sem cálculo de largura: a impressora
# decide a quebra/ajuste real. Ajustar este valor conforme teste físico.
DESCRIPTION_MAX_CHARS = 26
# Margem direita própria da descrição, menor que RIGHT_MARGIN (12):
# LEFT_MARGIN (38) é zona morta de hardware confirmada fisicamente e não
# é reduzida aqui; a direita nunca teve essa confirmação, e a descrição
# não compartilha linha com nenhum outro campo, então aproveita mais
# espaço sem risco de invadir código/categoria/número/preço.
DESCRIPTION_RIGHT_MARGIN = 4

LAST_ROW_Y = 98
NUMBER_FONT_SIZE = 13
NUMBER_COLUMN_WIDTH = 55
PRICE_FONT_SIZE = 18

# --- Rolo de etiquetas: impressão em lote (aba "Impressão" e Catálogo
# Integrado) ---
# O rolo de etiquetas é calibrado fisicamente para 3 colunas por linha.
# Enviar um job ^XA mais estreito que essa largura faz a impressora repetir
# o conteúdo nas colunas restantes (ver DOCUMENTACAO_CHECKPOINT.md, cap. 2.6).
BATCH_ROW_COLUMNS = 3
BATCH_COLUMN_PITCH = 264
