# Pendências — SIGPAR

## F1 (fechar)

- [x] Projeto Firebase `sigpar-smas` + site `sigpar` (`sigpar.web.app`)
- [x] Web App + config pública
- [x] Placeholder publicado no Hosting
- [x] API FastAPI + schema v1 + `/health` + `/me` + testes
- [x] Caddy/TLS + systemd + `/etc/sigpar.env`
- [x] Esqueletos de ETL, backup e restore
- [x] **Auth Google habilitado via API** (`firebase:provisionFirebaseApp`), OAuth client criado, `sigpar.web.app` autorizado
- [x] Página de teste de login publicada em `https://sigpar.web.app/login.html`
- [ ] Validar login real (telefone) e publicar o consent screen para os 95 usuários (F2/F5)
- [x] Planilha `SIGPAR - Backup` criada/compartilhada com a SA e `SIGPAR_BACKUP_SHEET_ID` configurado
- [x] Backup testado (abas + `_meta`, banco vazio)
- [x] Restore testado (banco vazio)
- [ ] Testar backup + restore com dados reais (F2)
- [ ] Repositório git com primeiro commit revisado

## F2 (dados) — concluída

- [x] Implementar `etl/migrate_from_sheet.py --write`
- [x] Importar cadastros e 83 lançamentos; reconciliação de contagens/somas
- [x] Seed dos usuários e permissões (94 e-mails únicos + 2 admins de teste = 96)
- [x] Testar `/me` com token Firebase real (Admin)
- [x] Duplicados unidade+mês: 8 combinações, 17 lançamentos com `duplicado=1`
- [x] Backup no Sheet + restore com dados reais (contagens idênticas)
- [x] Relatório em `docs/migracao-relatorio.md`
- Observações: `Operacional` linha 21 (ID repetido/descrição vazia) ignorada; `lancamento_veiculos` vazio por design (texto em `veiculos_detalhe`).

## F3 (lançamento) — implementada, em validação

- [x] Template próprio de PDF (logos oficiais, seções, assinatura) em `api/app/templates/relatorio.html`
- [x] Renderização no Chromium headless (`api/app/pdf.py`)
- [x] Endpoints de criação/edição/exclusão com transação, auditoria e 409 de duplicidade
- [x] Frontend em `https://sigpar.web.app` (formulário completo, recentes, editar, PDF)
- [x] Teste de API em banco cópia: criar, duplicar (409), confirmar, PDF 200
- [ ] Validar o formulário no celular e ajustar o layout do PDF conforme o modelo oficial
- [ ] Definir se o PDF precisa ficar idêntico ao do GAS ou se a versão nova é aceitável

## F4 (consultas/consolidado)

- [ ] Busca por ID, unidade e mês/data
- [ ] Relatório consolidado (PDF)
- [ ] Exportações (CSV/XLSX) — opcional

## F5 (cutover)

- [ ] Rodada em paralelo; treinamento; congelar escrita na planilha
- [ ] Migração final e reconciliação
- [ ] Planilha antiga read-only/arquivo
- [ ] Plano de rollback

## F-D1 (DevOps) — concluída

- [x] Repo público + commit inicial + histórico sanitizado
- [x] CI, CodeQL default, Gitleaks, dependency review, Dependabot
- [x] Branch protection `main`/`staging`, environments e reviewers
- [x] WIF para Firebase/GCP; service account `sigpar-deploy`
- [x] Site de staging + domínio autorizado no Firebase Auth
- [x] Migrações SQL versionadas + runner; `pyproject`/`uv.lock`; testes

## F-D3 — staging (concluída)

- [x] Usuários `sigpar-prod`/`sigpar-staging`/deploy; release layout; Chromium compartilhado
- [x] Staging API/DB sintéticos (`sigpar-api-staging`, 3105)
- [x] Caddy staging + TLS; frontend `sigpar-staging.web.app`
- [x] Deploy script SSH + sudoers + ambiente staging
- [x] Workflow `deploy-staging.yml`
- [x] F-D4: cutover de produção (`/opt/sigpar/prod`, DB `/var/lib/sigpar/prod`, serviço non-root, frontend republicado, backup re-apontado)
- [x] F-D5 mínimo: `licenca_medica` mascarado (API/PDF/tela/Sheet); preservação em edição de não-admin
- [x] F-D6 documentação: access review, catálogo, incidentes, riscos, aprovação; backup timer 03:15 BRT
- [x] F-D5 produção: `v0.2.1` deployada em 2026-11-26 via `sigpar-deploy-inner production v0.2.1` (break-glass admin; CI verde; backup pré-deploy, health e headers validados)
- [ ] F-D6 assinaturas: data owner/DPO, Meireles/Vitor
- [x] F-D2: testes de contrato/segurança, headers e cobertura (90% total; job API 84,5%; gate 75%)
- [x] F-D7: uptime GitHub + healthcheck local (units instaladas, timer ativo) + monitoração/runbook/treinamento
- [ ] Backlog F-D5: backup binário criptografado/offsite, CSP/SRI, rate limit, version history do Sheet

## Pós-MVP

- [ ] Telas de administração de cadastros
- [ ] Envio de e-mail do PDF (SMTP/Google)
- [ ] Dashboard/indicadores
- [ ] Histórico de versões visível

## Pontos de dados a confirmar

- `Avaliacao` (6 linhas, NÍVEL CENTRAL) vs `Avaliacao_Central` (11 notas): coexistência?
- `Postos` com linhas repetidas por unidade: confirmar que é slot, não duplicidade.
- `Historico_Lancamentos` tem ~850 linhas vazias no range (formatação) — ignorar no ETL.
