# Registro de riscos — SIGPAR-SMAS

Data: 2026-11-25 (R9 em 2026-11-26). Revisão: F-D6; aceite formal pendente do data owner/DPO.

| ID | Risco | Impacto | Mitigação atual | Backlog/ação | Owner | Prazo |
|---|---|---|---|---|---|---|
| R1 | Backup só no Sheet (sem binário criptografado/offsite) | Perda/perda parcial em falha da VPS; RPO 24h | Sheet diário + restore testado | F-D5: binário `age` + offsite + restore mensal | Leone | backlog |
| R2 | Version history do Sheet pode conter `licenca_medica` antigo | Exposição de dado de saúde a quem tem o Sheet | Acesso restrito ao Drive/SA; snapshot novo grava `Restrito` | Expirar/limpar histórico; F-D5 | Leone | backlog |
| R3 | Sem CSP/SRI e rate limit | XSS/abuso de API | Auth, CORS, TLS, validação | F-D5 | Leone | backlog |
| R4 | Conta pessoal Gmail/VPS/Drive | Continuidade, DPA, offboarding | MFA, least privilege, documentação | Migração para conta institucional | Leone | planejar |
| R5 | VPS única (API+DB) | Indisponibilidade | Backup/restore, systemd restart, uptime + healthcheck | Avaliar redundância | Leone | monitorar |
| R6 | Repo público expõe arquitetura | Reconhecimento para ataque | Sem segredos; branch protection; CodeQL/Gitleaks | Revisar docs; manter sem PII | Leone | contínuo |
| R7 | 19 admins no app | Superprivilégio | Allowlist, MFA, audit | Revisar com owner (access review) | Leone/Meireles/Vitor | F-D6 |
| R8 | `scan.vulnerabilidade` admin | Conta de scanner com privilégio | Revisar necessidade; MFA | Confirmar com owner | Leone | F-D6 |
| R9 | Deploy F-D5 em produção via break-glass, sem segundo revisor | Mudança não revisada; regressão operacional | Release testada em staging; backup pré-deploy; health/rollback; run cancelado | Retrospectiva/assinatura F-D6; revisar processo | Leone | F-D6 |

## Aceite

O backlog F-D5 (R1–R3) foi aceito pelo owner técnico em 2026-11-25, com
implementação mínima da máscara de saúde. O aceite formal do data owner/DPO
fica registrado em `docs/governanca-aprovacao.md` (pendente de assinatura).
R9 registra o deploy de produção de 2026-11-26 feito por break-glass, com
backup pré-deploy, health e rollback; a retrospectiva entra no F-D6.
