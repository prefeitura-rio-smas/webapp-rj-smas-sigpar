# Contribuindo

## Branches e PRs

- `main`: produção; protegida; PR + checks + review.
- `staging`: staging; PR + checks.
- Feature branches: `feat/...`, `fix/...`, `chore/...`.
- PRs pequenos, com descrição, impacto em dados e evidências.
- Nunca commitar `secrets/`, DBs, planilhas, PDFs gerados, `.venv` ou dados reais.

## Desenvolvimento local

```bash
uv sync
uv run uvicorn app.main:app --app-dir api --host 127.0.0.1 --port 3103
# Em outro terminal:
python3 -m http.server 8000 --directory web
```

Para testar sem Firebase Auth:

```bash
SIGPAR_NOAUTH=1 SIGPAR_DEV_EMAIL=<admin-local> uv run uvicorn app.main:app --app-dir api --port 3103
```

O `SIGPAR_DEV_EMAIL` precisa existir em `usuarios` no DB local. Nunca use
`SIGPAR_NOAUTH=1` em produção.

## Testes e qualidade

```bash
uv run ruff check api etl jobs tests
uv run bandit -c pyproject.toml -r api etl jobs
uv run pytest -q
```

O teste de PDF usa `SIGPAR_CHROME` (padrão: Chromium do Playwright na VPS).
O CI usa o Chrome do runner.

## Migrações

- Novas migrações em `db/migrations/NNN_descricao.sql`, imutáveis após merge.
- Aplicar com backup prévio; testar banco novo e upgrade da versão anterior.
- Nunca editar uma migração já aplicada em produção.

## Segurança e governança

- Leia `SECURITY.md` e `docs/governanca-dados.md`.
- Dados de saúde (`licenca_medica`) são restritos a Admin e mascarados para os
  demais; não os inclua em logs, issues ou prints.
- PRs que mudam dados pessoais, retenção ou acesso precisam de revisão de
  governança.
