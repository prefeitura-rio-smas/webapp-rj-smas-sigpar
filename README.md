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

## DevOps / repositório

**F-D1 — bootstrap concluído**

- Repo público `prefeitura-rio-smas/webapp-rj-smas-sigpar`; branches `main`/`staging`.
- CI: testes de API/migração/PDF, Ruff, Bandit, pip-audit, Gitleaks, dependency review.
- CodeQL: **default setup** (Python/JavaScript/Actions) + secret scanning/push protection.
- Dependabot: atualizações semanais para `uv` e GitHub Actions.
- Branch protection em `main`/`staging`: PR, 1 review, code owner, checks obrigatórios, sem force/delete.
- Environments: `staging` (branch `staging`) e `production` (reviewers + bypass admin, branch `main`/tag `v*`).
- Deploy Firebase/GCP: **WIF** configurado; service account `sigpar-deploy`; sem chave no GitHub.
- Staging: site `sigpar-staging.web.app` criado e domínio autorizado no Firebase Auth.
- Segurança: secrets em environments; Gitleaks; CodeQL; Dependabot; WIF; branch protection.
- Governança: `docs/governanca-dados.md` (classificação, retenção, LGPD, acesso, backup).
- `licenca_medica` (dado de saúde): decisão Admin-only/mascarado — implementação na **F-D5**.

**F-D3 — staging e deploy (concluída na parte de staging)**

- Staging API: https://sigpar-staging.152.53.195.232.nip.io (`sigpar-api-staging`, porta 3105, systemd non-root).
- Staging frontend: https://sigpar-staging.web.app (Firebase Auth autorizado).
- DB staging sintético em `/var/lib/sigpar/staging/staging.sqlite` (5 unidades, 2 admins).
- Release layout: `/opt/sigpar-staging/{releases,current}`; Chromium compartilhado em `/opt/sigpar/chromium`.
- Deploy VPS: `deploy/vps/sigpar-deploy` + inner + sudoers + SSH usuários `sigpar-deploy-staging`/`prod`.
- Workflows: `deploy-staging.yml` e `deploy-production.yml` (este último entra na F-D4).

**F-D5 mínimo — dado de saúde (concluído)**

- `licenca_medica` mascarado para não-admin na API/PDF/tela; create/edit de não-admin não grava o campo.
- Edição por não-admin **preserva** o valor existente.
- Snapshot do Sheet grava `Restrito`; binário criptografado/offsite, CSP/SRI e rate limit ficam no backlog com aceite formal.

**F-D4 — cutover de produção (concluída)**

- API prod agora em `/opt/sigpar/prod/current`, serviço `sigpar-api` **non-root** (`sigpar-prod`).
- DB prod copiado para `/var/lib/sigpar/prod/sigpar.sqlite` (83 lançamentos, 96 usuários, 86 unidades).
- Frontend `sigpar.web.app` republicado a partir da `main`; `/health` e `/me` validados.
- Backup (`/usr/local/bin/sigpar-backup`, cron 03:15 BRT) re-apontado para o novo DB/release.
- Rollback disponível: unit antiga em `/etc/systemd/system/sigpar-api.service.bak-*` + DB antigo em `/root/sigpar/db/sigpar.sqlite`.
- Workflow `deploy-production.yml` pronto para releases `v*` com environment `production`.

**Próximas fases**

- **F-D6**: governança operacional (DPO/retention/access review) e catálogo; aceite formal do backlog.
- **F-D2**: testes de contrato/segurança e cobertura.
- **F-D7**: monitoração, runbooks finais e treinamento.
- **Backlog F-D5**: binário criptografado/offsite, CSP/SRI, rate limit, version history do Sheet.

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
