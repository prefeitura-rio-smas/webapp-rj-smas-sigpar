# Governança de dados — SIGPAR-SMAS

> Documento vivo. Revisão obrigatória em mudanças de schema, acesso, retenção,
> fornecedores ou finalidade. Aprovação: SMAS (data owner) + encarregado/DPO.
> Última atualização: 2026-11-26 (F-D5 em produção via break-glass + F-D6).

## 1. Escopo e ativos

| Ativo | Onde vive | Observação |
|---|---|---|
| Banco operacional | SQLite na VPS (`/var/lib/sigpar/prod/sigpar.sqlite`) | Fonte da verdade |
| Snapshot legível | Google Sheets (`SIGPAR - Backup`) | `licenca_medica` mascarado como `Restrito` |
| Backup binário | **Backlog F-D5** (local/VPS pré-deploy + offsite criptografado) | Hoje: apenas Sheet |
| Código/config | GitHub `prefeitura-rio-smas/webapp-rj-smas-sigpar` | Público; sem dados/segredos |
| Frontend | Firebase Hosting (`sigpar.web.app` / `sigpar-staging.web.app`) | Estático |
| Identidade | Firebase Auth (Google) | Allowlist no SQLite |
| Planilha de origem | Google Sheets (SMAS, legado) | ID em env; não versionar PII |

## 2. Classificação

| Classe | Exemplos | Controles |
|---|---|---|
| Público | nomes de unidades, itens de contrato, metas | livre |
| Interno | indicadores de execução, pareceres, textos de análise | autenticação + unidade |
| Pessoal | e-mails/nomes de servidores, autoria de lançamentos | autenticação + unidade; minimização |
| **Sensível (saúde)** | `lancamento_postos.licenca_medica` | **Admin-only**; API/PDF/tela mascarados para os demais; Sheet `Restrito`; binário criptografado no backlog |

- Implementado na F-D5 mínima (2026-11-24): não-admin não lê/grava o campo; edição por não-admin preserva o valor existente.
- Residual: version history do Google Sheet pode conter valores antigos não mascarados até a retenção expirar; binário full/criptografado ainda não existe.

## 3. Papéis (proposta aceita; confirmar DPO)

| Papel | Responsável |
|---|---|
| Controlador | SMAS / Subsecretaria de Gestão (`subg.smas@prefeitura.rio`) |
| Data owner | SMAS/SUBG (nome do subsecretário a confirmar) |
| Data steward | Leone Barreto + Leonardo Meireles |
| Operador técnico | Leone Barreto / equipe de dados |
| Segurança | Leone Barreto |
| DPO/encarregado | encarregado de dados da Prefeitura (contato a confirmar) |
| Access review | Leone Barreto + Leonardo Meireles + Vitor Dantas (`dantasfvitor`) |
| Incidentes | DPO + Leone Barreto + Leonardo Meireles |

## 4. Base legal e finalidade (LGPD)

- Finalidade: monitoramento da execução de parcerias e prestação de contas.
- Base legal: execução de políticas públicas e obrigação legal/regulatória;
  confirmar com o jurídico/DPO para o dado de saúde.
- Minimização: coletar apenas o necessário; não incluir CPF de cidadãos;
  evitar nomes em campos livres.
- Direitos dos titulares: solicitação via SMAS/DPO; correção/registro.
- DPIA do `licenca_medica`: pendente de validação do DPO (F-D6).

## 5. Acesso

| Perfil | Escopo |
|---|---|
| Admin | todas as unidades; exclusão; dado de saúde; NÍVEL CENTRAL |
| Cord | unidades do território + unidade padrão; sem dado de saúde |
| User | própria unidade; sem dado de saúde |
| Técnico (VPS/DB) | acesso operacional mínimo; logs; sem uso de dados para fins pessoais |
| Backup | service account restrita ao Sheet/Drive de backup |

- MFA obrigatório no GitHub, Google e VPS.
- Revisão de acesso trimestral; desativar usuários inativos (`usuarios.ativo`).
- Chaves/segredos em cofres; nunca no repositório.

### 5.1 Access review inicial (F-D6)

- **App**: 96 usuários (19 admin / 10 cord / 67 user); inclui `scan.vulnerabilidade` e `leandro.esquerdo`; revisar ativos/inativos.
- **GitHub**: 9 collaborators (org + Vitor Dantas), repo público, branch protection e environment de produção.
- **VPS**: `root`, `sigpar-prod`, `sigpar-staging`, `sigpar-deploy-prod`, `sigpar-deploy-staging`; chaves SSH e sudoers restritos.
- **Firebase/GCP**: conta `leone.smtr` (owner), WIF, SAs `sigpar-deploy` e `sigpar-backup`.
- **Drive/Sheet**: conta `leone.smtr` + SA de backup.
- Evidência/ações serão registradas em `docs/acesso-revisao.md` (F-D6).

## 6. Retenção (proposta aceita — validar com DPO)

| Dado | Retenção |
|---|---|
| Lançamentos/auditoria | 5 anos (confirmar temporalidade SMAS) |
| Logs de aplicação | 90 dias |
| Backup binário local | 30 dias (backlog F-D5) |
| Backup offsite | 90–365 dias (backlog F-D5) |
| Snapshot Sheet | 12 meses |
| Staging | descartável; dados sintéticos |

RPO atual: 24h (Sheet diário). RTO: 1 dia útil.
Exclusão: soft delete (`status='excluido'`); purga conforme retenção.

## 7. Backup e restore

- **Atual**: snapshot diário no Sheet (timer 03:15 BRT) + restore via `etl/restore_from_sheet.py` (testado).
- O Sheet grava `licenca_medica` como `Restrito`; o restore do Sheet não recupera o valor real.
- Pré-deploy binário local só ocorre via deploy script; não há offsite/criptografia ainda.
- **Backlog F-D5**: binário full criptografado (`age`) + offsite, retenção e teste de restore mensal.
- Acesso ao backup restrito ao operador e ao DPO, quando necessário.

## 8. Segurança

- TLS em todas as pontas; API restrita por Firebase Auth + allowlist.
- API/PDF rodando como usuário dedicado, não root; systemd hardening.
- CORS restrito; validação server-side; SQL parametrizado.
- Segredos em `/etc` (600/640) e GitHub Environments; WIF para GCP.
- Varredura: Gitleaks, CodeQL (repo público), Dependabot, `pip-audit`, Bandit.
- Testes de contrato/segurança com cobertura mínima de 75% no CI; headers de segurança na API.
- Branch protection, environments, revisão de código e de produção.
- Monitoração: uptime externo (GitHub Actions) + healthcheck local (API/backup).
- **Backlog F-D5**: CSP/SRI no frontend e rate limit.

## 9. Incidentes

1. Conter (revogar tokens/chaves, isolar serviço).
2. Preservar logs/evidências (sem expor PII).
3. Avaliar titulares/dados afetados com DPO/SMAS.
4. Comunicar conforme LGPD/política da Prefeitura.
5. Corrigir, testar e registrar post-mortem.

Canal: GitHub Security Advisories + contato do DPO/SMAS.

## 10. Fornecedores e exceções

- Google/Firebase/Drive, GitHub, provedor da VPS.
- **Exceção atual**: projeto Firebase, Drive de backup e VPS sob conta pessoal
  (`leone.smtr@gmail.com`). Riscos: continuidade, DPA, offboarding. Mitigações:
  MFA, least privilege, backup documentado, plano de migração para conta
  institucional quando disponível.
- Preferência futura: Shared Drive do SMAS para backups; conta institucional.

## 11. Dados em CI/staging

- CI usa apenas fixtures sintéticas; nunca produção.
- Staging usa banco sintético; admins de teste (`leone.smtr`, `leone.abreu`); sem dados de produção.
- Logs do Actions são públicos (repo público): não imprimir PII/segredos.

## 12. Catálogo e qualidade

- Dicionário em `docs/modelo-dados.md`; catálogo detalhado em `docs/catalogo-dados.md` (F-D6).
- Reconciliação de contagens/somas na migração e nos deploys.
- `audit_log` para criação/edição/exclusão; revisão periódica.
- Duplicidades unidade+mês são sinalizadas (`duplicado=1`) e revisadas.

## 13. Risco residual aceito (F-D6)

| Risco | Mitigação atual | Owner | Prazo |
|---|---|---|---|
| Binário/offsite criptografado ausente | Sheet diário + restore | Leone | backlog F-D5 |
| CSP/SRI e rate limit ausentes | CORS, auth, TLS | Leone | backlog F-D5 |
| Version history do Sheet com dado antigo | acesso restrito ao Drive | Leone | revisar no F-D5 |
| Conta pessoal Gmail/VPS | MFA, least privilege | Leone | plano de migração |
| VPS única | backups/restore | Leone | monitorar |
| Deploy F-D5 via break-glass (2026-11-26) | backup pré-deploy, health, rollback | Leone | retrospectiva F-D6 |

Aceite formal: data owner/DPO (F-D6). Até lá, este documento registra o estado real e o backlog.

## 14. Aprovação

- **Data owner**: SMAS/SUBG — pendente de assinatura.
- **DPO/encarregado**: Prefeitura — contato/assinatura pendente.
- **Segurança/operação**: Leone Barreto — revisão técnica.
- **Access review**: Leone + Meireles + Vitor — execução no F-D6.

## 15. Documentos relacionados

- `docs/acesso-revisao.md` — revisão de acessos (app, GitHub, VPS, Firebase/Drive).
- `docs/catalogo-dados.md` — catálogo/classificação/retenção por tabela.
- `docs/incidentes.md` — contatos e playbook.
- `docs/riscos.md` — registro de riscos e backlog aceito.
- `docs/governanca-aprovacao.md` — assinaturas e pendências.
- `docs/runbook.md` — operação/rollback/backup/restore.
