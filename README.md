# Santa Rubi Label Studio

Sistema desktop para leitura de planilhas Excel e impressão de etiquetas na
impressora Elgin L42 PRO.

## Status do projeto

Em desenvolvimento inicial. A interface gráfica já está disponível e agora a
aplicação passa a suportar a leitura de planilhas Excel para consulta de
produtos.

## Tecnologias

- Python 3.12
- Tkinter
- openpyxl
- Pillow
- python-barcode
- reportlab
- pywin32

## Estrutura do projeto

```
SantaRubi-LabelStudio/
│
├── app.py              # Ponto de entrada da aplicação
├── requirements.txt     # Dependências do projeto
├── README.md              # Este arquivo
├── .gitignore              # Arquivos/pastas ignorados pelo Git
│
├── assets/                 # Ícones, imagens e recursos visuais da interface
├── core/                   # Lógica de negócio (leitura de Excel, geração de etiquetas, impressão)
├── ui/                      # Telas e componentes Tkinter
├── layouts/                # Templates/definições de layout de etiquetas
├── data/                    # Arquivos de dados de entrada/saída
└── tests/                   # Testes automatizados
```

## Funcionalidade atual

- Seleção de arquivos .xlsx pela interface.
- Leitura da primeira aba da planilha.
- Localização automática das colunas pelos nomes:
  - CODIGO
  - CATEGORIA
  - DESCRICAO
  - PRECO
  - NUMERO
- Validação de arquivo, existência da planilha e colunas obrigatórias.
- Exibição de mensagem de sucesso ou erro após o carregamento.
- Função preparada para buscar um produto por código via `buscar_produto(codigo)`.

## Como executar

1. Crie e ative um ambiente virtual:

   ```
   python -m venv venv
   venv\Scripts\activate
   ```

2. Instale as dependências:

   ```
   pip install -r requirements.txt
   ```

3. Execute a aplicação:

   ```
   python app.py
   ```

