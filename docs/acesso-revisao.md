# Revisão de acessos — SIGPAR-SMAS

Data: 2026-11-25
Revisores: Leone Barreto, Leonardo Meireles, Vitor Dantas (`dantasfvitor`)

## 1. Aplicação (SQLite de produção)

- **96 usuários**, todos ativos (`usuarios.ativo=1`): **19 Admin**, **10 Cord**, **67 User**.
- **Admins (19)**: `ccpar`, `contas`, `cop`, `cpgof`, `csa`, `csimas`, `demandas`, `gacp`, `gadl`, `gpcof`, `gpmp`, `leandro.esquerdo`, `leone.abreu`, `leone.smtr`, `planejamento`, `scan.vulnerabilidade`, `subg`, `subpsb`, `subpse` (todos `@prefeitura.rio`, exceto `leone.smtr@gmail.com`).
- **Cord (10) / User (67)**: escopo por território/unidade, conforme `vw_unidades_permitidas`.
- **Ações/observações**:
  - `scan.vulnerabilidade@prefeitura.rio`: conta de scanner; confirmar com o owner se deve permanecer Admin.
  - `leandro.esquerdo@prefeitura.rio`: Admin SMAS; confirmar necessidade.
  - `leone.smtr@gmail.com` e `leone.abreu@prefeitura.rio`: admins técnicos; manter com MFA.
  - `subg`/`subpse`/`subpsb`: contas institucionais das subsecretarias; manter.
  - Sem usuários inativos na base; revisão trimestral recomendada.

## 2. GitHub (`prefeitura-rio-smas/webapp-rj-smas-sigpar`)

- **9 collaborators**: `leonebar`, `meirelesleonardo`, `dantasfvitor`, `ssaulolopes`, `mariacfalcao`, `enzostana`, `luisamartins26`, `camilarocha27`, `VivianeBueno`.
- Repo **público**; `main`/`staging` protegidas; environment `production` com 2 revisores e bypass de admin.
- Ação: revisar se todos precisam de write; MFA obrigatório; remover acessos ao sair da equipe.

## 3. VPS

- Usuários: `root`, `sigpar-prod`, `sigpar-staging` (nologin), `sigpar-deploy-prod`, `sigpar-deploy-staging` (shell restrito por forced command).
- Chaves SSH dos deploy em `authorized_keys` com `command="/usr/local/bin/sigpar-deploy"`; sudoers restrito a inner/restart.
- Ação: rotação de chaves na saída de pessoas; MFA/SSH key-only; revisar `sudoers` a cada mudança.

## 4. Firebase / GCP / Drive

- Firebase Auth: 2 usuários reais (`leone.smtr@gmail.com`, `subg.smas@prefeitura.rio`). Os usuários de teste `auth-test@example.com`/`auth-test2@example.com` foram **removidos em 2026-11-25**.
- Service accounts: `sigpar-deploy` (WIF, Hosting) e `sigpar-backup` (Sheet/Drive).
- Drive/Sheet: conta `leone.smtr` (owner) + SA de backup; acesso ao Sheet restrito.
- Ação: manter WIF (sem chave de SA no GitHub); rotacionar a chave da `sigpar-backup`; documentar a exceção de conta pessoal no risk register.

## 5. Evidências

- Consultas em `usuarios` (perfil/ativo), `gh api repos/.../collaborators`, `getent passwd`, `identitytoolkit accounts:batchGet`, `systemctl`/`sudoers`.
- Resultado: nenhum acesso anômalo; 2 contas de teste removidas; pendências de confirmação com o data owner.

## 6. Assinaturas

- Leone Barreto: revisado
- Leonardo Meireles: pendente
- Vitor Dantas: pendente
