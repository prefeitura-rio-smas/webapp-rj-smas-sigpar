# Operação — SIGPAR

## URLs

| O quê | URL |
|---|---|
| Frontend | https://sigpar.web.app |
| API (health) | https://sigpar.152.53.195.232.nip.io/health |
| Firebase project | `sigpar-smas` |
| Hosting site | `sigpar` |

## Serviços

- **API**: `systemctl status sigpar-api` / `journalctl -u sigpar-api -f` (uvicorn em `127.0.0.1:3103`).
- **Caddy**: container `caddy-corin` (host network; config em `/root/sandbox/corin/caddy/Caddyfile`).
  - Reload: `docker exec caddy-corin caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile`
  - Logs: `docker logs -f caddy-corin`
- **Traefik**: container `traefik` (config dinâmica em `/root/prefect/traefik_dynamic.yml`, file provider com watch).
- **SQLite**: `/root/sigpar/db/sigpar.sqlite` (WAL). A API usa 1 worker.

## Configuração

`/etc/sigpar.env` (600):

```
SIGPAR_DB=/root/sigpar/db/sigpar.sqlite
SIGPAR_FIREBASE_PROJECT=sigpar-smas
SIGPAR_CORS_ORIGINS=https://sigpar.web.app,https://sigpar.firebaseapp.com,https://sigpar-smas.web.app,https://sigpar-smas.firebaseapp.com
SIGPAR_NOAUTH=0
SIGPAR_BACKUP_SHEET_ID=
SIGPAR_BACKUP_SA_KEY=/root/sigpar/secrets/sigpar-backup.json
```

- `SIGPAR_NOAUTH=1` só para desenvolvimento/testes. **Nunca** em produção.
- `secrets/firebase-web-config.json`: config pública do Web App (apiKey/authDomain/projectId/appId).
- `secrets/sigpar-backup.json`: chave da service account de backup (600, gitignored).

## Deploy do frontend

```bash
cd /root/sigpar
python3 deploy/deploy_hosting.py "mensagem do release"
```

No CI/CD a autenticação é via **Workload Identity Federation** (sem chave).
Localmente, o script usa a conta definida em `SIGPAR_FIREBASE_ACCOUNT`.

## Deploy da API

```bash
cd /root/sigpar
git diff            # revisar
systemctl restart sigpar-api
curl -s https://sigpar.152.53.195.232.nip.io/health
```

## Backup (Google Sheets)

Pré-requisitos (uma vez):

1. Planilha `SIGPAR - Backup` na pasta configurada no Drive, compartilhada como
   **Editor** com `sigpar-backup@sigpar-smas.iam.gserviceaccount.com`.
2. IDs configurados em `SIGPAR_BACKUP_SHEET_ID` e `SIGPAR_BACKUP_DRIVE_FOLDER_ID`
   no `/etc/sigpar.env` (não versionar).
3. Teste manual:
   ```bash
   set -a; . /etc/sigpar.env; set +a
   python3 /root/sigpar/jobs/backup_to_sheet.py
   ```
4. Agendamento já instalado em `/etc/cron.d/sigpar-backup` (03:15 America/Sao_Paulo).

O job grava uma aba por tabela + `_meta` (timestamp/contagens/versão do schema).
Ele lê o SQLite em uma transação para o snapshot ser consistente.

## Restore

```bash
set -a; . /etc/sigpar.env; set +a
python3 /root/sigpar/etl/restore_from_sheet.py /root/sigpar/db/sigpar-restored.sqlite
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
docker logs --tail 50 caddy-corin
sqlite3 /root/sigpar/db/sigpar.sqlite 'PRAGMA integrity_check;'
```
