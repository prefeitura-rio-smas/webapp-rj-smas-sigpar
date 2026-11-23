## Resumo

<!-- O que muda e por quê. -->

## Tipo

- [ ] Correção
- [ ] Funcionalidade
- [ ] Migração de dados/schema
- [ ] Segurança/infra
- [ ] Documentação

## Checklist

- [ ] `uv run pytest -q` passa (incluindo PDF quando aplicável)
- [ ] `uv run ruff check api etl jobs tests` e `uv run bandit ...` passam
- [ ] Migrações testadas em banco novo e em cópia da versão anterior
- [ ] Backup/rollback considerado (se houver migração ou deploy)
- [ ] Nenhum segredo, credencial, DB, planilha ou dado pessoal no diff
- [ ] Dados pessoais/sensíveis tratados conforme `docs/governanca-dados.md`
- [ ] Testado em staging (ou justificado por que não)
- [ ] Documentação/runbook atualizados
- [ ] Screenshot/PDF de exemplo anexado (mudanças de UI/relatório)

## Impacto em dados

<!-- Tabelas/colunas afetadas, retenção, acesso, necessidade de backup. -->
