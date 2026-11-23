# Modelo de dados — SQLite v1

Fonte: planilha `SMAS - SISTEMA DE MONITORAMENTO DE METAS`
(ID em `SIGPAR_SOURCE_SHEET_ID`, 17 abas).

## Cadastros

| Tabela | Origem | Volume atual |
|---|---|---|
| `itens_contrato` | `Item` | 7 |
| `unidades` | `Unidades` | 86 |
| `usuarios` | `Responsaveis` | 95 (18 Admin, 10 Cord, 67 User) |
| `postos` | `Postos` | 1.260 |
| `insumos` | `Insumos` | 196 |
| `kit_operacional` | `Operacional` | 20 |
| `veiculos` | `Veiculos` | 2 |
| `avaliacoes_servico` | `Avaliacao` | 6 |

## Transacional

| Tabela | Origem | Volume atual |
|---|---|---|
| `lancamentos` | `Historico_Lancamentos` | 83 |
| `lancamento_postos` | `Ocupacao_Postos` | 1.237 |
| `lancamento_insumos` | `Registro_Insumos` | 4.787 |
| `lancamento_veiculos` | (derivado de `Veiculos_Detalhe`) | — |
| `lancamento_lanches` | `Registro_Lanches` | 60 |
| `lancamento_kit` | `Composicao_Kit_Nutricionista` | 407 |
| `lancamento_locacao` | `Registro_Locacao` | 3 |
| `avaliacao_central` | `Avaliacao_Central` | 1 |

Descartada: `Lancamentos` (resumo redundante do `Historico`).

## Relações

```
itens_contrato 1─N unidades
unidades 1─N postos
unidades 1─N veiculos
unidades 1─N lancamentos
unidades 1─N avaliacoes_servico
lancamentos 1─N lancamento_postos
lancamentos 1─N lancamento_insumos
lancamentos 1─N lancamento_veiculos
lancamentos 1─N lancamento_lanches
lancamentos 1─N lancamento_kit
lancamentos 1─N lancamento_locacao
lancamentos 1─1 avaliacao_central
```

## Estado após a F2 (banco real)

- `unidades`: 86
- `usuarios`: 96 (94 e-mails únicos da planilha + 2 admins técnicos)
- `postos`: 1.260
- `insumos`: 196
- `kit_operacional`: 19 (a linha 21 da planilha, com ID repetido e descrição vazia, foi ignorada)
- `veiculos`: 2
- `avaliacoes_servico`: 6
- `lancamentos`: 83 (17 marcados com `duplicado=1` em 8 combinações unidade+mês)
- `lancamento_postos`: 1.237 (0 sem vínculo)
- `lancamento_insumos`: 4.787 (0 sem vínculo)
- `lancamento_lanches`: 60
- `lancamento_kit`: 407
- `lancamento_locacao`: 3
- `avaliacao_central`: 1
- `lancamento_veiculos`: 0 (por design; histórico usa `veiculos_detalhe`)

Relatório: `docs/migracao-relatorio.md`.

## Regras de autorização (view `vw_unidades_permitidas`)

- **admin**: todas as unidades ativas.
- **cord**: unidades do território da unidade padrão + a própria unidade padrão.
- **user**: apenas a unidade padrão.

## Normalizações da migração

- `Referencia_Mes` (data ou texto) → `YYYY-MM-01`.
- `ID_Lancamento`, `ID_posto`, `ID_insumos`, `ID_operacional` → `legacy_id`.
- Nomes de unidade: `nome_norm` = trim + minúsculas + espaços colapsados (para casar com o app antigo).
- Percentuais: fração `0..1` (ex.: `0,9429`).
- `Parecer_Comissao.Opcao_Parecer` → `parecer_opcao` + `parecer_codigo`:
  - contém `COM RESSALVA` → `atestar_ressalva`
  - contém `NÃO ATESTAR`/`NAO ATESTAR` → `nao_atestar`
  - contém `ATESTAR` → `atestar`
- `Classificacao_Analise`: `Pleno` → `Plenamente`; `Parcial` → `Parcialmente`.
- `Atualizado_Por`/`Data_Hora_Atualizacao` → `atualizado_por`/`atualizado_em`.
- Duplicidades unidade+mês existentes: importar com `duplicado=1`; novas exigem confirmação.

## Pendências de entendimento

- `Avaliacao` (6 linhas, NÍVEL CENTRAL) vs `Avaliacao_Central` (11 notas por lançamento): confirmar se as duas devem coexistir.
- `Postos` tem linhas repetidas por unidade (provavelmente slots); preservar `legacy_id` por linha.
- `Historico_Lancamentos` tem 850 linhas vazias no range (formatação); ignorar.
