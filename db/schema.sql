PRAGMA foreign_keys = ON;

-- ============================================================
-- SIGPAR — schema v1
-- Fonte da verdade: este banco SQLite.
-- IDs legados da planilha são preservados em *_legacy_id.
-- Percentuais/atingimentos são frações 0..1 (ex.: 0.9429 = 94,29%).
-- ============================================================

CREATE TABLE IF NOT EXISTS schema_meta (
  key   TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS itens_contrato (
  id                 INTEGER PRIMARY KEY AUTOINCREMENT,
  codigo             TEXT NOT NULL UNIQUE,   -- "ITEM I do CP-03/2026"
  instituicao        TEXT,
  cnpj               TEXT,
  instrumento        TEXT,
  objeto             TEXT,
  vigencia_inicio    TEXT,
  vigencia_fim       TEXT,
  processo_instrutivo TEXT
);

CREATE TABLE IF NOT EXISTS unidades (
  id                INTEGER PRIMARY KEY AUTOINCREMENT,
  legacy_id         TEXT UNIQUE,             -- ID_unidade da planilha
  nome              TEXT NOT NULL,
  nome_norm         TEXT NOT NULL UNIQUE,
  tipo              TEXT,
  territorio        TEXT,
  item_id           INTEGER REFERENCES itens_contrato(id),
  postos_previstos  REAL NOT NULL DEFAULT 0,
  lanches_previstos REAL NOT NULL DEFAULT 0,
  aluguel           INTEGER NOT NULL DEFAULT 0,
  ativo             INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS usuarios (
  email             TEXT COLLATE NOCASE PRIMARY KEY,
  nome              TEXT,
  perfil            TEXT NOT NULL CHECK (perfil IN ('admin', 'cord', 'user')),
  unidade_padrao_id INTEGER REFERENCES unidades(id),
  territorio        TEXT,
  meta              REAL NOT NULL DEFAULT 0,
  ativo             INTEGER NOT NULL DEFAULT 1,
  criado_em         TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
  atualizado_em     TEXT
);

CREATE TABLE IF NOT EXISTS postos (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  legacy_id  TEXT UNIQUE,                    -- ID_posto da planilha
  unidade_id INTEGER NOT NULL REFERENCES unidades(id),
  nome       TEXT NOT NULL,
  ordem      INTEGER,
  ativo      INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX IF NOT EXISTS idx_postos_unidade ON postos(unidade_id, ordem, id);

CREATE TABLE IF NOT EXISTS insumos (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  legacy_id    TEXT UNIQUE,                  -- ID_insumos
  tipo_unidade TEXT NOT NULL,
  subitem      TEXT,
  descricao    TEXT NOT NULL,
  previsao     REAL,
  ordem        INTEGER,
  ativo        INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX IF NOT EXISTS idx_insumos_tipo ON insumos(tipo_unidade, ordem, id);

CREATE TABLE IF NOT EXISTS kit_operacional (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  legacy_id    TEXT UNIQUE,                  -- ID_operacional
  tipo_unidade TEXT NOT NULL,
  subitem      TEXT,
  descricao    TEXT NOT NULL,
  previsao     REAL,
  ordem        INTEGER,
  ativo        INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX IF NOT EXISTS idx_kit_tipo ON kit_operacional(tipo_unidade, ordem, id);

CREATE TABLE IF NOT EXISTS veiculos (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  unidade_id INTEGER NOT NULL REFERENCES unidades(id),
  nome       TEXT NOT NULL,
  quantidade REAL,
  UNIQUE (unidade_id, nome)
);

CREATE TABLE IF NOT EXISTS avaliacoes_servico (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  unidade_id     INTEGER NOT NULL REFERENCES unidades(id),
  criterio       TEXT NOT NULL,
  media          REAL,
  satisfacao     REAL,
  referencia_mes TEXT NOT NULL,             -- YYYY-MM-01
  UNIQUE (unidade_id, criterio, referencia_mes)
);

CREATE TABLE IF NOT EXISTS lancamentos (
  id                    INTEGER PRIMARY KEY AUTOINCREMENT,
  legacy_id             TEXT UNIQUE,         -- ID_Lancamento (LANC-...)
  unidade_id            INTEGER NOT NULL REFERENCES unidades(id),
  unidade_nome          TEXT NOT NULL,       -- snapshot histórico
  tipo_unidade          TEXT,                -- snapshot histórico
  item_contrato         TEXT,                -- snapshot histórico
  referencia_mes        TEXT NOT NULL,       -- YYYY-MM-01
  autor_email           TEXT NOT NULL,
  criado_em             TEXT NOT NULL,       -- YYYY-MM-DD HH:MM:SS (America/Sao_Paulo)
  atualizado_em         TEXT,
  atualizado_por        TEXT,
  parecer_opcao         TEXT,
  parecer_codigo        TEXT,                -- atestar | atestar_ressalva | nao_atestar
  observacoes           TEXT,
  descricao_atividades  TEXT,
  analise_atividades    TEXT,
  classificacao         TEXT,                -- Plenamente | Parcialmente | Regular | Insatisfatório | ''
  lanches_previsto      REAL NOT NULL DEFAULT 0,
  lanches_executado     REAL,
  postos_total          REAL NOT NULL DEFAULT 0,
  postos_ocupados       REAL NOT NULL DEFAULT 0,
  insumos_percentual    REAL,                -- fração 0..1
  veiculos_detalhe      TEXT,                -- "N/A" ou "Veículo: Exec x/Prev | ..."
  duplicado             INTEGER NOT NULL DEFAULT 0,
  status                TEXT NOT NULL DEFAULT 'ativo' CHECK (status IN ('ativo', 'excluido')),
  created_at            TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
  updated_at            TEXT
);
CREATE INDEX IF NOT EXISTS idx_lanc_unidade_mes ON lancamentos(unidade_id, referencia_mes);
CREATE INDEX IF NOT EXISTS idx_lanc_mes ON lancamentos(referencia_mes);
CREATE INDEX IF NOT EXISTS idx_lanc_autor ON lancamentos(autor_email);
CREATE INDEX IF NOT EXISTS idx_lanc_status ON lancamentos(status);

CREATE TABLE IF NOT EXISTS lancamento_postos (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  lancamento_id  INTEGER NOT NULL REFERENCES lancamentos(id) ON DELETE CASCADE,
  posto_id       INTEGER REFERENCES postos(id),
  posto_nome     TEXT,
  ocupado        INTEGER NOT NULL DEFAULT 0,
  desempenho     TEXT,
  licenca_medica TEXT,
  UNIQUE (lancamento_id, posto_id)
);
CREATE INDEX IF NOT EXISTS idx_lpostos_lanc ON lancamento_postos(lancamento_id);

CREATE TABLE IF NOT EXISTS lancamento_insumos (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  lancamento_id INTEGER NOT NULL REFERENCES lancamentos(id) ON DELETE CASCADE,
  insumo_id     INTEGER REFERENCES insumos(id),
  subitem       TEXT,
  descricao     TEXT,
  previsto      REAL,
  executado     REAL,
  atingimento   REAL,                        -- fração 0..1
  UNIQUE (lancamento_id, insumo_id)
);
CREATE INDEX IF NOT EXISTS idx_linsumos_lanc ON lancamento_insumos(lancamento_id);

CREATE TABLE IF NOT EXISTS lancamento_veiculos (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  lancamento_id INTEGER NOT NULL REFERENCES lancamentos(id) ON DELETE CASCADE,
  veiculo_id    INTEGER REFERENCES veiculos(id),
  nome          TEXT,
  previsto      REAL,
  executado     REAL,
  UNIQUE (lancamento_id, veiculo_id)
);

CREATE TABLE IF NOT EXISTS lancamento_lanches (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  lancamento_id INTEGER NOT NULL REFERENCES lancamentos(id) ON DELETE CASCADE,
  periodo       TEXT NOT NULL DEFAULT 'Mensal Integral',
  previsto      REAL,
  executado     REAL,
  atingimento   REAL,                        -- fração 0..1
  UNIQUE (lancamento_id, periodo)
);

CREATE TABLE IF NOT EXISTS lancamento_kit (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  lancamento_id INTEGER NOT NULL REFERENCES lancamentos(id) ON DELETE CASCADE,
  item          TEXT NOT NULL,
  quantitativo  REAL,
  conformidade  TEXT,
  percentual    REAL,
  obs           TEXT,
  UNIQUE (lancamento_id, item)
);

CREATE TABLE IF NOT EXISTS lancamento_locacao (
  id                     INTEGER PRIMARY KEY AUTOINCREMENT,
  lancamento_id          INTEGER NOT NULL REFERENCES lancamentos(id) ON DELETE CASCADE,
  unidade_locacao        TEXT,
  dias_corridos          REAL,
  controle_regularizacao TEXT,
  nota                   TEXT,
  data_autorizo          TEXT
);

CREATE TABLE IF NOT EXISTS avaliacao_central (
  lancamento_id         INTEGER PRIMARY KEY REFERENCES lancamentos(id) ON DELETE CASCADE,
  perfil_meta           REAL,
  nota1                 REAL,  -- CSIMAS Cap. Contratação
  nota2                 REAL,  -- CSIMAS Adimplência
  nota3                 REAL,  -- COP Insumos
  nota4                 REAL,  -- COP Veículos
  nota5                 REAL,  -- CIN Aluguéis
  nota6                 REAL,  -- CCPAR Prestação
  nota7                 REAL,  -- CCPAR Diligência
  nota8                 REAL,  -- CSIMAS Ergon
  nota9                 REAL,  -- COP Motoristas
  nota10                REAL,  -- CCPAR SIAFIC
  nota11                REAL,  -- CCPAR Osinfo
  obs_nutricionista     TEXT
);

CREATE TABLE IF NOT EXISTS audit_log (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  ator_email  TEXT,
  acao        TEXT NOT NULL,
  entidade    TEXT NOT NULL,
  entidade_id TEXT,
  antes_json  TEXT,
  depois_json TEXT,
  em          TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);
CREATE INDEX IF NOT EXISTS idx_audit_entidade ON audit_log(entidade, entidade_id);
CREATE INDEX IF NOT EXISTS idx_audit_em ON audit_log(em);

CREATE TABLE IF NOT EXISTS backup_runs (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  started_at  TEXT NOT NULL,
  finished_at TEXT,
  status      TEXT NOT NULL,                 -- running | ok | erro
  sheet_id    TEXT,
  detalhe     TEXT,
  erro        TEXT
);

-- ============================================================
-- Views
-- ============================================================

-- Unidades que cada usuário pode ver, reproduzindo a regra atual:
-- admin: todas; cord: unidades do território da unidade padrão + a própria;
-- user: apenas a unidade padrão.
CREATE VIEW IF NOT EXISTS vw_unidades_permitidas AS
SELECT
  u.email,
  un.id       AS unidade_id,
  un.nome,
  un.tipo,
  un.territorio
FROM usuarios u
JOIN unidades un
  ON un.ativo = 1
 AND (
      u.perfil = 'admin'
   OR (u.perfil = 'cord' AND (
         un.id = u.unidade_padrao_id
      OR (un.territorio IS NOT NULL
          AND un.territorio = (SELECT u2.territorio FROM unidades u2 WHERE u2.id = u.unidade_padrao_id))
      ))
   OR (u.perfil = 'user' AND un.id = u.unidade_padrao_id)
 )
WHERE u.ativo = 1;

CREATE VIEW IF NOT EXISTS vw_lancamentos AS
SELECT l.*, u.nome AS unidade_atual_nome, u.tipo AS unidade_atual_tipo
FROM lancamentos l
JOIN unidades u ON u.id = l.unidade_id
WHERE l.status = 'ativo';

CREATE VIEW IF NOT EXISTS vw_lancamento_resumo AS
SELECT
  l.id,
  l.legacy_id,
  l.unidade_id,
  l.unidade_nome,
  l.referencia_mes,
  l.autor_email,
  l.criado_em,
  l.duplicado,
  l.postos_total,
  l.postos_ocupados,
  CASE WHEN l.postos_total > 0
       THEN CAST(l.postos_ocupados AS REAL) / l.postos_total END AS postos_pct,
  l.lanches_previsto,
  l.lanches_executado,
  CASE WHEN l.lanches_previsto > 0
       THEN CAST(l.lanches_executado AS REAL) / l.lanches_previsto END AS lanches_pct,
  l.insumos_percentual,
  (SELECT COUNT(*) FROM lancamento_postos p WHERE p.lancamento_id = l.id) AS qtd_postos,
  (SELECT COUNT(*) FROM lancamento_insumos i WHERE i.lancamento_id = l.id) AS qtd_insumos,
  (SELECT COUNT(*) FROM lancamento_kit k WHERE k.lancamento_id = l.id) AS qtd_kit
FROM lancamentos l
WHERE l.status = 'ativo';

INSERT OR IGNORE INTO schema_meta(key, value) VALUES ('app', 'sigpar');
INSERT OR IGNORE INTO schema_meta(key, value) VALUES ('version', '1');
