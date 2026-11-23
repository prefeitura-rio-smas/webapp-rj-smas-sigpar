# SIGPAR — Sistema Integrado de Gestão e Monitoramento de Parcerias

Reescrita do app Google Apps Script (SIGPAR-SMAS) para:

- **Frontend**: Firebase Hosting em https://sigpar.web.app (site `sigpar` do projeto `sigpar-smas`)
- **Auth**: Firebase Authentication (Google)
- **API**: FastAPI na VPS, atrás de Caddy/TLS
- **Banco**: SQLite na VPS (`db/sigpar.sqlite`) — fora do Firebase
- **Relatórios**: PDF via Chromium/Playwright, download pelo usuário
- **Backup**: binário criptografado (local + Drive) + snapshot no Google Sheets
- **Repositório**: https://github.com/prefeitura-rio-smas/webapp-rj-smas-sigpar

## Status

F1 — fundação (concluída):

- [x] Repo e estrutura
- [x] Projeto Firebase `sigpar-smas` + site `sigpar` (https://sigpar.web.app)
- [x] Web App + config pública
- [x] Auth Google habilitado (via provisionamento API) + página de teste de login
- [x] Placeholder publicado no Hosting
- [x] API + SQLite + /health + /me
- [x] Caddy/systemd
- [x] ETL/backup (esqueletos)
- [x] Planilha de backup + teste de restore

## F3 — lançamento (em validação)

- [x] CRUD transacional de lançamentos + auditoria + aviso de duplicidade
- [x] PDF próprio com logos oficiais renderizado no Chromium
- [x] Formulário no ar em `https://sigpar.web.app`
- [x] Teste de API (criar/duplicar/confirmar/PDF) em banco cópia
- [ ] Validar no celular e ajustar o PDF ao modelo oficial

## F2 — dados (concluída)

- [x] Migração dos cadastros e dos 83 lançamentos (`docs/migracao-relatorio.md`)
- [x] 86 unidades, 96 usuários (94 da planilha + 2 admins), 1.260 postos, 4.787 insumos
- [x] Reconciliação de contagens e somas (100%)
- [x] Backup no Sheet + restore real validados
- [x] Login Google validado com `/me` real

## DevOps / repositório (F-D em andamento)

- Repo público `prefeitura-rio-smas/webapp-rj-smas-sigpar`; branches `main`/`staging`.
- CI: testes de API/migração/PDF, Ruff, Bandit, pip-audit, Gitleaks, dependency review, CodeQL.
- CD: staging automático; produção por release + environment com revisores.
- Deploy da API: release imutável + SSH com usuário dedicado/forced command.
- Staging: `sigpar-staging.web.app` + API/DB sintéticos.
- Segurança: WIF para Firebase/GCP; SSH sem root; systemd hardening; CSP/SRI (F-D5).
- Governança: `docs/governanca-dados.md` (classificação, retenção, LGPD, acesso, backup).
- `licenca_medica` (dado de saúde): Admin-only; mascarado para os demais.

## Estrutura

```
api/        FastAPI (auth, endpoints, PDF)
web/        SPA estática publicada no Firebase Hosting
db/         schema.sql + migrations SQL versionadas
etl/        Sheet -> SQLite (F2) e restore a partir do Sheet
jobs/       backup_to_sheet.py
deploy/     deploy_hosting.py, Caddyfile, systemd
docs/       arquitetura, modelo de dados, operação, governança, runbook
.github/    CI, security, Dependabot, CODEOWNERS, templates
pyproject.toml / uv.lock
secrets/    chaves/credenciais (gitignored)
```

## Decisões (F0)

- MVP com paridade funcional + hardening (transações, auditoria, validação).
- SQLite é a fonte da verdade; a planilha antiga vira arquivo/exportação.
- Perfis Admin/Cord/User mantidos; 95 usuários atuais.
- Sem envio de e-mail no MVP (PDF apenas para download).
- Duplicidade unidade+mês permitida com aviso + audit_log.
- Cadastros via ETL/CLI no MVP; telas de admin depois.
- Backup binário criptografado + snapshot no Sheet (o Sheet é legível; o binário é a recuperação).
- `licenca_medica` restrito a Admin e mascarado no PDF/API para os demais.

## Desenvolvimento

```bash
uv sync
uv run uvicorn app.main:app --app-dir api --host 127.0.0.1 --port 3103

uv run pytest -q
uv run ruff check api etl jobs tests
```

Configuração em `/etc/sigpar.env` (600). Ver `docs/operacao.md`,
`docs/governanca-dados.md` e `docs/runbook.md`.
