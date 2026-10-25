# Review Checklist

Versão: 2.0 (revisado por auditoria de código)

Última atualização: Julho/2026

Este documento define os critérios mínimos para aprovação de qualquer
implementação realizada no Santa Rubi Label Studio.

Nenhuma implementação deve ser considerada concluída sem passar por esta
revisão.

---

# Arquitetura

☐ Respeita `LABEL_STUDIO_GUIDE.md`

☐ Não cria componentes duplicados (ex.: um segundo `ZplBuilder`, uma
segunda `PrintQueue`, um segundo cliente HTTP Jueri)

☐ Não altera a arquitetura existente sem aprovação explícita

☐ Mantém a separação de responsabilidades (`core/` sem Tkinter; `ui/`
nunca implementa regra de negócio; `ui/main_window.py` e
`ui/catalog_tab.py` nunca se importam mutuamente)

☐ Reutiliza componentes existentes (`core/column_sort.py`,
`ui/treeview_selection.py`, `ui/toast.py`, `core/table_state.py`,
`core/queue_feedback.py` já são compartilhados entre telas)

---

# Código

☐ Código simples

☐ Boa legibilidade

☐ Métodos pequenos

☐ Nomes consistentes com o restante do projeto (português nos
comentários/docstrings, nomes de identificadores em português quando o
domínio é de negócio — ex.: `catalog_tree`, `print_queue`)

☐ Não existem trechos mortos

☐ Não existem comentários desnecessários (comentário só quando explica um
motivo não óbvio — convenção já seguida em todo o código atual)

---

# Interface

☐ Segue o Design System real implementado (`03_DESIGN_SYSTEM.md`) — fonte
"Segoe UI", estilos `App.TButton`/`Primary.TButton`/`Card.TFrame`/
`Subtitle.TLabel` já existentes, não uma paleta de marca ainda não
implementada

☐ Componentes consistentes entre as duas abas

☐ Espaçamentos corretos (consistentes com o restante da tela)

☐ Tipografia consistente

☐ Cores corretas (as da tabela em `03_DESIGN_SYSTEM.md`, seção 2)

☐ Boa experiência do usuário — feedback discreto (`Toast`) para
confirmações de rotina, `messagebox` reservado a avisos que exigem atenção

---

# Funcionalidade

☐ Resolve o problema solicitado

☐ Não quebra funcionalidades existentes

☐ Não cria regressões conhecidas

☐ Mantém compatibilidade

---

# Testes

☐ Testes existentes continuam passando (`python -m unittest discover -s
tests -p "test_*.py"` — 541 testes no momento desta auditoria)

☐ Novos testes adicionados quando necessário

☐ Não reduz cobertura de testes

---

# Performance

☐ Não adiciona processamento desnecessário

☐ Não cria consultas redundantes (ex.: reler o Excel a cada tecla digitada
em vez de filtrar o cache em `CatalogRepository`)

☐ Não aumenta acoplamento

---

# Documentação

☐ Roadmap atualizado (`04_ROADMAP.md`, quando necessário)

☐ Changelog atualizado (`05_CHANGELOG.md`, quando necessário)

☐ Documentação compatível com a implementação — toda afirmação nova deve
ser verificável no código; se não for, deve ser marcada explicitamente
como suposição ou contexto de negócio não verificável (mesmo padrão usado
em `ARCHITECTURE_AUDIT.md`)

---

# Aprovação

Uma implementação somente pode ser considerada concluída quando todos os
itens aplicáveis deste checklist forem atendidos.
