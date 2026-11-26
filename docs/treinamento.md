# Treinamento — SIGPAR-SMAS

## Público e objetivo

- **Admin**: cadastros/lançamentos, exclusão, dado de saúde, visão central.
- **Cord/User**: lançamento e consulta da própria unidade/território.
- **Operação/suporte**: health, backup, deploy/rollback e resposta a incidente.

Ao final, a pessoa consegue entrar, lançar/editar/consultar, gerar PDF, reconhecer
duplicidade e escalar um incidente sem expor dados pessoais.

## Antes de começar

- Conta Google autorizada na allowlist (`usuarios.ativo=1`).
- Acesso a `https://sigpar.web.app`.
- Contato do data steward/operação: Leonardo Meireles / Leone Barreto.
- Nunca usar dados reais em issue, chat ou exemplo; o repositório é público.

## Roteiro (60–90 min)

1. **Login e perfil**: entrar com Google, conferir `/me`, unidade padrão e
   unidades permitidas. Explicar Admin/Cord/User.
2. **Lançamento**: escolher unidade e mês; preencher postos, insumos e veículos;
   parecer/classificação; anexos/observações; gerar PDF.
3. **Dado de saúde**: `licenca_medica` é Admin-only; para os demais aparece
   `Restrito` e não é gravado/editado. Explicar por que não se compartilha.
4. **Duplicidade**: aviso 409; confirmar somente com ciência; o campo
   `duplicado` fica registrado para revisão.
5. **Consulta e edição**: lista por unidade/mês/ID; edição; exclusão só Admin
   (soft delete + audit trail).
6. **Erros comuns**: mês inválido, posto/insumo de outra unidade, unidade sem
   permissão, sessão expirada (401), usuário inativo (403).
7. **Operação**: `/health`, backup 03:15, uptime GitHub, healthcheck local,
   rollback e canal de incidente.

## Checklist de aceite

- [ ] Login e `/me` conferidos.
- [ ] Um lançamento de teste criado, consultado, editado e PDF baixado.
- [ ] Tentativa de duplicidade vista e compreendida.
- [ ] Regra de `licenca_medica` explicada e testada com perfil não-admin.
- [ ] Permissão por unidade testada (tentar unidade indevida).
- [ ] Backup/restore e healthcheck local apresentados.
- [ ] Canal de incidente e regra de não expor PII apresentados.

## Evidência

Registrar data, participantes, ambiente (staging/produção) e pendências no
`docs/pendencias.md` ou no issue interno. Não anexar dados reais/prints com PII.

## Contatos

- Data steward: Leonardo Meireles.
- Operação/segurança: Leone Barreto.
- Data owner/DPO: ver `docs/governanca-aprovacao.md`.
