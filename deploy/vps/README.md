# Deploy VPS — SIGPAR

## Fluxo

1. CI cria uma release `staging-<sha>` (ou `v*` em produção) com:
   - `sigpar-api-<tag>.tar.gz` (api, db, jobs, etl, pyproject, uv.lock)
   - `sigpar-api-<tag>.tar.gz.sha256`
2. O workflow acessa a VPS via SSH com o usuário `sigpar-deploy-staging`/`sigpar-deploy-prod`.
3. `authorized_keys` força `command="/usr/local/bin/sigpar-deploy"`; o comando remoto é `staging <tag>`/`production <tag>`.
4. O wrapper re-executa o inner como usuário de serviço, reinicia o systemd e valida `/health`; falha → rollback do symlink.

## Instalação (uma vez)

```bash
install -m 755 deploy/vps/sigpar-deploy /usr/local/bin/sigpar-deploy
install -m 755 deploy/vps/sigpar-deploy-inner /usr/local/bin/sigpar-deploy-inner
install -m 440 deploy/vps/sudoers-sigpar-deploy /etc/sudoers.d/sigpar-deploy
visudo -cf /etc/sudoers.d/sigpar-deploy
```

Chaves: gerar ed25519 por ambiente, colocar a pública em
`~sigpar-deploy-<env>/.ssh/authorized_keys` com o forced command e a privada no
GitHub Environment secret `VPS_SSH_KEY`.

```text
command="/usr/local/bin/sigpar-deploy",no-pty,no-port-forwarding,no-agent-forwarding,no-X11-forwarding ssh-ed25519 AAAA...
```

## Layout

- Prod: `/opt/sigpar/prod/{releases,current,backups,.uv-cache}`; DB `/var/lib/sigpar/prod/sigpar.sqlite`.
- Staging: `/opt/sigpar-staging/{releases,current,.uv-cache}`; DB `/var/lib/sigpar/staging/staging.sqlite`.
- Serviços: `sigpar-api` (prod, 3103) e `sigpar-api-staging` (3105).
- Chromium compartilhado: `/opt/sigpar/chromium/chrome-linux-arm64/chrome`.

## Observações

- O banco de produção não é versionado; o backup pré-deploy binário é feito pelo inner.
- Migrações rodam com `app.migrate` (versionadas em `db/migrations`).
- Rollback de código = symlink anterior; rollback de schema = restaurar backup pré-deploy.
