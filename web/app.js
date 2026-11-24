/* SIGPAR-SMAS — frontend F3 */
const firebaseConfig = {
  apiKey: "AIzaSyA2Yv8ZXiQKJMUDRdRqbzrIWGR68HEMGqA",
  authDomain: "sigpar-smas.firebaseapp.com",
  projectId: "sigpar-smas",
  storageBucket: "sigpar-smas.firebasestorage.app",
  messagingSenderId: "1073163291626",
  appId: "1:1073163291626:web:3a7c9e9c31f62d57b50093"
};

const API_BASE = location.hostname.startsWith("sigpar-staging.")
  ? "https://sigpar-staging.152.53.195.232.nip.io"
  : (location.hostname.endsWith(".web.app") || location.hostname.endsWith(".firebaseapp.com"))
    ? "https://sigpar.152.53.195.232.nip.io"
    : "http://127.0.0.1:3103";

const state = {
  me: null,
  ctx: null,
  detail: null,
  editId: null,
  lastPdf: null,
  temLanches: false
};

const $ = (id) => document.getElementById(id);
const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (m) => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;"
}[m]));
const escAttr = (v) => esc(v).replace(/"/g, "&quot;");
const num = (v) => {
  if (v === "" || v === null || v === undefined) return null;
  const n = Number(String(v).replace(",", "."));
  return Number.isFinite(n) ? n : null;
};

firebase.initializeApp(firebaseConfig);
const auth = firebase.auth();

function setStatus(msg) { $("statusMsg").textContent = msg || ""; }
function setFormStatus(msg, erro = false) {
  const el = $("formStatus");
  el.textContent = msg || "";
  el.className = "small " + (erro ? "text-danger" : "text-success");
}

async function api(path, options = {}) {
  const user = auth.currentUser;
  if (!user) throw new Error("não autenticado");
  const token = await user.getIdToken(true);
  const headers = { ...(options.headers || {}), Authorization: "Bearer " + token };
  const resp = await fetch(API_BASE + path, { ...options, headers });
  const text = await resp.text();
  let data = null;
  try { data = text ? JSON.parse(text) : null; } catch { data = text; }
  if (!resp.ok) {
    const err = new Error("HTTP " + resp.status);
    err.status = resp.status;
    err.data = data;
    throw err;
  }
  return data;
}

async function apiJson(path, options = {}) {
  return api(path, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) }
  });
}

async function baixarPdf(id) {
  try {
    const user = auth.currentUser;
    if (!user) return;
    const token = await user.getIdToken(true);
    const resp = await fetch(`${API_BASE}/lancamentos/${id}/pdf`, {
      headers: { Authorization: "Bearer " + token }
    });
    if (!resp.ok) throw new Error("HTTP " + resp.status);
    const blob = await resp.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `Relatorio_${id}.pdf`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 5000);
  } catch (e) {
    setFormStatus("Falha ao baixar PDF: " + e.message, true);
  }
}

function mostrarPdf(id) {
  state.lastPdf = id;
  ["btnPdfTop", "btnPdf"].forEach((k) => $(k).classList.remove("hidden"));
}

function esconderPdf() {
  state.lastPdf = null;
  ["btnPdfTop", "btnPdf"].forEach((k) => $(k).classList.add("hidden"));
}

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------
async function entrar() {
  const provider = new firebase.auth.GoogleAuthProvider();
  provider.setCustomParameters({ prompt: "select_account" });
  try {
    await auth.signInWithPopup(provider);
  } catch (e) {
    console.warn("popup falhou, usando redirect", e);
    await auth.signInWithRedirect(provider);
  }
}

async function carregarMe() {
  const me = await apiJson("/me");
  state.me = me;
  $("userEmail").textContent = me.email;
  $("btnLogout").classList.remove("hidden");
  $("loginCard").classList.add("hidden");
  $("appArea").classList.remove("hidden");
  preencherUnidades(me.unidades_permitidas || []);
  loadRecent();
}

function preencherUnidades(unidades) {
  const sel = $("selUnidade");
  sel.innerHTML = "";
  const lista = [...unidades].sort((a, b) => a.nome.localeCompare(b.nome, "pt-BR"));
  for (const u of lista) {
    const opt = document.createElement("option");
    opt.value = u.unidade_id;
    opt.textContent = u.nome;
    sel.appendChild(opt);
  }
  const pref = state.me?.unidade_padrao_id;
  if (pref && lista.some((u) => u.unidade_id === pref)) sel.value = String(pref);
  if (!$("inpMes").value) {
    const now = new Date();
    $("inpMes").value = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
  }
  carregarContexto();
}

// ---------------------------------------------------------------------------
// Contexto e render
// ---------------------------------------------------------------------------
async function carregarContexto() {
  const unidadeId = Number($("selUnidade").value);
  const mes = $("inpMes").value;
  if (!unidadeId || !mes) {
    setStatus("Selecione a unidade e o mês.");
    return;
  }
  try {
    setStatus("Carregando unidade...");
    state.ctx = await apiJson(`/unidades/${unidadeId}/contexto`);
    renderForm();
    setStatus("");
  } catch (e) {
    setStatus("Erro ao carregar: " + (e.data?.detail || e.message));
  }
}

function renderForm() {
  const ctx = state.ctx;
  if (!ctx) return;
  $("form").classList.remove("hidden");
  renderInfo();
  renderLanches();
  renderPostos();
  renderInsumos();
  renderVeiculos();
  renderKit();
  renderCentral();
  preencherCabecalho(state.detail);
}

function renderInfo() {
  const u = state.ctx.unidade;
  const item = state.ctx.item;
  $("infoUnidade").innerHTML = `
    <div class="col-md-4"><b>Unidade</b><br>${esc(u.nome)}</div>
    <div class="col-md-2"><b>Tipo</b><br>${esc(u.tipo || "-")}</div>
    <div class="col-md-3"><b>Território</b><br>${esc(u.territorio || "-")}</div>
    <div class="col-md-3"><b>Item do contrato</b><br>${esc(item?.codigo || "-")}</div>
    <div class="col-12"><b>Instituição</b><br>${esc(item?.instituicao || "-")}</div>
    ${item?.objeto ? `<div class="col-12"><b>Objeto</b><br><span class="muted">${esc(item.objeto)}</span></div>` : ""}
  `;
}

function renderLanches() {
  const u = state.ctx.unidade;
  const detalhe = state.detail?.lanches || [];
  const tem = (u.lanches_previstos || 0) > 0 || detalhe.length > 0;
  state.temLanches = tem;
  $("secLanches").classList.toggle("hidden", !tem);
  if (tem) {
    const l = detalhe[0] || {};
    $("inpLanchesPrev").value = l.previsto ?? u.lanches_previstos ?? "";
    $("inpLanchesExec").value = l.executado ?? "";
  }
}

function renderPostos() {
  const tbody = $("tbodyPostos");
  const postos = state.ctx.postos || [];
  if (!postos.length) {
    tbody.innerHTML = '<tr><td colspan="4" class="text-muted">Sem postos cadastrados.</td></tr>';
    return;
  }
  const detalhe = new Map((state.detail?.postos || []).map((p) => [p.posto_id, p]));
  const admin = state.me?.perfil === "admin";
  tbody.innerHTML = postos.map((p) => {
    const d = detalhe.get(p.id) || {};
    const ocupado = d.ocupado ? "checked" : "";
    const desempenho = d.desempenho || "Satisfatório";
    const licenca = d.licenca_medica || "Não";
    const licencaCell = admin
      ? `<select class="form-select form-select-sm sel-licenca">
        <option value="-">-</option><option value="Sim"${licenca === "Sim" ? " selected" : ""}>Sim</option>
        <option value="Não"${licenca === "Não" ? " selected" : ""}>Não</option></select>`
      : `<span class="text-muted">Restrito</span>`;
    return `<tr data-posto-id="${p.id}">
      <td>${esc(p.nome)}</td>
      <td class="text-center"><input type="checkbox" class="form-check-input chk-ocupado" ${ocupado}></td>
      <td>${licencaCell}</td>
      <td><select class="form-select form-select-sm sel-desempenho">
        <option value="-">-</option>
        <option value="Satisfatório"${desempenho === "Satisfatório" ? " selected" : ""}>Satisfatório</option>
        <option value="Parcialmente satisfatório"${desempenho === "Parcialmente satisfatório" ? " selected" : ""}>Parcialmente satisfatório</option>
        <option value="Insatisfatório"${desempenho === "Insatisfatório" ? " selected" : ""}>Insatisfatório</option>
      </select></td></tr>`;
  }).join("");
  tbody.querySelectorAll("tr[data-posto-id]").forEach((tr) => {
    const chk = tr.querySelector(".chk-ocupado");
    chk.addEventListener("change", () => syncPosto(tr));
    syncPosto(tr);
  });
}

function syncPosto(tr) {
  const chk = tr.querySelector(".chk-ocupado");
  const lic = tr.querySelector(".sel-licenca");
  const des = tr.querySelector(".sel-desempenho");
  if (!chk || !des) return;
  if (lic) lic.disabled = !chk.checked;
  des.disabled = !chk.checked;
  if (!chk.checked) {
    if (lic) lic.value = "-";
    des.value = "-";
  } else {
    if (lic && lic.value === "-") lic.value = "Não";
    if (des.value === "-") des.value = "Satisfatório";
  }
}

function renderInsumos() {
  const tbody = $("tbodyInsumos");
  const insumos = state.ctx.insumos || [];
  if (!insumos.length) {
    tbody.innerHTML = '<tr><td colspan="4" class="text-muted">Sem insumos cadastrados para este tipo de unidade.</td></tr>';
    return;
  }
  const detalhe = new Map((state.detail?.insumos || []).map((i) => [i.insumo_id, i]));
  tbody.innerHTML = insumos.map((i) => {
    const d = detalhe.get(i.id) || {};
    const prev = d.previsto ?? i.previsao ?? "";
    const exec = d.executado ?? "";
    return `<tr data-insumo-id="${i.id}">
      <td>${esc(i.subitem || "-")}</td><td>${esc(i.descricao)}</td>
      <td><input type="number" step="0.01" class="form-control form-control-sm inp-prev" value="${prev}"></td>
      <td><input type="number" step="0.01" class="form-control form-control-sm inp-exec" value="${exec}"></td>
    </tr>`;
  }).join("");
}

function renderVeiculos() {
  const veiculos = state.ctx.veiculos || [];
  $("secVeiculos").classList.toggle("hidden", !veiculos.length);
  if (!veiculos.length) return;
  const detalhe = new Map((state.detail?.veiculos || []).map((v) => [v.veiculo_id, v]));
  $("tbodyVeiculos").innerHTML = veiculos.map((v) => {
    const d = detalhe.get(v.id) || {};
    return `<tr data-veiculo-id="${v.id}">
      <td>${esc(v.nome)}</td>
      <td><input type="number" step="0.01" class="form-control form-control-sm inp-veic-prev" value="${d.previsto ?? ""}"></td>
      <td><input type="number" step="0.01" class="form-control form-control-sm inp-veic-exec" value="${d.executado ?? ""}"></td>
    </tr>`;
  }).join("");
}

function renderKit() {
  const mostrar = state.temLanches && ((state.ctx.kit || []).length > 0 || (state.detail?.kit || []).length > 0);
  $("secKit").classList.toggle("hidden", !mostrar);
  if (!mostrar) return;
  const detalhePorItem = new Map((state.detail?.kit || []).map((k) => [k.item, k]));
  const catalogo = state.ctx.kit || [];
  const itens = catalogo.map((k) => k.descricao);
  for (const k of state.detail?.kit || []) if (!itens.includes(k.item)) itens.push(k.item);
  const admin = state.me?.perfil === "admin";
  const qtdPadrao = state.ctx.unidade.lanches_previstos || "";
  $("tbodyKit").innerHTML = itens.map((item) => {
    const d = detalhePorItem.get(item) || {};
    const qtd = d.quantitativo ?? qtdPadrao;
    return `<tr data-item="${escAttr(item)}">
      <td>${esc(item)}</td>
      <td><input type="number" step="0.01" class="form-control form-control-sm inp-kit-qtd" value="${qtd}"></td>
      <td><input type="text" class="form-control form-control-sm inp-kit-conf" value="${escAttr(d.conformidade || "")}" ${admin ? "" : "disabled"}></td>
      <td><input type="number" step="0.01" class="form-control form-control-sm inp-kit-pct" value="${d.percentual ?? ""}" ${admin ? "" : "disabled"}></td>
      <td><input type="text" class="form-control form-control-sm inp-kit-obs" value="${escAttr(d.obs || "")}"></td>
    </tr>`;
  }).join("");
}

function renderCentral() {
  const central = state.ctx.pode_central;
  $("secCentral").classList.toggle("hidden", !central);
  if (!central) return;
  const locDetalhe = new Map((state.detail?.locacao || []).map((l) => [l.unidade_locacao, l]));
  const unidades = state.ctx.unidades_aluguel || [];
  const nomes = unidades.map((u) => u.nome);
  for (const l of state.detail?.locacao || []) if (!nomes.includes(l.unidade_locacao)) nomes.push(l.unidade_locacao);
  $("tbodyLocacao").innerHTML = nomes.map((nome) => {
    const d = locDetalhe.get(nome) || {};
    const reg = d.controle_regularizacao || "Não";
    return `<tr data-loc-unidade="${escAttr(nome)}">
      <td>${esc(nome)}</td>
      <td><input type="number" step="1" class="form-control form-control-sm inp-loc-dias" value="${d.dias_corridos ?? ""}"></td>
      <td><select class="form-select form-select-sm sel-loc-reg">
        <option value="Não"${reg === "Não" ? " selected" : ""}>Não</option>
        <option value="Sim"${reg === "Sim" ? " selected" : ""}>Sim</option></select></td>
      <td><input type="text" class="form-control form-control-sm inp-loc-nota" value="${escAttr(d.nota || "")}"></td>
      <td><input type="date" class="form-control form-control-sm inp-loc-data" value="${d.data_autorizo || ""}"></td>
    </tr>`;
  }).join("");

  const labels = [
    ["1. CSIMAS — Capacidade de Contratação", "nota1"],
    ["2. CSIMAS — Adimplência", "nota2"],
    ["3. COP — Insumos", "nota3"],
    ["4. COP — Veículos", "nota4"],
    ["5. CIN — Aluguéis", "nota5"],
    ["6. CCPAR — Prestação", "nota6"],
    ["7. CCPAR — Diligência", "nota7"],
    ["8. CSIMAS — Ergon", "nota8"],
    ["9. COP — Motoristas", "nota9"],
    ["10. CCPAR — SIAFIC", "nota10"],
    ["11. CCPAR — Osinfo", "nota11"]
  ];
  const av = state.detail?.avaliacao_central || {};
  $("avaliacaoBox").innerHTML = labels.map(([label, key]) => `
    <div class="col-md-4">
      <label class="form-label small">${label}</label>
      <input type="number" step="0.01" class="form-control form-control-sm inp-aval" data-key="${key}" value="${av[key] ?? ""}">
    </div>`).join("");
  $("inpObsNutri").value = av.obs_nutricionista || state.detail?.lancamento?.obs_nutricionista || "";
}

function setSelectValue(sel, value) {
  const v = value || "";
  const opts = [...sel.options];
  if (v && !opts.some((o) => o.value === v)) {
    const opt = document.createElement("option");
    opt.value = v;
    opt.textContent = v;
    sel.appendChild(opt);
  }
  sel.value = v;
}

function preencherCabecalho(detalhe) {
  const l = detalhe?.lancamento;
  if (!l) {
    $("selParecer").value = "";
    $("txtObs").value = "";
    $("txtDesc").value = "";
    $("txtAnalise").value = "";
    $("selClassificacao").value = "";
    $("inpObsNutri").value = "";
    return;
  }
  setSelectValue($("selParecer"), l.parecer_opcao);
  $("txtObs").value = l.observacoes || "";
  $("txtDesc").value = l.descricao_atividades || "";
  $("txtAnalise").value = l.analise_atividades || "";
  setSelectValue($("selClassificacao"), l.classificacao);
  $("inpObsNutri").value = detalhe?.avaliacao_central?.obs_nutricionista || "";
}

// ---------------------------------------------------------------------------
// Coleta e save
// ---------------------------------------------------------------------------
function coletarPayload() {
  const unidadeId = Number($("selUnidade").value);
  const mes = $("inpMes").value;
  const admin = state.me?.perfil === "admin";
  const detalhePostos = [...document.querySelectorAll("#tbodyPostos tr[data-posto-id]")].map((tr) => {
    const chk = tr.querySelector(".chk-ocupado");
    const ocupado = chk.checked;
    const lic = tr.querySelector(".sel-licenca");
    return {
      posto_id: Number(tr.dataset.postoId),
      ocupado,
      desempenho: ocupado ? tr.querySelector(".sel-desempenho").value : null,
      licenca_medica: admin && ocupado && lic ? lic.value : null
    };
  });
  const detalheInsumos = [...document.querySelectorAll("#tbodyInsumos tr[data-insumo-id]")].map((tr) => ({
    insumo_id: Number(tr.dataset.insumoId),
    previsto: num(tr.querySelector(".inp-prev").value),
    executado: num(tr.querySelector(".inp-exec").value)
  }));
  const detalheVeiculos = [...document.querySelectorAll("#tbodyVeiculos tr[data-veiculo-id]")].map((tr) => ({
    veiculo_id: Number(tr.dataset.veiculoId),
    previsto: num(tr.querySelector(".inp-veic-prev").value),
    executado: num(tr.querySelector(".inp-veic-exec").value)
  }));
  const composicaoKit = state.temLanches
    ? [...document.querySelectorAll("#tbodyKit tr[data-item]")].map((tr) => ({
        item: tr.dataset.item,
        quantitativo: num(tr.querySelector(".inp-kit-qtd").value),
        conformidade: tr.querySelector(".inp-kit-conf").disabled ? null : (tr.querySelector(".inp-kit-conf").value || null),
        percentual: tr.querySelector(".inp-kit-pct").disabled ? null : num(tr.querySelector(".inp-kit-pct").value),
        obs: tr.querySelector(".inp-kit-obs").value || null
      }))
    : [];
  let locacao = [];
  let avaliacao = null;
  if (state.ctx?.pode_central) {
    locacao = [...document.querySelectorAll("#tbodyLocacao tr[data-loc-unidade]")].map((tr) => ({
      unidade_locacao: tr.dataset.locUnidade,
      dias_corridos: num(tr.querySelector(".inp-loc-dias").value),
      controle_regularizacao: tr.querySelector(".sel-loc-reg").value,
      nota: tr.querySelector(".inp-loc-nota").value || null,
      data_autorizo: tr.querySelector(".inp-loc-data").value || null
    })).filter((l) => l.dias_corridos || l.nota || l.data_autorizo || l.controle_regularizacao === "Sim");
    const notas = {};
    document.querySelectorAll(".inp-aval").forEach((inp) => {
      const v = num(inp.value);
      if (v !== null) notas[inp.dataset.key] = v;
    });
    const obs = $("inpObsNutri").value || null;
    if (Object.keys(notas).length || obs) {
      avaliacao = { perfil_meta: state.me?.meta ?? null, ...notas, obs_nutricionista: obs };
    }
  }
  return {
    unidade_id: unidadeId,
    referencia_mes: mes ? mes + "-01" : "",
    tem_lanches: state.temLanches,
    lanches_previsto: state.temLanches ? (num($("inpLanchesPrev").value) ?? 0) : 0,
    lanches_executado: state.temLanches ? num($("inpLanchesExec").value) : null,
    parecer_opcao: $("selParecer").value,
    observacoes: $("txtObs").value,
    descricao_atividades: $("txtDesc").value,
    analise_atividades: $("txtAnalise").value,
    classificacao: $("selClassificacao").value,
    detalhe_postos: detalhePostos,
    detalhe_insumos: detalheInsumos,
    detalhe_veiculos: detalheVeiculos,
    composicao_kit: composicaoKit,
    locacao,
    avaliacao_central: avaliacao,
    confirmar_duplicado: false
  };
}

async function salvar() {
  const payload = coletarPayload();
  if (!payload.unidade_id || !payload.referencia_mes) {
    setFormStatus("Selecione unidade e mês.", true);
    return;
  }
  if (!payload.parecer_opcao) {
    setFormStatus("Selecione o parecer.", true);
    return;
  }
  const editando = Boolean(state.editId);
  const url = editando ? `/lancamentos/${state.editId}` : "/lancamentos";
  const method = editando ? "PUT" : "POST";
  setFormStatus("Salvando...");
  try {
    const res = await apiJson(url, { method, body: JSON.stringify(payload) });
    state.editId = res.id;
    state.detail = await apiJson(`/lancamentos/${res.id}`);
    mostrarPdf(res.id);
    setFormStatus(`Salvo com sucesso (ID ${res.legacy_id}).`);
    loadRecent();
  } catch (e) {
    if (e.status === 409) {
      const info = e.data?.detail || {};
      const ids = (info.existentes || []).map((x) => x.legacy_id || x.id).join(", ");
      const ok = confirm((info.mensagem || "Já existe lançamento para esta unidade/mês.") +
        (ids ? `\nExistentes: ${ids}` : "") + "\n\nDeseja registrar mesmo assim?");
      if (ok) {
        payload.confirmar_duplicado = true;
        try {
          const res = await apiJson(url, { method, body: JSON.stringify(payload) });
          state.editId = res.id;
          state.detail = await apiJson(`/lancamentos/${res.id}`);
          mostrarPdf(res.id);
          setFormStatus(`Salvo com aviso de duplicidade (ID ${res.legacy_id}).`);
          loadRecent();
          return;
        } catch (e2) {
          setFormStatus("Erro: " + (e2.data?.detail || e2.message), true);
          return;
        }
      }
      setFormStatus("Salvamento cancelado.", true);
      return;
    }
    setFormStatus("Erro: " + (e.data?.detail || e.message), true);
  }
}

// ---------------------------------------------------------------------------
// Edição / recentes
// ---------------------------------------------------------------------------
async function abrirEdicao(id) {
  try {
    setStatus("Carregando lançamento...");
    const d = await apiJson(`/lancamentos/${id}`);
    state.detail = d;
    state.editId = d.lancamento.id;
    $("selUnidade").value = String(d.lancamento.unidade_id);
    $("inpMes").value = (d.lancamento.referencia_mes || "").slice(0, 7);
    await carregarContexto();
    preencherCabecalho(d);
    mostrarPdf(d.lancamento.id);
    setStatus(`Editando ${d.lancamento.legacy_id} — ${d.lancamento.unidade_nome}`);
    window.scrollTo({ top: 0, behavior: "smooth" });
  } catch (e) {
    setStatus("Erro: " + (e.data?.detail || e.message));
  }
}

function novo() {
  state.detail = null;
  state.editId = null;
  esconderPdf();
  $("selParecer").value = "";
  $("txtObs").value = "";
  $("txtDesc").value = "";
  $("txtAnalise").value = "";
  $("selClassificacao").value = "";
  $("formStatus").textContent = "";
  carregarContexto();
}

async function buscar() {
  const q = $("inpBuscaId").value.trim();
  if (!q) return;
  try {
    const rows = await apiJson(`/lancamentos?id_lancamento=${encodeURIComponent(q)}&limit=20`);
    if (!rows.length) {
      setStatus("Nenhum lançamento encontrado para " + q);
      return;
    }
    await abrirEdicao(rows[0].id);
  } catch (e) {
    setStatus("Erro: " + (e.data?.detail || e.message));
  }
}

async function loadRecent() {
  try {
    const rows = await apiJson("/lancamentos?limit=20");
    const tbody = $("tbodyRecentes");
    if (!rows.length) {
      tbody.innerHTML = '<tr><td colspan="6" class="text-muted">Nenhum lançamento.</td></tr>';
      return;
    }
    tbody.innerHTML = rows.map((r) => `
      <tr>
        <td class="small">${esc(r.legacy_id || r.id)}${r.duplicado ? ' <span class="badge bg-warning text-dark">dup</span>' : ""}</td>
        <td class="small">${esc(r.unidade_nome)}</td>
        <td class="small">${esc((r.referencia_mes || "").slice(0, 7))}</td>
        <td class="small">${esc(r.autor_email)}</td>
        <td class="small">${esc(r.criado_em)}</td>
        <td class="text-end text-nowrap">
          <button class="btn btn-sm btn-outline-primary btn-editar" data-id="${r.id}">Editar</button>
          <button class="btn btn-sm btn-outline-danger btn-pdf-recente" data-id="${r.id}">PDF</button>
          ${state.me?.perfil === "admin" ? `<button class="btn btn-sm btn-outline-secondary btn-excluir" data-id="${r.id}">Excluir</button>` : ""}
        </td>
      </tr>`).join("");
    tbody.querySelectorAll(".btn-editar").forEach((b) => b.onclick = () => abrirEdicao(Number(b.dataset.id)));
    tbody.querySelectorAll(".btn-pdf-recente").forEach((b) => b.onclick = () => baixarPdf(Number(b.dataset.id)));
    tbody.querySelectorAll(".btn-excluir").forEach((b) => b.onclick = () => excluir(Number(b.dataset.id)));
  } catch (e) {
    $("tbodyRecentes").innerHTML = `<tr><td colspan="6" class="text-danger">${esc(e.data?.detail || e.message)}</td></tr>`;
  }
}

async function excluir(id) {
  if (!confirm("Excluir este lançamento? Ele será marcado como excluído (soft delete).")) return;
  try {
    await apiJson(`/lancamentos/${id}`, { method: "DELETE" });
    if (state.editId === id) novo();
    loadRecent();
    setStatus("Lançamento excluído.");
  } catch (e) {
    setStatus("Erro ao excluir: " + (e.data?.detail || e.message));
  }
}

// ---------------------------------------------------------------------------
// Eventos e boot
// ---------------------------------------------------------------------------
$("btnLogin").onclick = entrar;
$("btnLogout").onclick = () => auth.signOut();
$("btnCarregar").onclick = () => { state.detail = null; state.editId = null; esconderPdf(); carregarContexto(); };
$("btnNovo").onclick = novo;
$("btnBuscar").onclick = buscar;
$("btnSalvar").onclick = salvar;
$("btnRecentes").onclick = loadRecent;
$("btnPdf").onclick = () => state.lastPdf && baixarPdf(state.lastPdf);
$("btnPdfTop").onclick = () => state.lastPdf && baixarPdf(state.lastPdf);
$("selUnidade").onchange = () => { state.detail = null; state.editId = null; esconderPdf(); carregarContexto(); };
$("inpMes").onchange = () => { state.detail = null; state.editId = null; esconderPdf(); };

auth.getRedirectResult().catch((e) => console.warn("redirect", e));
auth.onAuthStateChanged(async (user) => {
  if (!user) {
    $("loginCard").classList.remove("hidden");
    $("appArea").classList.add("hidden");
    $("userEmail").textContent = "";
    $("btnLogout").classList.add("hidden");
    return;
  }
  try {
    $("loginMsg").textContent = "";
    await carregarMe();
  } catch (e) {
    $("loginCard").classList.remove("hidden");
    $("appArea").classList.add("hidden");
    $("loginMsg").textContent = "Autenticado como " + (user.email || user.uid) +
      ", mas a API recusou: " + (e.data?.detail || e.message);
  }
});
