# Prompt Template

Versão: 2.0 (revisado por auditoria de código)

Última atualização: Julho/2026

Este documento define o padrão de trabalho para qualquer IA utilizada no
desenvolvimento do Santa Rubi Label Studio.

> Nota de nomenclatura: o arquivo listado abaixo como "guia de arquitetura"
> está fisicamente salvo em `docs/ai/LABEL_STUDIO_GUIDE.md` (sem o prefixo
> numérico "01_" usado pelos demais arquivos deste conjunto). Isso foi
> constatado durante a auditoria de código e mantido como está — este
> template não deve ser usado como justificativa para renomear o arquivo
> sem instrução explícita.

---

# Antes de iniciar qualquer tarefa

Antes de implementar qualquer funcionalidade, a IA deve considerar os
seguintes documentos:

1. `LABEL_STUDIO_GUIDE.md` — arquitetura oficial.
2. `02_PROJECT_CONTEXT.md` — contexto de negócio.
3. `03_DESIGN_SYSTEM.md` — identidade visual e componentes.
4. `04_ROADMAP.md` — prioridades e estado atual.
5. `05_CHANGELOG.md` — histórico do que já foi entregue.

Caso exista conflito entre a implementação proposta e esses documentos, os
documentos devem prevalecer.

Caso exista conflito entre um desses documentos e o código-fonte real, o
código deve ser tratado como a fonte de verdade — e a divergência
reportada, não silenciada (ver `ARCHITECTURE_AUDIT.md` para o método usado
na última auditoria completa).

---

# Objetivo

A IA deve atuar como desenvolvedora do projeto, respeitando integralmente
sua arquitetura e padrões.

Ela não deve propor alterações estruturais sem solicitação explícita.

---

# Princípios

Sempre:

- preservar a arquitetura existente (ver `LABEL_STUDIO_GUIDE.md`: um único
  motor de impressão, uma única `PrintQueue`, `CatalogProduct` como modelo
  comum);
- reutilizar componentes existentes — em especial os já compartilhados
  entre telas: `core/column_sort.py`, `ui/treeview_selection.py`,
  `ui/toast.py`, `core/table_state.py`, `core/queue_feedback.py`;
- evitar duplicação de código;
- manter o código simples;
- manter baixo acoplamento (`core/` nunca importa `ui/`; `ui/main_window.py`
  e `ui/catalog_tab.py` nunca se importam mutuamente);
- preservar compatibilidade.

Nunca:

- reescrever grandes partes do sistema sem necessidade;
- alterar a arquitetura por iniciativa própria;
- criar soluções paralelas para problemas já resolvidos (ex.: um segundo
  cliente HTTP para Jueri, uma segunda fila de impressão, um segundo
  leitor de Excel além de `ExcelCatalogSource`).

---

# Fluxo de trabalho esperado

Para cada tarefa, a IA deve seguir a sequência:

## 1. Entendimento

Explicar brevemente o problema.

---

## 2. Impacto

Indicar quais arquivos serão alterados.

---

## 3. Arquitetura

Explicar como a solução respeita a arquitetura existente.

---

## 4. Implementação

Implementar apenas o necessário.

---

## 5. Testes

Criar ou atualizar testes quando aplicável. Rodar a suíte completa
(`python -m unittest discover -s tests -p "test_*.py"`) antes de reportar a
tarefa como concluída.

---

## 6. Resumo

Explicar objetivamente o que foi alterado.

---

# Restrições

A IA não deve:

- remover funcionalidades existentes sem autorização;
- alterar fluxos principais;
- modificar a `PrintQueue` sem necessidade;
- alterar `Product` ou `CatalogProduct` sem justificativa técnica;
- inventar informação sobre o sistema que não possa ser confirmada pelo
  código ou por instrução explícita do usuário.

---

# Quando sugerir melhorias

Caso identifique oportunidades de melhoria, a IA deve:

- apresentar a sugestão separadamente;
- explicar benefícios;
- aguardar aprovação antes da implementação.

---

# Qualidade esperada

Toda implementação deve ser:

- pequena;
- incremental;
- testável;
- consistente com o restante do projeto.
