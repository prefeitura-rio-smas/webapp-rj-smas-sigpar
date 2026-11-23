# Relatório de migração — SIGPAR

Gerado em: 2026-11-20 15:02:52 (America/Sao_Paulo)

## Contagens

| Origem | Planilha | SQLite |
|---|---:|---:|
| Item | 7 | 7 |
| Unidades | 86 | 86 |
| Responsaveis | 95 | 96 ⚠ |
| Postos | 1260 | 1260 |
| Insumos | 196 | 196 |
| Operacional | 20 | 19 ⚠ |
| Veiculos | 2 | 2 |
| Avaliacao | 6 | 6 |
| Historico_Lancamentos | 83 | 83 |
| Ocupacao_Postos | 1237 | 1237 |
| Registro_Insumos | 4787 | 4787 |
| Registro_Lanches | 60 | 60 |
| Composicao_Kit_Nutricionista | 407 | 407 |
| Registro_Locacao | 3 | 3 |
| Avaliacao_Central | 1 | 1 |

## Somas do histórico

| Campo | Planilha | SQLite |
|---|---:|---:|
| postos_total | 1237.00 | 1237.00 |
| postos_ocupados | 1090.00 | 1090.00 |
| lanches_previsto | 73360.00 | 73360.00 |
| lanches_executado | 62952.00 | 62952.00 |

## Notas

- `usuarios` inclui 2 admins técnicos além dos 94 e-mails únicos da planilha.
- `lancamento_veiculos` fica vazio por design: o histórico usa o texto `veiculos_detalhe` (a planilha não tem detalhe por veículo).
- A linha 21 de `Operacional` (ID repetido, descrição vazia) é ignorada; ver avisos.

## Avisos

- Responsaveis: um e-mail duplicado na planilha (omitido)
- Operacional: linha ignorada (id='6zbyhvwk', descricao='')
