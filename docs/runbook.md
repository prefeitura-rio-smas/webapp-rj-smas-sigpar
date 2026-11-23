# Runbook — SIGPAR

> Estado atual: F-D1 (bootstrap do repo/CI). Deploy automatizado entra na F-D3/F-D4.

## URLs

| Ambiente | Frontend | API |
|---|---|---|
| Produção | https://sigpar.web.app | https://sigpar.152.53.195.232.nip.io |
| Staging (a criar) | https://sigpar-staging.web.app | https://sigpar-staging.152.53.195.232.nip.io |

## Serviços atuais (VPS)

```bash
systemctl status sigpar-api
journalctl -u sigpar-api -f
curl -s https://sigpar.152.53.195.232.nip.io/health
docker logs --tail 50 caddy-corin
```

- API: `127.0.0.1:3103`, systemd `sigpar-api`.
- DB: `/root/sigpar/db/sigpar.sqlite` (migrar para `/var/lib/sigpar`).
- Caddy/Traefik: ver `docs/operacao.md`.
- Backup: cron `/etc/cron.d/sigpar-backup` (03:15 BRT) + Sheet.

## Deploy de frontend (atual)

```bash
cd /root/sigpar
python3 deploy/deploy_hosting.py "mensagem"
```

No CI/CD: WIF + `firebase deploy --only hosting:<target>`.

## Migrações

```bash
# sempre com backup prévio em produção
PYTHONPATH=api python3 -m app.migrate --db /var/lib/sigpar/sigpar.sqlite
```

## Backup

```bash
set -a; . /etc/sigpar.env; set +a
python3 /root/sigpar/jobs/backup_to_sheet.py
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
set -a; . /etc/sigpar.env; set +a
python3 /root/sigpar/etl/restore_from_sheet.py /tmp/sigpar-restored.sqlite
```

## Rollback de deploy

- Release anterior: `sigpar-deploy production <tag-anterior>` (F-D4).
- Migração: restaurar backup pré-deploy; validar; subir release compatível.
- Frontend: republicar a release anterior no Firebase Hosting.

## Incidentes

Ver `docs/governanca-dados.md` §9 e `SECURITY.md`.
