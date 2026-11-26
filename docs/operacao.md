# Operação — SIGPAR

## URLs

| O quê | URL |
|---|---|
| Frontend | https://sigpar.web.app |
| API (health) | https://sigpar.152.53.195.232.nip.io/health |
| Staging frontend | https://sigpar-staging.web.app |
| Staging API | https://sigpar-staging.152.53.195.232.nip.io/health |
| Firebase project | `sigpar-smas` |
| Hosting sites | `sigpar`, `sigpar-staging` |

## Serviços

- **API prod**: `systemctl status sigpar-api` / `journalctl -u sigpar-api -f` (`127.0.0.1:3103`, usuário `sigpar-prod`, código `/opt/sigpar/prod/current`, DB `/var/lib/sigpar/prod/sigpar.sqlite`).
- **API staging**: `systemctl status sigpar-api-staging` / `journalctl -u sigpar-api-staging -f` (`127.0.0.1:3105`, `/opt/sigpar-staging/current`, DB `/var/lib/sigpar/staging/staging.sqlite`).
- **Backup**: `/usr/local/bin/sigpar-backup` via `sigpar-backup.timer` (03:15 America/Sao_Paulo) + Sheet; `licenca_medica` mascarado como `Restrito`. Binário/offsite no backlog F-D5.
- **Monitoração**: `.github/workflows/uptime.yml` (15 min, issue de incidente) + `sigpar-healthcheck.timer` local (API + idade do backup). Detalhes em `docs/monitoracao.md`.
- **Deploy VPS**: ver `deploy/vps/README.md` (`sigpar-deploy`, release imutável + backup + migração + health + rollback).
- **Caddy**: container `caddy-edge` (host network; config em `/root/edge/Caddyfile`).
  - Reload: `docker exec caddy-edge caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile`
  - Logs: `docker logs -f caddy-edge`
- **SQLite**: `/var/lib/sigpar/prod/sigpar.sqlite` (WAL). A API usa 1 worker.

## Configuração

`/etc/sigpar/sigpar-prod.env` (640 root:sigpar-prod):

```
SIGPAR_DB=/var/lib/sigpar/prod/sigpar.sqlite
SIGPAR_FIREBASE_PROJECT=sigpar-smas
SIGPAR_CORS_ORIGINS=https://sigpar.web.app,https://sigpar.firebaseapp.com,https://sigpar-smas.web.app,https://sigpar-smas.firebaseapp.com
SIGPAR_NOAUTH=0
SIGPAR_BACKUP_SHEET_ID=<id>
SIGPAR_BACKUP_SA_KEY=/etc/sigpar/sigpar-backup.json
TZ=America/Sao_Paulo
```

- `SIGPAR_NOAUTH=1` só para desenvolvimento/testes. **Nunca** em produção.
- `secrets/firebase-web-config.json`: config pública do Web App (apiKey/authDomain/projectId/appId).
- `/etc/sigpar/sigpar-backup.json`: chave da service account de backup (640 root:sigpar-prod, não versionar).

## Deploy do frontend

```bash
cd /root/sigpar
python3 deploy/deploy_hosting.py "mensagem do release"
```

No CI/CD a autenticação é via **Workload Identity Federation** (sem chave).
Localmente, o script usa a conta definida em `SIGPAR_FIREBASE_ACCOUNT`.

## Deploy da API

Via release/tag (workflow `deploy-production.yml`) ou break-glass na VPS:

```bash
sudo -u sigpar-prod /usr/local/bin/sigpar-deploy-inner production v0.2.0
sudo systemctl restart sigpar-api
curl -s https://sigpar.152.53.195.232.nip.io/health
```

O inner baixa o asset do release, faz backup pré-deploy, `uv sync`, migração,
troca o symlink e deixa o rollback disponível.

## Backup (Google Sheets)

Pré-requisitos (uma vez):

1. Planilha `SIGPAR - Backup` na pasta configurada no Drive, compartilhada como
   **Editor** com `sigpar-backup@sigpar-smas.iam.gserviceaccount.com`.
2. ID configurado em `SIGPAR_BACKUP_SHEET_ID` e chave em
   `SIGPAR_BACKUP_SA_KEY` no `/etc/sigpar/sigpar-prod.env` (não versionar).
3. Teste manual:
   ```bash
   sudo systemctl start sigpar-backup.service
   sudo journalctl -u sigpar-backup.service -n 30 --no-pager
   ```
4. Agendamento via `sigpar-backup.timer` (03:15 America/Sao_Paulo).

O job grava uma aba por tabela + `_meta` (timestamp/contagens/versão do schema).
Ele lê o SQLite em uma transação para o snapshot ser consistente.

## Restore

```bash
set -a; . /etc/sigpar/sigpar-prod.env; set +a
/opt/sigpar/prod/current/.venv/bin/python /opt/sigpar/prod/current/etl/restore_from_sheet.py /tmp/sigpar-restored.sqlite
# validar contagens; parar a API; trocar o arquivo; subir a API
```

O destino deve ser um arquivo novo. Teste o restore periodicamente — ele é a
única recuperação do MVP (não há backup binário local).

## Firebase Auth

O provider Google foi habilitado via API (`firebase:provisionFirebaseApp`),
que criou o OAuth client e o brand automaticamente. Domínios autorizados:
`localhost`, `sigpar.web.app`, `sigpar-smas.firebaseapp.com`,
`sigpar-smas.web.app`.

Teste: https://sigpar.web.app/login.html (entrar com um usuário Admin cadastrado).
A página chama `/me` com o ID token real.

Para reconfigurar via código no futuro, o caminho é `firebase.json` com bloco
`auth.providers.googleSignIn` + `firebase deploy --only auth`.

Pendente: publicar o OAuth consent screen (Google Auth Platform) para que os
95 usuários externos possam entrar sem aviso de app não verificado.

## Rotinas de verificação

```bash
curl -s https://sigpar.web.app | head
curl -s https://sigpar.152.53.195.232.nip.io/health
systemctl is-active sigpar-api
docker logs --tail 50 caddy-edge
sqlite3 /var/lib/sigpar/prod/sigpar.sqlite 'PRAGMA integrity_check;'
```
