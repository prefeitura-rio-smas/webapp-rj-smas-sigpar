# Monitoração — SIGPAR-SMAS

## Camadas

| Camada | Implementação | Frequência | Sinal |
|---|---|---|---|
| Uptime externo | GitHub Actions `uptime.yml` | 15 min | issue `[monitoracao] SIGPAR indisponivel` (abre/comenta/fecha) |
| API local + backup | `sigpar-healthcheck.timer` | 15 min | `systemctl --failed` / `journalctl -u sigpar-healthcheck` |
| Backup diário | `sigpar-backup.timer` | 03:15 America/Sao_Paulo | `backup_runs` + healthcheck (idade > 26h falha) |
| CI e segurança | CI, CodeQL, Gitleaks, Dependabot | PR/push | GitHub Actions |
| Deploy | `deploy-production.yml`/`deploy-staging.yml` + smoke | release | GitHub Actions |

## O que é verificado

- `GET /health` da API de produção: `ok=true`, `db=ok` e `schema_version`.
- Frontend `https://sigpar.web.app`: HTTP 200.
- Último `backup_runs.status='ok'` e `finished_at` com menos de 26h.
- O healthcheck local não consulta dados pessoais e imprime apenas status/idades.

## Uptime externo (GitHub)

O workflow `.github/workflows/uptime.yml` roda a cada 15 minutos e no
`workflow_dispatch`:

- se API e frontend respondem, fecha a issue de incidente aberta (se houver);
- se falhar, abre uma issue com o título `[monitoracao] SIGPAR indisponivel` ou
  comenta na issue já aberta e falha o run.

O GitHub pode atrasar schedules; para incidente em andamento, use também os
comandos manuais abaixo. Nunca cole PII/segredos na issue (o repositório é
público).

## Healthcheck local (VPS)

O script `jobs/healthcheck.py` verifica a API em `127.0.0.1:3103` e o último
backup no SQLite. A unidade/timer estão em `deploy/sigpar-healthcheck.*`.
A ativação acontece depois de um release que inclua `jobs/healthcheck.py`:

```bash
sudo install -m 644 deploy/sigpar-healthcheck.service /etc/systemd/system/
sudo install -m 644 deploy/sigpar-healthcheck.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now sigpar-healthcheck.timer
sudo systemctl start sigpar-healthcheck.service
sudo journalctl -u sigpar-healthcheck.service -n 30 --no-pager
```

O check roda como `sigpar-prod`, somente leitura no banco. Falha = status
`failed` no systemd; o alerta externo continua sendo a issue do GitHub.

## Comandos manuais

```bash
curl -fsS https://sigpar.152.53.195.232.nip.io/health
curl -fsS -o /dev/null -w '%{http_code}\n' https://sigpar.web.app
systemctl is-active sigpar-api
systemctl list-timers 'sigpar-*' --no-pager
sudo journalctl -u sigpar-api -n 80 --no-pager
sudo systemctl start sigpar-backup.service
sudo journalctl -u sigpar-backup.service -n 20 --no-pager
sqlite3 /var/lib/sigpar/prod/sigpar.sqlite \
  "SELECT status,finished_at FROM backup_runs ORDER BY id DESC LIMIT 1;"
```

## Resposta a alerta

1. Confirmar se é falha real (API, frontend, DNS/TLS, VPS).
2. Ver logs da API, Caddy e `journalctl`; não expor PII na issue.
3. Se for deploy/erro de código, seguir rollback do `docs/runbook.md`.
4. Se for backup, rodar o backup manual e verificar `backup_runs`.
5. Registrar causa/ação no incidente e atualizar `docs/incidentes.md` se necessário.

Ver também `docs/runbook.md` e `docs/treinamento.md`.
