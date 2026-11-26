# Runbook — SIGPAR

> Estado atual: F-D5 em produção (`v0.2.0`); F-D6 com assinaturas pendentes.

## URLs

| Ambiente | Frontend | API |
|---|---|---|
| Produção | https://sigpar.web.app | https://sigpar.152.53.195.232.nip.io |
| Staging | https://sigpar-staging.web.app | https://sigpar-staging.152.53.195.232.nip.io |

## Serviços atuais (VPS)

```bash
systemctl status sigpar-api
journalctl -u sigpar-api -f
curl -s https://sigpar.152.53.195.232.nip.io/health
docker logs --tail 50 caddy-corin
```

- API prod: `127.0.0.1:3103`, `sigpar-api` (usuário `sigpar-prod`, release `/opt/sigpar/prod/current`).
- API staging: `127.0.0.1:3105`, `sigpar-api-staging` (release `/opt/sigpar-staging/current`).
- DB prod: `/var/lib/sigpar/prod/sigpar.sqlite`; staging: `/var/lib/sigpar/staging/staging.sqlite`.
- Caddy/Traefik: ver `docs/operacao.md`.
- Backup: `/usr/local/bin/sigpar-backup` via `sigpar-backup.timer` (03:15 America/Sao_Paulo) + Sheet (`licenca_medica=Restrito`).

## Rollback do cutover F-D4

```bash
# unit antiga (root, /root/sigpar) — backup criado no cutover
ls /etc/systemd/system/sigpar-api.service.bak-*
systemctl stop sigpar-api
cp /etc/systemd/system/sigpar-api.service.bak-<timestamp> /etc/systemd/system/sigpar-api.service
systemctl daemon-reload && systemctl start sigpar-api
# DB antigo continua em /root/sigpar/db/sigpar.sqlite
```

## Deploy de frontend (atual)

```bash
cd /root/sigpar
python3 deploy/deploy_hosting.py "mensagem"
```

No CI/CD: WIF + `firebase deploy --only hosting:<target>`.

## Migrações

```bash
# sempre com backup prévio em produção
PYTHONPATH=api python3 -m app.migrate --db /var/lib/sigpar/prod/sigpar.sqlite
```

## Backup

```bash
sudo systemctl start sigpar-backup.service
sudo journalctl -u sigpar-backup.service -n 30 --no-pager
```

Binário criptografado/offsite: entra na F-D5 (`age` + Drive). O backup binário é
a recuperação primária; o Sheet é snapshot legível com dados sensíveis mascarados.

## Restore (binário — a implementar F-D5)

1. Baixar o `.sqlite.gz.age` mais recente.
2. Descriptografar com a chave `age` do cofre.
3. Restaurar em banco novo; validar contagens/integridade.
4. Parar API, trocar arquivo, subir, `/health` e smoke.

## Restore (Sheet — fallback)

```bash
set -a; . /etc/sigpar/sigpar-prod.env; set +a
/opt/sigpar/prod/current/.venv/bin/python /opt/sigpar/prod/current/etl/restore_from_sheet.py /tmp/sigpar-restored.sqlite
```

Atenção: desde a F-D5 o snapshot do Sheet grava `licenca_medica` como `Restrito`;
o restore do Sheet não recupera o valor real. A cópia full/criptografada está no
backlog do F-D5.

## Rollback de deploy

- Release anterior: `sigpar-deploy production <tag-anterior>` (F-D4).
- Migração: restaurar backup pré-deploy; validar; subir release compatível.
- Frontend: republicar a release anterior no Firebase Hosting.

## Incidentes

Ver `docs/governanca-dados.md` §9 e `SECURITY.md`.
