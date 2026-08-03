# Project Context

Versão: 2.0 (revisado por auditoria de código)

Última atualização: Julho/2026

Este documento apresenta o contexto de negócio do Santa Rubi Label Studio.

Ele deve ser lido antes de qualquer implementação para que a IA compreenda
o ambiente onde o sistema é utilizado.

> Nota metodológica: as seções sobre a empresa e o fluxo de negócio abaixo
> descrevem contexto organizacional — não são verificáveis diretamente pelo
> código-fonte (o código não guarda informação sobre a estrutura comercial
> da Santa Rubi). Já as afirmações técnicas (PrintQueue única, papel de
> cada aba, o que o sistema faz e não faz) foram conferidas contra o código
> real durante a auditoria registrada em `ARCHITECTURE_AUDIT.md`.

---

# Sobre a Santa Rubi

A Santa Rubi é uma empresa especializada em semijoias.

Seu principal modelo de negócio é a venda através de revendedoras, chamadas
internamente de Executivas.

O Label Studio é uma ferramenta interna utilizada exclusivamente pela
Santa Rubi.

---

# Objetivo do Label Studio

O Label Studio existe para agilizar e padronizar a impressão de etiquetas.

Ele não é um ERP.

Ele não substitui o sistema Jueri.

Ele não realiza controle financeiro.

Ele não controla estoque.

Ele é especializado exclusivamente na preparação e impressão de etiquetas.

Tecnicamente, isso se reflete em duas telas (confirmado em
`ui/main_window.py`/`ui/catalog_tab.py`): uma para pesquisar produtos na
API Jueri, outra para gerenciar o catálogo vindo da Planilha Excel — ambas
alimentando a mesma fila de impressão.

---

# Fluxo Operacional

O fluxo principal da empresa é:

Fornecedor

↓

Planilha Excel

↓

Precificação

↓

Impressão de etiquetas

↓

Cadastro dos produtos no ERP Jueri

Após o cadastro no ERP, os produtos passam a ser consultados pela API
Jueri quando necessário.

---

# Papel da Planilha Excel

A Planilha Excel é a principal ferramenta operacional.

Ela contém:

- produtos recebidos;
- custos;
- precificação;
- informações utilizadas antes do cadastro no ERP.

O fluxo principal sempre começa pela Planilha Excel.

No sistema, isso corresponde à aba **"Planilha Excel"**
(`ui/catalog_tab.py`, classe `CatalogTab`): o usuário aponta o arquivo
`.xlsx`, seleciona as abas que quer usar e mapeia cada coluna (Código,
Descrição, Preço, Categoria, Numeração, Quantidade) para o cabeçalho real
da planilha. O catálogo inteiro é carregado em memória
(`CatalogRepository`) e permanece disponível para pesquisa/filtro/
ordenação instantâneos até o usuário clicar em "Recarregar Catálogo".

---

# Papel da API Jueri

A API Jueri possui função complementar.

Ela é utilizada principalmente para:

- reimpressão de etiquetas;
- promoções;
- remarcações;
- substituição de etiquetas perdidas;
- consultas de produtos já cadastrados.

Ela nunca substitui a Planilha Excel como fluxo principal.

No sistema, isso corresponde à aba **"API Jueri"**: o usuário pesquisa por
texto, lista de códigos, ou intervalo de datas de cadastro (com atalhos
"Hoje"/"Ontem"), seleciona os produtos encontrados e os envia para a mesma
fila de impressão da Planilha Excel — sem nunca imprimir diretamente dali.
Pesquisas podem ser salvas como favoritas (persistidas) ou reaproveitadas
do histórico recente (só durante a sessão).

---

# Impressão

Toda impressão deve ocorrer através da PrintQueue.

Não existem múltiplas filas de impressão.

Não existem fluxos alternativos.

Toda origem de produtos converge para uma única fila.

Confirmado em código: `core/print_queue.py` define `PrintQueue` como
coleção única; uma única instância existe em todo o programa
(`CatalogTab.__init__`), e é essa mesma instância que a aba "API Jueri" usa
para adicionar produtos (`CatalogTab.add_product_to_queue`). A impressão
de fato só acontece a partir da aba "Planilha Excel" (botão "Imprimir
Fila", atalho Ctrl+P), nunca da aba "API Jueri".

---

# Filosofia do Sistema

O sistema deve priorizar:

- simplicidade;
- velocidade;
- estabilidade;
- reutilização de componentes;
- experiência do operador.

Toda melhoria deve reduzir cliques e aumentar produtividade.

---

# Filosofia de Interface

A interface deve transmitir a identidade da Santa Rubi.

Ela deve ser:

- elegante;
- limpa;
- organizada;
- minimalista;
- profissional.

A interface nunca deve parecer um ERP antigo.

A experiência do usuário é considerada parte essencial da qualidade do
sistema.

> Nota técnica: a paleta de cores e a tipografia efetivamente
> implementadas hoje estão descritas em `03_DESIGN_SYSTEM.md`, revisado
> nesta mesma auditoria para refletir o que o código realmente configura
> (`ui/main_window.py`, método `_setup_style`) — não uma paleta de marca
> ainda não implementada.

---

# Evolução do Projeto

O projeto evolui por pequenas sprints.

Cada sprint possui objetivo único.

Alterações grandes devem ser divididas em etapas menores.

Toda alteração deve preservar a arquitetura existente e manter a suíte de
testes passando (541 testes em `tests/`, executados via
`python -m unittest discover -s tests -p "test_*.py"`, no momento desta
auditoria).
