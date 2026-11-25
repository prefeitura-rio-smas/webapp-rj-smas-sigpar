# Aprovação de governança — SIGPAR-SMAS

Data: 2026-11-25
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

## Assinaturas

- [ ] Data owner (SMAS/SUBG)
- [ ] DPO/encarregado
- [x] Segurança/operação — Leone Barreto, 2026-11-25
- [ ] Access review — Leonardo Meireles / Vitor Dantas (Meireles/Vitor pendentes)

## Pendências para concluir o F-D6

1. Nome/contato do DPO/encarregado e do subsecretário (data owner).
2. Assinatura do data owner e do DPO.
3. Confirmação do Meireles/Vitor na access review.
4. Aprovação/deploy da release `v0.2.0` no environment `production` (F-D5 mínimo).
