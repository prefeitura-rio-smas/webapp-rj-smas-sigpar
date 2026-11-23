from app.pdf import render_pdf


def test_pdf_smoke():
    data = {
        "lancamento": {
            "id": 1,
            "legacy_id": "LANC-TESTE",
            "unidade_nome": "Unidade Teste",
            "tipo_unidade": "CRAS",
            "item_contrato": "ITEM I",
            "referencia_mes": "2026-01-01",
            "autor_email": "teste@example.com",
            "criado_em": "2026-01-01 10:00:00",
            "atualizado_em": None,
            "atualizado_por": None,
            "parecer_opcao": "ATESTAR a regularidade da prestação dos serviços.",
            "observacoes": "Sem observações.",
            "descricao_atividades": "Atividades de teste.",
            "analise_atividades": "Análise de teste.",
            "classificacao": "Plenamente",
            "postos_total": 2,
            "postos_ocupados": 1,
            "lanches_previsto": 100,
            "lanches_executado": 90,
            "insumos_percentual": 0.9,
            "veiculos_detalhe": "N/A",
        },
        "unidade": {"nome": "Unidade Teste", "territorio": "01ªCAS"},
        "item": None,
        "autor_perfil": "admin",
        "postos": [
            {
                "posto_id": 1,
                "posto_nome": "Assistente Social",
                "ocupado": 1,
                "desempenho": "Satisfatório",
                "licenca_medica": "Restrito",
            }
        ],
        "insumos": [
            {
                "insumo_id": 1,
                "subitem": "Material de Limpeza",
                "descricao": "Água sanitária",
                "previsto": 10,
                "executado": 9,
                "atingimento": 0.9,
            }
        ],
        "veiculos": [],
        "lanches": [
            {
                "periodo": "Mensal Integral",
                "previsto": 100,
                "executado": 90,
                "atingimento": 0.9,
            }
        ],
        "kit": [],
        "locacao": [],
        "avaliacao_central": None,
    }
    pdf = render_pdf(data)
    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 1000
