# Arquitetura — SIGPAR

## Visão

```
Usuário
  │
  ▼
https://sigpar.web.app            Firebase Hosting (site sigpar)
  │  Firebase SDK (auth Google)  →  ID token
  │  fetch(Authorization: Bearer <idToken>)
  ▼
https://sigpar.152.53.195.232.nip.io   Caddy (TLS Let's Encrypt)
  │
  ▼
FastAPI :3103 (uvicorn, 1 worker)
  ├── verifica ID token Firebase (projeto sigpar-smas)
  ├── autorização por perfil/unidade (SQLite)
  ├── SQLite /var/lib/sigpar/prod/sigpar.sqlite (WAL)
  ├── geração de PDF (Chromium/Playwright)
  └── snapshot diário → Google Sheets (service account)
```

## Camadas

| Camada | Implementação |
|---|---|
| Experiência | HTML/CSS/JS estático no Firebase Hosting; Bootstrap; views de lançamento, consulta e consolidado |
| Identidade | Firebase Auth Google; API confere `email_verified` + allowlist `usuarios` |
| API | FastAPI, Pydantic, transações SQLite, CORS restrito |
| Domínio | Regras Admin/Cord/User, mês de referência, totais, parecer, classificação, duplicidade |
| Persistência | SQLite (WAL, foreign_keys, busy_timeout); schema versionado |
| Relatórios | Template HTML/CSS herdado do GAS; render via Chromium; download |
| Backup | Job diário exporta todas as tabelas para uma planilha Google; `restore_from_sheet.py` |
| Operação | systemd (`sigpar-api`), Caddy em container host-network, logs/journal, `/health` |

## Decisões de infraestrutura

- **VPS**: mesma do CORIN (152.53.195.232).
- **Caddy**: edge (`/root/edge/Caddyfile`); site `sigpar.152.53.195.232.nip.io` → `127.0.0.1:3103`.
- **Traefik**: removido do fluxo do SIGPAR; o Caddy é o edge.
- **SQLite**: um arquivo, um writer (uvicorn 1 worker). Backup via `sqlite3 .backup` no job de snapshot (a cópia binária não é persistida no MVP; o Sheet é a cópia de recuperação).
- **Firebase**: projeto novo `sigpar-smas` (o ID `sigpar` já estava em uso), site `sigpar` → `sigpar.web.app`, separado do `rj-smtr-corin`.
- **Sem Firestore**: o banco é SQLite na VPS.
- **Sem e-mail no MVP**: o PDF é gerado e baixado.

## Segurança

- Token Firebase verificado no servidor com os certificados públicos do Google (sem keyfile).
- Allowlist no SQLite; toda query é escopada pelas unidades permitidas.
- CORS apenas para `sigpar.web.app` e domínios Firebase do projeto.
- Headers de segurança na API (`nosniff`, `DENY`, CSP, Referrer/Permissions).
- Monitoração: uptime externo no GitHub Actions + healthcheck local (API/backup).
- API escuta em 127.0.0.1; TLS terminado no Caddy.
- Segredos em `/etc/sigpar.env` (600) e `secrets/` (600, gitignored).
- Auditoria de criação/edição/exclusão em `audit_log`.

## Limitações conhecidas (MVP)

- Backup só em Sheet: RPO de até 24h; restore depende do snapshot (testar).
- Sem envio de e-mail; sem telas de administração de cadastros.
- PDF renderizado no Chromium pode ter pequenas diferenças visuais em relação ao Google.
- Firebase Auth Google precisa ser habilitado uma vez no console.
