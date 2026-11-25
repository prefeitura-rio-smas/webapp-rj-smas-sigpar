# Incidentes e resposta — SIGPAR-SMAS

## Contatos

| Papel | Contato |
|---|---|
| Segurança/operação | Leone Barreto |
| Data steward | Leonardo Meireles |
| Access review | Vitor Dantas (`dantasfvitor`) |
| DPO/encarregado | encarregado de dados da Prefeitura (contato a confirmar) |
| Data owner | SMAS/SUBG (`subg.smas@prefeitura.rio`) |

## Vetores e contenção

| Cenário | Primeiras ações |
|---|---|
| Vazamento de PII/health | Revogar acessos, preservar logs, avaliar titulares com DPO, comunicar conforme LGPD |
| Token/SSH/SA comprometido | Revogar chave/token, rotacionar, revisar `audit_log`, forçar re-login |
| Deploy malicioso/erro | Rollback do symlink + backup pré-deploy; bloquear workflows |
| Dependência vulnerável | Dependabot/CodeQL/pip-audit; patch + deploy |
| Perda do DB/VPS | Restore do backup (Sheet hoje; binário no backlog F-D5) |

## Playbook

1. **Conter** (acesso, chave, serviço) sem destruir evidências.
2. **Preservar** logs (`journalctl`, `audit_log`, Actions), sem expor PII em issue.
3. **Avaliar** escopo/titulares com DPO/SMAS.
4. **Comunicar** conforme LGPD/política da Prefeitura.
5. **Corrigir**, testar, registrar post-mortem e ação preventiva.

## Canais

- GitHub Security Advisories (private vulnerability reporting) para vulnerabilidades.
- Discord/Issue interno para operação; nunca colar credenciais/PII em canal público.
- O repo é público: issues e logs do Actions são públicos; não incluir PII/segredos.
