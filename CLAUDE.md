# Santa Rubi Label Studio

## Objetivo

Sistema desktop para Windows destinado à impressão de etiquetas para a Santa Rubi.

## Tecnologias obrigatórias

- Python 3.12
- Tkinter (ttk)
- openpyxl
- Pillow
- python-barcode
- reportlab
- pywin32

## Arquitetura

Sempre manter o projeto modular.

Nunca colocar toda a lógica em um único arquivo.

Organização:

core/
ui/
layouts/
assets/
data/
tests/

## Regras

Antes de criar novos módulos, explique o motivo.

Não alterar arquitetura sem aprovação.

Utilizar type hints.

Utilizar ttk.

Evitar comentários desnecessários.

Criar funções pequenas.

Nunca utilizar caminhos absolutos.

Nunca adicionar dependências sem aprovação.

Sempre consultar o arquivo SPEC.md antes de implementar funcionalidades.

## Desenvolvimento

Implementar apenas uma funcionalidade por vez.

Ao finalizar cada etapa, aguardar aprovação antes de continuar.

## Atualização de sessão

Nesta sessão foram aplicados ajustes importantes na interface e na impressão:

- Reorganização completa da interface com `grid` para um layout mais profissional.
- Tabela de produtos priorizada como elemento principal.
- Pesquisa em tempo real para filtrar produtos.
- Seleção múltipla de produtos com botões de selecionar, desmarcar e inverter seleção.
- Pré-visualização imediata da etiqueta, centralizada e redimensionável.
- Botões `Visualizar`, `Imprimir` e `Teste de Impressão` padronizados.
- Integração com `pywin32` para impressão Windows.
- Correção da criação de Device Context em `core/printer.py` usando `CreateDC()` + `CreatePrinterDC()`.
- Execução de testes unitários e compilação sem erros.

### Estado atual da impressão

A impressão foi corrigida e a lista de impressoras funciona. O sistema ainda pode apresentar erro de impressão do Windows com a mensagem "Unable to open printer" em alguns ambientes, o que indica problema de acesso à impressora ou permissões no Windows.

### Próximo passo

Continuar o desenvolvimento focando em:

- Refinamento da pré-visualização e suporte a múltiplos layouts de etiqueta.
- Estruturação do painel direito para futuras opções de histórico, favoritos e seleção de impressora.
- Implementação de tratamento mais robusto de erros de impressão e mensagens ao usuário.
