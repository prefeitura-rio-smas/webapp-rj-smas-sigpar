# Catálogo de dados — SIGPAR-SMAS

Fonte da verdade: SQLite `/var/lib/sigpar/prod/sigpar.sqlite`
(schema em `db/schema.sql` + migrações em `db/migrations`).

## Classificação e retenção

| Tabela | Conteúdo | Classe | Retenção |
|---|---|---|---|
| `itens_contrato` | contratos/instituições | Público/Interno | enquanto vigente |
| `unidades` | unidades, tipo, território | Público | enquanto ativa |
| `usuarios` | e-mail, nome, perfil, meta | Pessoal | enquanto ativo + 5 anos |
| `postos` | catálogo de postos | Interno | enquanto ativo |
| `insumos` | catálogo de insumos | Interno | enquanto ativo |
| `kit_operacional` | catálogo de kit | Interno | enquanto ativo |
| `veiculos` | catálogo de veículos | Interno | enquanto ativo |
| `avaliacoes_servico` | avaliações de serviço | Interno | 5 anos |
| `lancamentos` | cabeçalho do lançamento mensal | Interno | 5 anos |
| `lancamento_postos` | ocupação/desempenho/**licença médica** | Pessoal/**Sensível (saúde)** | 5 anos |
| `lancamento_insumos` | execução de insumos | Interno | 5 anos |
| `lancamento_veiculos` | execução de veículos | Interno | 5 anos |
| `lancamento_lanches` | execução de lanches | Interno | 5 anos |
| `lancamento_kit` | composição do kit | Interno | 5 anos |
| `lancamento_locacao` | locação/regularização | Interno | 5 anos |
| `avaliacao_central` | notas centrais | Interno | 5 anos |
| `audit_log` | autoria de criação/edição/exclusão | Pessoal | 5 anos |
| `backup_runs` | execuções de backup | Interno | 90 dias |
| `schema_meta` | versão do schema | Interno | permanente |

## Campos sensíveis

- `lancamento_postos.licenca_medica`: **dado de saúde**; Admin-only; mascarado como `Restrito` na API/PDF/tela para não-admin e no snapshot do Sheet; binário full criptografado é backlog F-D5.
- `usuarios.email`, `lancamentos.autor_email`, `audit_log.ator_email`: dados pessoais; acesso autenticado e restrito por unidade/perfil.
- `lancamentos.observacoes`/`descricao_atividades`/`analise_atividades`: texto livre; pode conter nomes/PII; orientar preenchimento sem PII desnecessária.

## Dados derivados

- `vw_unidades_permitidas`: permissões por perfil (admin/cord/user).
- `vw_lancamentos`, `vw_lancamento_resumo`: consulta e totais; não são fonte.
- `lancamento_veiculos`: vazio por design no legado; `veiculos_detalhe` guarda o texto.

## Fora do banco

- **Sheet de origem** (legado SMAS): PII; não versionar ID; acesso restrito.
- **Sheet de backup**: snapshot legível; `licenca_medica` mascarado; acesso restrito.
- **CI/staging**: dados sintéticos; sem PII de produção.
- **Repository**: público; sem dados/segredos.
