# Segurança

## Como reportar

Use **GitHub Security Advisories → Report a vulnerability** neste repositório
(Private vulnerability reporting). Não abra issue pública com detalhes de
vulnerabilidade, credenciais, dados pessoais ou prints com PII.

## Escopo

- API FastAPI e banco SQLite na VPS;
- frontend em `sigpar.web.app`;
- Firebase Authentication / Hosting;
- scripts de ETL, backup e deploy;
- workflows do GitHub Actions.

## O que esperamos

- Descrição do impacto e passos de reprodução;
- versão/commit afetado;
- sugestão de correção, se houver.

## Compromissos

- Confirmação de recebimento e triagem inicial;
- correção priorizada conforme severidade;
- crédito ao reporter, se desejado.

## Fora de escopo

- Engenharia social, phishing ou testes em contas de terceiros;
- testes que exponham dados reais de servidores/cidadãos;
- negação de serviço contra produção.

## Boas práticas para contribuidores

- Nunca commitar segredos, chaves, tokens, DBs, planilhas ou dados pessoais.
- Usar dados sintéticos em testes e staging.
- Seguir `docs/governanca-dados.md` e o template de PR.
