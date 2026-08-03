# Changelog

Versão: 2.0 (revisado por auditoria de código)

Última atualização: Julho/2026

Este documento registra a evolução do Santa Rubi Label Studio.

Seu objetivo é documentar decisões importantes, mudanças arquiteturais e
funcionalidades concluídas.

Não registrar pequenas correções de código.

Registrar apenas mudanças relevantes para o projeto.

> Nota desta revisão: o conteúdo abaixo foi conferido contra o estado real
> do código (branch `feature/v3.1`), não copiado do changelog legado da
> raiz do projeto (`CHANGELOG.md`), que descreve uma versão anterior do
> produto (tags `v1.0-print-engine` até `v3.0-stable`, sem integração
> Jueri). Esse changelog legado continua existindo como histórico daquele
> ciclo — ver `ARCHITECTURE_AUDIT.md` para a nota de divergência completa.

---

# v1.0.0

## Arquitetura

- Arquitetura consolidada em torno de uma única `PrintQueue`
  (`core/print_queue.py`), instanciada uma vez em `CatalogTab` e
  compartilhada com a aba "API Jueri".
- `CatalogProduct` (`core/catalog_product.py`) estabelecido como modelo
  interno comum a Excel e API Jueri.
- Separação definitiva entre origem dos dados (Excel via
  `ExcelCatalogSource`, Jueri via `ProductsAPI`) e impressão (`ZplBuilder`
  + `PrinterService`).
- Reorganização das abas: a antiga aba "Impressão" (Excel avulso, sem
  fila) foi removida; as duas abas atuais são **"API Jueri"** e
  **"Planilha Excel"**.

## Integração Jueri

- Cliente HTTP próprio (`app/api/client.py`, `JueriClient`), sem
  dependências novas (usa `urllib` da biblioteca padrão).
- Busca de produtos por texto, lista de códigos ou intervalo de datas de
  cadastro (`app/api/products.py`, `ProductsAPI`).
- Resolução de nome de categoria via `CategoriesAPI` (cache em memória).
- Conversão automática `Product` → `CatalogProduct`
  (`Product.to_catalog_product`).
- Janela dedicada de pesquisa (`ui/product_search_dialog.py`,
  `ProductSearchDialog`), com seleção múltipla/arraste, ordenação, e
  atalhos ESC (fechar) / ENTER (pesquisar).
- Configuração da integração (habilitar, cliente_sistema, token, testar
  conexão) em `ui/settings_dialog.py`.

## Planilha Excel

- Fluxo principal de impressão mantido pela Planilha Excel
  (`ui/catalog_tab.py`, `CatalogTab`): configuração de arquivo/abas/
  colunas, catálogo em cache de memória, pesquisa/filtro/ordenação
  instantâneos.
- Fila de Impressão visual (cartões), com adicionar/remover/limpar,
  ajuste de quantidade por `[-]`/`[+]` ou edição direta, atalhos DEL/
  Ctrl+A.

## Interface

- Separação clara entre a tela da API Jueri e a tela da Planilha Excel,
  cada uma em sua própria aba do `ttk.Notebook`.
- Impressão centralizada exclusivamente pela `PrintQueue` — a aba "API
  Jueri" nunca imprime diretamente, só alimenta a fila.
- Cabeçalho fixo (título + "Configurações"), visível em qualquer aba.
- Resumo da Fila de Impressão (produtos, etiquetas, última atualização)
  visível diretamente na aba "API Jueri", sem precisar trocar de aba.

## Experiência do Usuário

- Favoritos de pesquisa (persistidos em `config.json`, chave
  `jueri_favorites`).
- Pesquisas recentes (histórico em memória, reexecutáveis com um clique).
- Seleção múltipla e seleção contínua por arraste em todas as tabelas.
- Persistência de configurações: aba ativa, geometria da janela, largura
  de colunas e ordenação das tabelas, além de credenciais e configuração
  do catálogo.
- Feedback discreto (`ui/toast.py`) ao adicionar produtos à fila, no lugar
  de uma janela de confirmação bloqueante.
- Atalhos globais: F3, Ctrl+F, Ctrl+P, Ctrl+L.
- Correção de usabilidade: alterar a quantidade de um item da fila
  (`[-]`/`[+]`/edição direta) não reconstrói mais a lista inteira de
  cartões — a posição do scroll, a seleção e o foco de teclado são
  preservados (antes, qualquer alteração de quantidade fazia a lista
  voltar ao topo).
- Melhorias de navegação: adicionar produtos pela aba "API Jueri" não
  troca mais de aba automaticamente — o usuário decide quando ver a fila.

## Qualidade

- Suíte de testes automatizados consolidada: 541 testes (`unittest`),
  100% passando no momento desta auditoria.
- Arquitetura estabilizada: motor de impressão único, constantes físicas
  centralizadas (`core/print_layout.py`), componentes de tabela
  (ordenação, seleção por arraste, persistência de estado) reutilizados
  entre as duas telas em vez de duplicados.

---

# Próximas versões

As mudanças futuras serão registradas neste documento seguindo o mesmo
padrão — apenas mudanças relevantes para o projeto, sempre conferidas
contra o código antes de serem registradas como concluídas.
