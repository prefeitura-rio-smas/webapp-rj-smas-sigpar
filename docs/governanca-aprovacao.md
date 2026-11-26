# Aprovação de governança — SIGPAR-SMAS

Data: 2026-11-25 (atualizado em 2026-11-26 após deploy da F-D5)
Documento base: `docs/governanca-dados.md` (F-D6)

## Partes

| Papel | Nome/conta | Status |
|---|---|---|
| Data owner | SMAS/SUBG — `subg.smas@prefeitura.rio` (subsecretário/a a confirmar) | pendente |
| DPO/encarregado | Prefeitura — contato a confirmar | pendente |
| Data steward | Leone Barreto + Leonardo Meireles | revisado |
| Segurança/operação | Leone Barreto | revisado |
| Access review | Leone + Meireles + Vitor Dantas | parcial (Meireles/Vitor pendentes) |

## Escopo aprovado (proposta)

- Classificação de dados e controles de acesso (`docs/governanca-dados.md`, `docs/catalogo-dados.md`).
- Retenção: 5 anos lançamentos/audit; 90 dias logs; 30 dias binário (backlog); 12 meses Sheet.
- Access review: 96 usuários do app (19/10/67), 9 collaborators GitHub, 5 usuários VPS, Firebase/Drive/SAs; 2 contas de teste removidas.
- Riscos R1–R8 (`docs/riscos.md`); backlog F-D5 aceito pelo owner técnico (binário/offsite, CSP/SRI/rate limit, version history do Sheet).
- `licenca_medica`: Admin-only; API/PDF/tela/Sheet mascarados (F-D5 mínimo).
- F-D5 produção: deploy direto na VPS em 2026-11-26 (`sigpar-deploy-inner production v0.2.0`), via break-glass de admin; environment `production` não aprovado e run 45485818588 cancelado; backup pré-deploy, migração, health e frontend validados.

## Assinaturas

- [ ] Data owner (SMAS/SUBG)
- [ ] DPO/encarregado
- [x] Segurança/operação — Leone Barreto, 2026-11-25
- [x] Deploy F-D5 produção — Leone Barreto, 2026-11-26 (break-glass; sem segundo revisor)
- [ ] Access review — Leonardo Meireles / Vitor Dantas (Meireles/Vitor pendentes)

## Pendências para concluir o F-D6

1. Nome/contato do DPO/encarregado e do subsecretário (data owner).
2. Assinatura do data owner e do DPO.
3. Confirmação do Meireles/Vitor na access review.
4. [x] Deploy da release `v0.2.0` em produção — concluído em 2026-11-26 via break-glass, fora do gate do environment; registrar a retrospectiva no F-D6.
