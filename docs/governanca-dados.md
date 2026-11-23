# Governança de dados — SIGPAR-SMAS

> Documento vivo. Revisão obrigatória em mudanças de schema, acesso, retenção,
> fornecedores ou finalidade. Aprovação: SMAS (data owner) + encarregado/DPO.

## 1. Escopo e ativos

| Ativo | Onde vive | Observação |
|---|---|---|
| Banco operacional | SQLite na VPS (`/var/lib/sigpar/sigpar.sqlite`) | Fonte da verdade |
| Snapshot legível | Google Sheets (`SIGPAR - Backup`) | Campos sensíveis mascarados |
| Backup binário | Local criptografado + Google Drive (offsite) | Full, com dado de saúde; criptografado |
| Código/config | GitHub `prefeitura-rio-smas/webapp-rj-smas-sigpar` | Público; sem dados/segredos |
| Frontend | Firebase Hosting (`sigpar.web.app`) | Estático |
| Identidade | Firebase Auth (Google) | Allowlist no SQLite |
| Planilha de origem | Google Sheets (SMAS) | Legado; não versionar ID/PII |

## 2. Classificação

| Classe | Exemplos | Controles |
|---|---|---|
| Público | nomes de unidades, itens de contrato, metas | livre |
| Interno | indicadores de execução, pareceres, textos de análise | autenticação + unidade |
| Pessoal | e-mails/nomes de servidores, autoria de lançamentos | autenticação + unidade; minimização |
| **Sensível (saúde)** | `lancamento_postos.licenca_medica` | **Admin-only**; mascarado no PDF/API para os demais; Sheet mascarado; binário criptografado |

## 3. Papéis

| Papel | Responsável (a confirmar) |
|---|---|
| Controlador | SMAS / Subsecretaria de Gestão |
| Data owner | SMAS/SUBG |
| Data steward | equipe SMAS indicada |
| Operador técnico | Leone Barreto / equipe de dados |
| Segurança | Leone Barreto |
| DPO/encarregado | encarregado de dados da Prefeitura (confirmar canal) |

## 4. Base legal e finalidade (LGPD)

- Finalidade: monitoramento da execução de parcerias e prestação de contas.
- Base legal: execução de políticas públicas e obrigação legal/regulatória;
  confirmar com o jurídico/DPO para o dado de saúde.
- Minimização: coletar apenas o necessário; não incluir CPF de cidadãos;
  evitar nomes em campos livres.
- Direitos dos titulares: solicitação via SMAS/DPO; correção/registro.

## 5. Acesso

| Perfil | Escopo |
|---|---|
| Admin | todas as unidades; exclusão; dado de saúde; NÍVEL CENTRAL |
| Cord | unidades do território + unidade padrão |
| User | própria unidade; sem dado de saúde |
| Técnico (VPS/DB) | acesso operacional mínimo; logs; sem uso de dados para fins pessoais |
| Backup | service account restrita ao Sheet/Drive de backup |

- MFA obrigatório no GitHub, Google e VPS.
- Revisão de acesso trimestral; desativar usuários inativos (`usuarios.ativo`).
- Chaves/segredos em cofres; nunca no repositório.

## 6. Retenção (proposta — validar)

| Dado | Retenção |
|---|---|
| Lançamentos/auditoria | conforme tabela de temporalidade administrativa (proposta: 5 anos) |
| Logs de aplicação | 90 dias |
| Backup binário local | 30 dias |
| Backup offsite | 90–365 dias (definir) |
| Snapshot Sheet | 12 meses (definir) |
| Staging | descartável; dados sintéticos |

RPO proposto: 24h (backup diário) / RTO: 1 dia útil.
Exclusão: soft delete (`status='excluido'`); purga conforme retenção.

## 7. Backup e restore

- Pré-deploy: backup binário + upload criptografado; deploy aborta se falhar.
- Diário: binário local + offsite; snapshot no Sheet.
- Criptografia: `age`; chave privada fora do Drive; cópia em cofre.
- Teste de restore mensal (banco novo + contagens).
- Acesso ao backup restrito ao operador e ao DPO, quando necessário.

## 8. Segurança

- TLS em todas as pontas; API restrita por Firebase Auth + allowlist.
- API/PDF rodando como usuário dedicado, não root; systemd hardening.
- CORS restrito; CSP/SRI; rate limit; validação server-side; SQL parametrizado.
- Segredos em `/etc` (600) e GitHub Environments; WIF para GCP.
- Varredura: Gitleaks, CodeQL (repo público), Dependabot, `pip-audit`, Bandit.
- Branch protection, environments, revisão de código e de produção.

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
- Staging usa banco sintético; sem PII real; usuários de teste.
- Logs do Actions são públicos (repo público): não imprimir PII/segredos.

## 12. Catálogo e qualidade

- Dicionário em `docs/modelo-dados.md`; este documento cobre classificação.
- Reconciliação de contagens/somas na migração e nos deploys.
- `audit_log` para criação/edição/exclusão; revisão periódica.
- Duplicidades unidade+mês são sinalizadas (`duplicado=1`) e revisadas.
