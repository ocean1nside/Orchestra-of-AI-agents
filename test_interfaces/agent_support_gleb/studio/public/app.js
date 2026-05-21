const $ = (id) => document.getElementById(id);

const VIEW_META = {
  widget: { title: "Виджет", subtitle: "Тест канала widget → POST /api/v1/widget/invoke" },
  chats: { title: "Диалоги", subtitle: "Operator API: все каналы, ответы, контроль ИИ/менеджер" },
  knowledge: { title: "База знаний", subtitle: "Добавление документов и индексация для ответов бота" },
  prompts: { title: "Инструкции агента", subtitle: "Редактор блоков и вкладка «Тюнинг» — правка промптов по жалобе" },
  system: { title: "Система", subtitle: "Health агента, оркестратора и инфраструктуры" },
};

let activeView = "widget";
let pollChats = null;
let pollMsgs = null;
let selectedChatId = null;
let selectedDocId = null;
let selectedPromptKey = null;
let jobPollTimer = null;
let pendingTune = null;
let activePromptTab = "editor";

function esc(s) {
  const d = document.createElement("div");
  d.textContent = s == null ? "" : String(s);
  return d.innerHTML;
}

function toast(msg) {
  const el = $("toast");
  el.textContent = msg;
  el.classList.add("show");
  setTimeout(() => el.classList.remove("show"), 2800);
}

function errMsg(data, status) {
  const d = data?.detail;
  if (typeof d === "string") return d;
  if (Array.isArray(d)) return d.map((x) => x.msg || JSON.stringify(x)).join("; ");
  return data?.message || data?.raw || `HTTP ${status}`;
}

/** С <base href="/studio/"> пути с ведущим / уходят в корень сайта → 404. */
function apiUrl(path) {
  return path.startsWith("/") ? path.slice(1) : path;
}

async function api(path, opts = {}) {
  const r = await fetch(apiUrl(path), {
    cache: "no-store",
    ...opts,
    headers: { "Content-Type": "application/json", ...(opts.headers || {}) },
  });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(errMsg(data, r.status));
  return data;
}

function setView(view) {
  activeView = view;
  document.querySelectorAll(".nav-btn").forEach((b) => b.classList.toggle("active", b.dataset.view === view));
  document.querySelectorAll(".view").forEach((v) => v.classList.toggle("active", v.id === `view-${view}`));
  const m = VIEW_META[view] || VIEW_META.widget;
  $("viewTitle").textContent = m.title;
  $("viewSubtitle").textContent = m.subtitle;
  if (view === "chats") startChatsPoll();
  else stopChatsPoll();
  if (view === "knowledge") loadDocList();
  if (view === "prompts") {
    setPromptTab(activePromptTab);
    loadPromptList();
  }
  if (view === "system") refreshSystem();
}

document.querySelectorAll(".nav-btn").forEach((btn) => {
  btn.addEventListener("click", () => setView(btn.dataset.view));
});

$("btnRefresh").addEventListener("click", () => {
  pingHealth();
  if (activeView === "widget") return;
  if (activeView === "chats") {
    loadChatList();
    if (selectedChatId) loadChatMessages(selectedChatId);
  }
  if (activeView === "knowledge") loadDocList();
  if (activeView === "prompts") loadPromptList();
  if (activeView === "system") refreshSystem();
});

// ---------- Health ----------

async function pingHealth() {
  const setDot = (id, ok) => {
    const el = $(id);
    el.classList.remove("ok", "err");
    el.classList.add(ok ? "ok" : "err");
  };
  try {
    const r = await fetch(apiUrl("/api/health/agent"), { cache: "no-store" });
    setDot("dot-agent", r.ok);
  } catch {
    setDot("dot-agent", false);
  }
  try {
    const r = await fetch(apiUrl("/api/health/orchestrator"), { cache: "no-store" });
    setDot("dot-orch", r.ok);
  } catch {
    setDot("dot-orch", false);
  }
}

async function refreshSystem() {
  const grid = $("sys-grid");
  grid.innerHTML = "";
  $("sys-raw").textContent = "";

  const cards = [
    { name: "Агент", url: "/api/health/agent" },
    { name: "Оркестратор", url: "/api/health/orchestrator" },
  ];

  for (const c of cards) {
    const div = document.createElement("div");
    div.className = "sys-card";
    try {
      const r = await fetch(apiUrl(c.url), { cache: "no-store" });
      const data = await r.json().catch(() => ({}));
      div.classList.add(r.ok ? "ok" : "bad");
      div.innerHTML = `<div class="name">${esc(c.name)}</div><div class="st">${r.ok ? "ok" : "error"}</div>`;
      if (!r.ok) div.querySelector(".st").textContent = errMsg(data, r.status);
    } catch (e) {
      div.classList.add("bad");
      div.innerHTML = `<div class="name">${esc(c.name)}</div><div class="st">${esc(String(e.message || e))}</div>`;
    }
    grid.appendChild(div);
  }

  try {
    const infra = await api("/api/health/infrastructure");
    $("sys-raw").textContent = JSON.stringify(infra, null, 2);
    const services = infra.services || infra;
    for (const [key, val] of Object.entries(services)) {
      if (typeof val !== "object" || val === null) continue;
      const st = val.status || "unknown";
      const div = document.createElement("div");
      div.className = "sys-card " + (st === "ok" ? "ok" : st === "unknown" ? "" : "bad");
      div.innerHTML = `<div class="name">${esc(key)}</div><div class="st">${esc(st)}</div>`;
      grid.appendChild(div);
    }
  } catch (e) {
    $("sys-raw").textContent = String(e.message || e);
  }
}

$("sys-refresh").addEventListener("click", refreshSystem);

// ---------- Widget ----------

const STORAGE_CONV = "studio_widget_conversation_id";
const STORAGE_USER = "studio_widget_user_id";

function wEnsureIds() {
  let conv = localStorage.getItem(STORAGE_CONV);
  let user = localStorage.getItem(STORAGE_USER);
  if (!conv) {
    conv = "demo_" + Math.random().toString(36).slice(2, 10);
    localStorage.setItem(STORAGE_CONV, conv);
  }
  if (!user) {
    user = "visitor_" + Math.random().toString(36).slice(2, 8);
    localStorage.setItem(STORAGE_USER, user);
  }
  $("w-conv").value = conv;
  $("w-user").value = user;
}

function wSaveIds() {
  localStorage.setItem(STORAGE_CONV, $("w-conv").value.trim());
  localStorage.setItem(STORAGE_USER, $("w-user").value.trim());
}

function wAppend(role, html) {
  const box = $("w-messages");
  const div = document.createElement("div");
  div.className = "bubble " + role;
  div.innerHTML = html;
  box.appendChild(div);
  box.scrollTop = box.scrollHeight;
}

async function wSend() {
  const text = $("w-input").value.trim();
  if (!text) return;
  const conversation_id = $("w-conv").value.trim();
  const user_id = $("w-user").value.trim();
  if (!conversation_id || !user_id) {
    $("w-err").textContent = "Заполните conversation_id и user_id.";
    return;
  }
  $("w-err").textContent = "";
  wSaveIds();
  wAppend("user", `<div class="meta">Вы</div><div>${esc(text)}</div>`);
  $("w-input").value = "";
  $("w-send").disabled = true;

  try {
    const data = await api("/api/widget/invoke", {
      method: "POST",
      body: JSON.stringify({
        channel: "widget",
        conversation_id,
        user_id,
        message: text,
        context: { source: "studio/widget" },
      }),
    });
    const meta = data.meta || {};
    const holder = meta.conversation_holder === "human" ? " · менеджер" : "";
    const muted = meta.ai_muted === true;
    let body = (data.answer || "").trim();
    if (muted && !body) body = "ИИ не отвечает (диалог у менеджера).";
    let src = "";
    if (Array.isArray(data.sources) && data.sources.length) {
      const lines = data.sources.slice(0, 8).map((s) => esc(s.title || s.chunk_id || ""));
      src = `<div class="sources">Источники: ${lines.join(" · ")}</div>`;
    }
    wAppend("assistant", `<div class="meta">Ассистент${esc(holder)}</div><div>${esc(body)}</div>${src}`);
  } catch (e) {
    wAppend("system", esc(String(e.message || e)));
  } finally {
    $("w-send").disabled = false;
  }
}

$("w-conv").addEventListener("change", wSaveIds);
$("w-user").addEventListener("change", wSaveIds);
$("w-send").addEventListener("click", wSend);
$("w-input").addEventListener("keydown", (ev) => {
  if (ev.key === "Enter" && !ev.shiftKey) {
    ev.preventDefault();
    wSend();
  }
});
$("w-newConv").addEventListener("click", () => {
  const conv = "demo_" + Math.random().toString(36).slice(2, 10);
  localStorage.setItem(STORAGE_CONV, conv);
  $("w-conv").value = conv;
  $("w-messages").innerHTML = "";
  toast("Новый conversation_id");
});
$("w-clear").addEventListener("click", () => {
  $("w-messages").innerHTML = "";
});

wEnsureIds();

// ---------- Chats ----------

function stopChatsPoll() {
  if (pollChats) {
    clearInterval(pollChats);
    pollChats = null;
  }
  if (pollMsgs) {
    clearInterval(pollMsgs);
    pollMsgs = null;
  }
}

function startChatsPoll() {
  stopChatsPoll();
  loadChatList();
  pollChats = setInterval(loadChatList, 5000);
}

function formatTime(iso) {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString("ru-RU", { dateStyle: "short", timeStyle: "short" });
  } catch {
    return String(iso);
  }
}

async function loadChatList() {
  $("ch-errL").textContent = "";
  const hidden = $("ch-includeHidden").checked ? "true" : "false";
  try {
    const data = await api(`/api/operator/conversations?limit=100&include_hidden=${hidden}`);
    const list = $("ch-list");
    list.innerHTML = "";
    for (const c of data.items || []) {
      const row = document.createElement("div");
      row.className = "chat-row" + (c.id === selectedChatId ? " active" : "");
      const holder = c.conversation_holder === "human" ? "human" : "ai";
      const badges = [
        `<span class="badge">${esc(c.channel)}</span>`,
        `<span class="badge ${holder}">${holder === "human" ? "Менеджер" : "ИИ"}</span>`,
      ];
      if (c.hidden) badges.push('<span class="badge hidden">скрыт</span>');
      row.innerHTML = `<div class="id">${esc(c.id)}</div><div class="sub">${badges.join("")}<br/>${formatTime(c.last_message_at)}</div>`;
      row.addEventListener("click", () => selectChat(c.id));
      list.appendChild(row);
    }
  } catch (e) {
    $("ch-errL").textContent = String(e.message || e);
  }
}

async function loadChatMessages(id) {
  $("ch-errR").textContent = "";
  try {
    const d = await api("/api/operator/conversations/" + encodeURIComponent(id));
    const hidden = Boolean(d.hidden);
    $("ch-side").innerHTML = `
      <dl>
        <dt>ID</dt><dd>${esc(d.id)}</dd>
        <dt>Канал</dt><dd>${esc(d.channel)}</dd>
        <dt>Пользователь</dt><dd>${esc(d.user_id)}</dd>
        <dt>Контроль</dt><dd>${d.conversation_holder === "human" ? "Менеджер (ИИ молчит)" : "ИИ"}</dd>
        <dt>Скрыт</dt><dd>${hidden ? "да" : "нет"}</dd>
        <dt>Создан</dt><dd>${formatTime(d.created_at)}</dd>
      </dl>
      <div class="toolbar" style="margin-top:16px">
        <button type="button" class="btn" id="ch-ai">Вернуть ИИ</button>
        <button type="button" class="btn" id="ch-human">Забрать менеджеру</button>
      </div>
      <div class="toolbar">
        <button type="button" class="btn btn-ghost" id="ch-hide">${hidden ? "Показать в списке" : "Скрыть из списка"}</button>
      </div>
    `;
    $("ch-ai").onclick = () => setControl(id, "ai");
    $("ch-human").onclick = () => setControl(id, "human");
    $("ch-hide").onclick = () => setVisibility(id, !hidden);

    let factsHtml = '<p class="empty-hint" style="margin:12px 0 0">Факты о пользователе пока не собраны.</p>';
    try {
      const uf = await api(
        "/api/operator/conversations/" + encodeURIComponent(id) + "/user-facts",
      );
      const items = uf.items || [];
      if (items.length) {
        factsHtml =
          '<h4 style="margin:16px 0 8px;font-size:13px">Память о пользователе</h4><ul class="user-facts-list">' +
          items
            .map(
              (f) =>
                `<li><strong>${esc(f.label)}:</strong> ${esc(f.value)}</li>`,
            )
            .join("") +
          "</ul>";
      }
    } catch {
      factsHtml = "";
    }
    $("ch-side").insertAdjacentHTML("beforeend", factsHtml);

    const m = await api(
      "/api/operator/conversations/" + encodeURIComponent(id) + "/messages?limit=500",
    );
    const box = $("ch-messages");
    box.innerHTML = "";
    for (const msg of m.messages || []) {
      const div = document.createElement("div");
      const role = msg.role === "user" ? "user" : msg.role === "operator" ? "operator" : "assistant";
      div.className = "msg " + role;
      div.innerHTML = `<div class="role">${esc(msg.role)} · ${formatTime(msg.created_at)}</div><div>${esc(msg.content)}</div>`;
      box.appendChild(div);
    }
    box.scrollTop = box.scrollHeight;
  } catch (e) {
    $("ch-errR").textContent = String(e.message || e);
  }
}

async function openConversationFromUrl(id) {
  if (!id || !String(id).trim()) return;
  const convId = String(id).trim();
  $("ch-includeHidden").checked = true;
  setView("chats");
  selectedChatId = convId;
  await loadChatList();
  await selectChat(convId);
}

function applyEscalationDeepLink() {
  const params = new URLSearchParams(window.location.search);
  const view = params.get("view");
  const conv = params.get("conversation_id") || params.get("conversation");
  if (view === "chats" && !conv) setView("chats");
  if (conv) openConversationFromUrl(conv);
}

async function selectChat(id) {
  selectedChatId = id;
  document.querySelectorAll(".chat-row").forEach((el, i) => {
    /* active set via reload */
  });
  if (pollMsgs) clearInterval(pollMsgs);
  await loadChatList();
  await loadChatMessages(id);
  pollMsgs = setInterval(() => loadChatMessages(id), 2500);
}

async function setControl(id, holder) {
  try {
    await api("/api/operator/conversations/" + encodeURIComponent(id) + "/control", {
      method: "POST",
      body: JSON.stringify({ holder }),
    });
    toast(holder === "human" ? "Контроль у менеджера" : "Контроль у ИИ");
    await loadChatList();
    await loadChatMessages(id);
  } catch (e) {
    $("ch-errR").textContent = String(e.message || e);
  }
}

async function setVisibility(id, hidden) {
  try {
    await api("/api/operator/conversations/" + encodeURIComponent(id) + "/visibility", {
      method: "POST",
      body: JSON.stringify({ hidden }),
    });
    toast(hidden ? "Диалог скрыт" : "Диалог снова в списке");
    if (hidden && !$("ch-includeHidden").checked) selectedChatId = null;
    await loadChatList();
    if (selectedChatId) await loadChatMessages(selectedChatId);
  } catch (e) {
    $("ch-errR").textContent = String(e.message || e);
  }
}

$("ch-refresh").addEventListener("click", loadChatList);
$("ch-includeHidden").addEventListener("change", loadChatList);
$("ch-send").addEventListener("click", async () => {
  if (!selectedChatId) return;
  const text = $("ch-reply").value.trim();
  if (!text) return;
  try {
    await api("/api/operator/conversations/" + encodeURIComponent(selectedChatId) + "/reply", {
      method: "POST",
      body: JSON.stringify({ text }),
    });
    $("ch-reply").value = "";
    await loadChatMessages(selectedChatId);
    await loadChatList();
  } catch (e) {
    $("ch-errR").textContent = String(e.message || e);
  }
});

// ---------- Knowledge ----------

let kUploadFile = null;
let kAiNormalized = false;

const META_LABELS = {
  source_filename: "Исходный файл",
  file_format: "Формат",
  upload_method: "Способ загрузки",
  byte_size: "Размер файла (байт)",
  chunk_count: "Чанков после индексации",
  extracted_char_count: "Символов в извлечённом тексте",
  indexed_at: "Проиндексирован",
  original_path: "Путь к оригиналу",
  content_hash: "Хеш содержимого",
  category: "Категория (для фильтра RAG)",
  chunk_strategy: "Стратегия нарезки",
  ai_normalized: "Подготовлено через ИИ",
};

function formatUploadMethod(v) {
  if (v === "file") return "файл";
  if (v === "text") return "текст в форме";
  return v;
}

function formatDocInfoRows(meta) {
  const m = meta || {};
  const keys = [
    "source_filename",
    "file_format",
    "upload_method",
    "byte_size",
    "chunk_count",
    "extracted_char_count",
    "indexed_at",
    "category",
    "original_path",
    "content_hash",
    "chunk_strategy",
    "ai_normalized",
  ];
  const rows = [];
  for (const k of keys) {
    if (m[k] === undefined || m[k] === null || m[k] === "") continue;
    let val = m[k];
    if (k === "upload_method") val = formatUploadMethod(val);
    if (k === "byte_size" || k === "chunk_count" || k === "extracted_char_count") val = String(val);
    rows.push(
      `<tr><th>${esc(META_LABELS[k] || k)}</th><td>${k === "original_path" || k === "content_hash" ? `<code>${esc(val)}</code>` : esc(val)}</td></tr>`,
    );
  }
  const extra = Object.keys(m).filter((k) => !keys.includes(k));
  for (const k of extra.sort()) {
    rows.push(
      `<tr><th>${esc(META_LABELS[k] || k)}</th><td><code>${esc(JSON.stringify(m[k]))}</code></td></tr>`,
    );
  }
  return rows.length
    ? `<table class="doc-info-table">${rows.join("")}</table>`
    : '<p class="empty-hint" style="margin:0">Сведения появятся после первой индексации (reindex). Поле «метаданные» — служебная информация о файле, не текст документа.</p>';
}

function chunkLenClass(n) {
  if (n < 200) return "chunk-len-warn";
  if (n > 1400) return "chunk-len-warn";
  return "chunk-len-ok";
}

function renderChunkCards(items, expanded) {
  if (!items.length) {
    return '<p class="empty-hint">Чанков нет. Статус должен быть «В поиске» — нажмите Reindex выбранного.</p>';
  }
  return items
    .map((c) => {
      const n = c.char_count || (c.content || "").length;
      const body = esc(c.content || "");
      const preview = expanded ? body : body.slice(0, 400) + (body.length > 400 ? "…" : "");
      return `<article class="chunk-card">
        <div class="chunk-card-head">
          <strong>Чанк #${c.chunk_index + 1}</strong>
          <span class="${chunkLenClass(n)}">${n} симв.</span>
          <span>~1000 по абзацам — норма</span>
        </div>
        <pre class="chunk-body${expanded ? " expanded" : ""}">${preview}</pre>
      </article>`;
    })
    .join("");
}

let lastChunksPreview = null;

function updateChunksSummary(items) {
  const chars = items.reduce((s, c) => s + (c.char_count || 0), 0);
  const avg = items.length ? Math.round(chars / items.length) : 0;
  $("k-chunks-summary").textContent =
    items.length === 0
      ? "Документ ещё не разбит на фрагменты для поиска."
        : `${items.length} чанков · ${chars} символов всего · в среднем ${avg} симв. на чанк. Хороший чанк начинается с ## заголовка раздела, без обрывка с середины предложения.`;
}

async function openChunksPreview(docId, title) {
  const dlg = $("k-chunks-dialog");
  $("k-chunks-title").textContent = "Чанки: " + (title || docId);
  $("k-chunks-summary").textContent = "Загрузка…";
  $("k-chunks-list").innerHTML = "";
  $("k-chunks-err").textContent = "";
  lastChunksPreview = null;
  dlg.showModal();
  try {
    const data = await api("/api/orch/knowledge/documents/" + encodeURIComponent(docId) + "/chunks");
    const items = data.items || [];
    lastChunksPreview = items;
    updateChunksSummary(items);
    $("k-chunks-list").innerHTML = renderChunkCards(items, $("k-chunks-expand")?.checked);
  } catch (e) {
    $("k-chunks-err").textContent = String(e.message || e);
    $("k-chunks-summary").textContent = "";
  }
}

function statusBadge(st) {
  const s = (st || "").toLowerCase();
  const label =
    s === "indexed"
      ? "В поиске"
      : s === "indexing"
        ? "Индексация…"
        : s === "pending_index" || s === "uploaded"
          ? "Нужен reindex"
          : s === "failed"
            ? "Ошибка"
            : s;
  return `<span class="doc-status-badge ${esc(s)}">${esc(label)}</span>`;
}

document.querySelectorAll("[data-kmode]").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll("[data-kmode]").forEach((b) => b.classList.toggle("active", b === btn));
    const mode = btn.dataset.kmode;
    $("k-panel-file").classList.toggle("hidden", mode !== "file");
    $("k-panel-text").classList.toggle("hidden", mode !== "text");
    $("k-wizardErr").textContent = "";
  });
});

async function loadDocList() {
  $("k-errL").textContent = "";
  try {
    const data = await api("/api/orch/knowledge/documents");
    const list = $("k-list");
    list.innerHTML = "";
    const items = (data.items || []).filter((d) => (d.status || "") !== "deleted");
    if (!items.length) {
      list.innerHTML = '<p class="empty-hint" style="padding:12px">Пока нет документов. Нажмите «+ Добавить документ».</p>';
    }
    for (const d of items) {
      const id = d.document_id || d.id;
      const row = document.createElement("div");
      row.className = "doc-row" + (id === selectedDocId ? " active" : "");
      row.innerHTML = `<div class="title">${esc(d.title || id)}</div>${statusBadge(d.status)}`;
      row.addEventListener("click", () => selectDoc(id));
      list.appendChild(row);
    }
    $("k-reindexDoc").disabled = !selectedDocId;
    if ($("k-prepareAiDoc")) $("k-prepareAiDoc").disabled = !selectedDocId;
  } catch (e) {
    $("k-errL").textContent = String(e.message || e);
  }
}

async function selectDoc(id) {
  selectedDocId = id;
  $("k-reindexDoc").disabled = !id;
  if ($("k-prepareAiDoc")) $("k-prepareAiDoc").disabled = !id;
  $("k-errR").textContent = "";
  await loadDocList();
  try {
    const d = await api("/api/orch/knowledge/documents/" + encodeURIComponent(id));
    const infoHtml = formatDocInfoRows(d.metadata);
    const chunkHint =
      (d.metadata && d.metadata.chunk_count) != null
        ? ` · ${d.metadata.chunk_count} чанков`
        : "";
    $("k-detail").innerHTML = `
      <h3 style="margin:0 0 8px">${esc(d.title || id)}</h3>
      <p style="font-size:13px;color:var(--muted);margin:0 0 12px">
        ${statusBadge(d.status)} · ID: <code>${esc(d.document_id || id)}</code>${esc(chunkHint)}
      </p>
      <p style="font-size:13px;color:var(--muted);margin:0 0 12px">
        <strong>Метаданные</strong> — служебные поля о файле и индексации (имя, формат, число чанков), не содержимое базы.
        Статус <strong>indexed</strong> («В поиске») — текст разбит на чанки и попал в Qdrant.
      </p>
      <h4 style="margin:0 0 8px">Сведения о документе</h4>
      ${infoHtml}
      <div class="toolbar" style="margin-top:12px;flex-wrap:wrap;gap:8px">
        <button type="button" class="btn btn-primary" id="k-prepareAi-detail">Разобрать через ИИ и переиндексировать</button>
        <button type="button" class="btn" id="k-preview-chunks">Просмотр чанков</button>
        <button type="button" class="btn btn-danger" id="k-delete">Удалить</button>
      </div>
    `;
    $("k-preview-chunks").onclick = () => openChunksPreview(id, d.title);
    $("k-prepareAi-detail").onclick = () => prepareAiDocument(id);
    $("k-delete").onclick = async () => {
      if (!confirm("Удалить документ из базы?")) return;
      try {
        await api("/api/orch/knowledge/documents/" + encodeURIComponent(id), { method: "DELETE" });
        selectedDocId = null;
        toast("Документ удалён");
        await loadDocList();
        $("k-detail").innerHTML = '<p class="empty-hint">Выберите документ слева или нажмите «+ Добавить документ».</p>';
      } catch (err) {
        $("k-errR").textContent = String(err.message || err);
      }
    };
  } catch (e) {
    $("k-errR").textContent = String(e.message || e);
  }
}

function setKnowledgeJobStatus(text) {
  const t = text || "";
  if ($("k-jobStatus")) $("k-jobStatus").textContent = t;
  if ($("k-modalJobStatus")) $("k-modalJobStatus").textContent = t;
}

function syncNormalizeButton() {
  /* файл без ИИ-подготовки загружать нельзя */
}

async function prepareAiDocument(docId) {
  if (!docId) return;
  if (!confirm("Переписать документ через ИИ по правилам базы знаний и заново проиндексировать?")) return;
  $("k-errR").textContent = "";
  setKnowledgeJobStatus("ИИ разбирает документ…");
  try {
    const data = await api(
      "/api/orch/knowledge/documents/" + encodeURIComponent(docId) + "/prepare-ai",
      { method: "POST", body: "{}" },
    );
    toast(data.message || "ИИ-подготовка запущена");
    if (data.job_id) await pollJob(data.job_id);
    await selectDoc(docId);
  } catch (e) {
    $("k-errR").textContent = String(e.message || e);
    setKnowledgeJobStatus("");
  }
}

async function normalizeUploadFile() {
  if (!kUploadFile) {
    $("k-wizardErr").textContent = "Сначала выберите файл.";
    return;
  }
  $("k-wizardErr").textContent = "";
  const st = $("k-aiNormalizeStatus");
  if (st) st.textContent = "ИИ готовит Markdown…";
  setKnowledgeJobStatus("ИИ готовит Markdown…");
  const title = ($("k-title").value || kUploadFile.name || "").trim();
  try {
    const buf = await kUploadFile.arrayBuffer();
    const q = title ? "?title=" + encodeURIComponent(title) : "";
    const r = await fetch(apiUrl("/api/orch/knowledge/normalize-file" + q), {
      method: "POST",
      headers: { "X-Filename": encodeURIComponent(kUploadFile.name) },
      body: buf,
    });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(errMsg(data, r.status));
    const md = data.markdown || "";
    if (!md.trim()) throw new Error("Пустой ответ от ИИ.");
    kAiNormalized = true;
    $("k-textTitle").value = title || kUploadFile.name.replace(/\.[^.]+$/, "");
    $("k-textBody").value = md;
    document.querySelectorAll("[data-kmode]").forEach((b) => b.classList.toggle("active", b.dataset.kmode === "text"));
    $("k-panel-file").classList.add("hidden");
    $("k-panel-text").classList.remove("hidden");
    toast("Готово — проверьте текст на вкладке «Текст»");
    const info = `ИИ: ${data.char_count || md.length} симв. (${data.model || ""})`;
    setKnowledgeJobStatus(info);
    if (st) st.textContent = info;
  } catch (e) {
    $("k-wizardErr").textContent = String(e.message || e);
    setKnowledgeJobStatus("");
    if (st) st.textContent = "";
    kAiNormalized = false;
  }
}

function resetKnowledgeModal() {
  kUploadFile = null;
  kAiNormalized = false;
  $("k-title").value = "";
  $("k-textTitle").value = "";
  $("k-textBody").value = "";
  $("k-wizardErr").textContent = "";
  setKnowledgeJobStatus("");
  const strong = $("k-drop")?.querySelector("strong");
  if (strong) strong.textContent = "Выберите или перетащите файл";
  const stEl = $("k-aiNormalizeStatus");
  if (stEl) stEl.textContent = "";
  document.querySelectorAll("[data-kmode]").forEach((b) => b.classList.toggle("active", b.dataset.kmode === "file"));
  $("k-panel-file").classList.remove("hidden");
  $("k-panel-text").classList.add("hidden");
}

const kAddDlg = $("k-add-dialog");
const kGuideDlg = $("k-guide-dialog");

$("k-addOpen").addEventListener("click", () => {
  resetKnowledgeModal();
  kAddDlg.showModal();
});
$("k-guideOpen").addEventListener("click", () => kGuideDlg.showModal());
$("k-guide-close").addEventListener("click", () => kGuideDlg.close());
$("k-chunks-close").addEventListener("click", () => $("k-chunks-dialog").close());
$("k-chunks-expand")?.addEventListener("change", () => {
  if (!lastChunksPreview) return;
  $("k-chunks-list").innerHTML = renderChunkCards(lastChunksPreview, $("k-chunks-expand").checked);
});
$("k-add-cancel").addEventListener("click", () => kAddDlg.close());

async function afterDocCreated(docId, autoIndex, closeModal = false) {
  if (!docId) return;
  if (closeModal) kAddDlg.close();
  await loadDocList();
  await selectDoc(docId);
  if (autoIndex) {
    setKnowledgeJobStatus("Индексация…");
    await runReindex("document", docId);
  } else {
    setKnowledgeJobStatus("Загружено. Запустите reindex.");
    toast("Документ создан — нужен reindex");
  }
}

async function uploadFile(file) {
  if (!file) return;
  $("k-wizardErr").textContent = "";
  setKnowledgeJobStatus("Загрузка файла…");
  const titleInput = ($("k-title").value || "").trim();
  try {
    const buf = await file.arrayBuffer();
    const r = await fetch(apiUrl("/api/orch/knowledge/documents/upload"), {
      method: "POST",
      headers: {
        "X-Filename": encodeURIComponent(file.name),
        "Content-Type": file.type || "application/octet-stream",
      },
      body: buf,
    });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(errMsg(data, r.status));
    const docId = data.document_id || "";
    if (titleInput && docId) {
      try {
        await api("/api/orch/knowledge/documents/" + encodeURIComponent(docId), {
          method: "PATCH",
          body: JSON.stringify({ title: titleInput }),
        });
      } catch {
        /* optional */
      }
    }
    kUploadFile = null;
    await afterDocCreated(docId, $("k-autoIndex").checked, true);
    resetKnowledgeModal();
  } catch (e) {
    $("k-wizardErr").textContent = String(e.message || e);
    setKnowledgeJobStatus("");
  }
}

async function uploadTextDoc() {
  $("k-wizardErr").textContent = "";
  if (kUploadFile && !kAiNormalized) {
    $("k-wizardErr").textContent = "Дождитесь окончания ИИ-подготовки файла.";
    return;
  }
  const title = ($("k-textTitle").value || "").trim();
  const content = ($("k-textBody").value || "").trim();
  if (!title) {
    $("k-wizardErr").textContent = "Укажите название документа.";
    return;
  }
  if (!content) {
    $("k-wizardErr").textContent = "Вставьте текст документа.";
    return;
  }
  setKnowledgeJobStatus("Создание документа…");
  try {
    const meta = {
      ai_normalized: true,
      upload_method: kUploadFile ? "file" : "text",
      source_filename: kUploadFile?.name || "content.md",
    };
    const data = await api("/api/orch/knowledge/documents", {
      method: "POST",
      body: JSON.stringify({ title, content, metadata: meta, auto_index: false }),
    });
    await afterDocCreated(data.document_id, $("k-autoIndex").checked, true);
    resetKnowledgeModal();
  } catch (e) {
    $("k-wizardErr").textContent = String(e.message || e);
    setKnowledgeJobStatus("");
  }
}

const drop = $("k-drop");
drop.addEventListener("click", () => $("k-file").click());
drop.addEventListener("dragover", (e) => {
  e.preventDefault();
  drop.classList.add("drag");
});
drop.addEventListener("dragleave", () => drop.classList.remove("drag"));
drop.addEventListener("drop", (e) => {
  e.preventDefault();
  drop.classList.remove("drag");
  const f = e.dataTransfer?.files?.[0];
  if (f) onKnowledgeFilePicked(f);
});
async function onKnowledgeFilePicked(f) {
  if (!f) return;
  kUploadFile = f;
  kAiNormalized = false;
  drop.querySelector("strong").textContent = f.name;
  $("k-wizardErr").textContent = "";
  await normalizeUploadFile();
}

$("k-file").addEventListener("change", (e) => {
  const f = e.target.files?.[0];
  if (f) onKnowledgeFilePicked(f);
  e.target.value = "";
});
$("k-add-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const textMode = !$("k-panel-text").classList.contains("hidden");
  if (textMode) {
    if (!kAiNormalized && kUploadFile) {
      $("k-wizardErr").textContent = "Дождитесь окончания ИИ-подготовки файла.";
      return;
    }
    await uploadTextDoc();
  } else {
    $("k-wizardErr").textContent =
      "Выберите файл — откроется ИИ-подготовка. Или вставьте уже готовый Markdown на вкладке «Текст».";
  }
});
$("k-prepareAiDoc")?.addEventListener("click", () => {
  if (selectedDocId) prepareAiDocument(selectedDocId);
});

function stopJobPoll() {
  if (jobPollTimer) {
    clearInterval(jobPollTimer);
    jobPollTimer = null;
  }
}

async function pollJob(jobId) {
  stopJobPoll();
  const tick = async () => {
    try {
      const j = await api("/api/orch/jobs/" + encodeURIComponent(jobId));
      const p = j.progress || {};
      setKnowledgeJobStatus(
        `${j.status} · docs ${p.processed_documents || 0}/${p.total_documents || 0} · chunks ${p.total_chunks || 0}`,
      );
      if (j.status === "completed" || j.status === "failed") {
        stopJobPoll();
        toast(j.status === "completed" ? "Reindex завершён" : "Reindex failed");
        await loadDocList();
        if (selectedDocId) await selectDoc(selectedDocId);
      }
    } catch (e) {
      setKnowledgeJobStatus(String(e.message || e));
      stopJobPoll();
    }
  };
  await tick();
  jobPollTimer = setInterval(tick, 2000);
}

async function runReindex(mode, document_id) {
  $("k-errR").textContent = "";
  $("k-wizardErr").textContent = "";
  const body = document_id ? { mode, document_id } : { mode };
  try {
    const j = await api("/api/orch/knowledge/reindex", { method: "POST", body: JSON.stringify(body) });
    toast("Индексация: " + (j.job_id || ""));
    if (j.job_id) await pollJob(j.job_id);
  } catch (e) {
    const msg = String(e.message || e);
    $("k-errR").textContent = msg;
    $("k-wizardErr").textContent = msg;
  }
}

$("k-reindexFull").addEventListener("click", () => runReindex("full"));
$("k-reindexDoc").addEventListener("click", () => {
  if (selectedDocId) runReindex("document", selectedDocId);
});

// ---------- Prompts ----------

const PROMPT_SECTIONS = [
  {
    id: "role",
    title: "Роль и задача",
    hint: "Кто такой агент и зачем он пользователю",
    keys: ["system"],
    labels: { system: "Системная роль" },
  },
  {
    id: "rules",
    title: "Правила ответа",
    hint: "Честность, эскалация, работа с базой знаний",
    keys: ["answer_policy", "fallback"],
    labels: { answer_policy: "Как отвечать", fallback: "Если данных нет" },
  },
  {
    id: "style",
    title: "Стиль общения",
    hint: "Тон, длина, формат сообщений",
    keys: ["channel_style"],
    labels: { channel_style: "Стиль канала" },
  },
  {
    id: "tuning",
    title: "Журнал тюнинга",
    hint: "Не попадает в ответы бота — только история правок",
    keys: ["tuning_log"],
    labels: { tuning_log: "Журнал автотюнинга" },
  },
];

function setPromptTab(tab) {
  activePromptTab = tab;
  document.querySelectorAll("[data-ptab]").forEach((b) => {
    b.classList.toggle("active", b.dataset.ptab === tab);
  });
  $("p-panel-editor").classList.toggle("hidden", tab !== "editor");
  $("p-panel-tune").classList.toggle("hidden", tab !== "tune");
}

document.querySelectorAll("[data-ptab]").forEach((btn) => {
  btn.addEventListener("click", () => setPromptTab(btn.dataset.ptab));
});

const PROMPT_KEY_TO_SECTION = {};
for (const sec of PROMPT_SECTIONS) {
  for (const k of sec.keys) PROMPT_KEY_TO_SECTION[k] = sec;
}

function promptLabel(key, description) {
  for (const sec of PROMPT_SECTIONS) {
    if (sec.labels[key]) return sec.labels[key];
  }
  return (description || "").trim() || key;
}

function slugKey(text) {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_|_$/g, "")
    .slice(0, 48) || "custom_rule";
}

async function loadPromptList() {
  $("p-err").textContent = "";
  try {
    const data = await api("/api/orch/prompts");
    const items = data.items || [];
    const byKey = Object.fromEntries(items.map((p) => [p.prompt_key, p]));
    const list = $("p-list");
    list.innerHTML = "";

    const renderSection = (sec, keys) => {
      const present = keys.filter((k) => byKey[k]);
      if (!present.length) return;
      const head = document.createElement("div");
      head.className = "prompt-section-title";
      head.textContent = sec.title;
      list.appendChild(head);
      for (const key of present) {
        const p = byKey[key];
        const row = document.createElement("div");
        row.className = "prompt-row" + (key === selectedPromptKey ? " active" : "");
        row.innerHTML = `${esc(promptLabel(key, p.description))}<small>${esc(key)} · v${p.latest_version}</small>`;
        row.addEventListener("click", () => selectPrompt(key));
        list.appendChild(row);
      }
    };

    for (const sec of PROMPT_SECTIONS) {
      renderSection(sec, sec.keys);
    }

    const known = new Set(PROMPT_SECTIONS.flatMap((s) => s.keys));
    const extra = items.filter((p) => !known.has(p.prompt_key)).sort((a, b) => a.prompt_key.localeCompare(b.prompt_key));
    if (extra.length) {
      renderSection(
        { title: "Дополнительные правила", labels: {} },
        extra.map((p) => p.prompt_key),
      );
    }
    if (!items.length) {
      list.innerHTML = '<p class="empty-hint" style="padding:12px">Нет блоков. Создайте первый кнопкой выше.</p>';
    }
  } catch (e) {
    $("p-err").textContent = String(e.message || e);
  }
}

function showPromptEditor(show) {
  $("p-editorEmpty").classList.toggle("hidden", show);
  $("p-editorForm").classList.toggle("hidden", !show);
}

async function selectPrompt(key) {
  selectedPromptKey = key;
  $("p-err").textContent = "";
  showPromptEditor(true);
  const sec = PROMPT_KEY_TO_SECTION[key];
  $("p-sectionLabel").textContent = sec ? sec.title + " · " + promptLabel(key, "") : promptLabel(key, "");
  $("p-keyHint").textContent = "ключ: " + key;
  await loadPromptList();
  try {
    const d = await api("/api/orch/prompts/" + encodeURIComponent(key));
    $("p-content").value = String(d.content || "");
    const items = await api("/api/orch/prompts");
    const item = (items.items || []).find((x) => x.prompt_key === key);
    $("p-desc").value = item?.description || "";
  } catch (e) {
    $("p-err").textContent = String(e.message || e);
  }
}

$("p-save").addEventListener("click", async () => {
  if (!selectedPromptKey) return;
  const content = ($("p-content").value || "").trim();
  if (!content) {
    $("p-err").textContent = "Текст инструкции не может быть пустым.";
    return;
  }
  try {
    await api("/api/orch/prompts/" + encodeURIComponent(selectedPromptKey), {
      method: "PUT",
      body: JSON.stringify({ content }),
    });
    toast("Сохранено — бот использует при следующем ответе");
    await loadPromptList();
  } catch (e) {
    $("p-err").textContent = String(e.message || e);
  }
});

const createDlg = $("p-create-dialog");
$("p-createOpen").addEventListener("click", () => {
  $("p-create-type").value = "custom";
  $("p-create-key-wrap").classList.remove("hidden");
  $("p-create-title").value = "";
  $("p-create-key").value = "";
  $("p-create-content").value = "";
  createDlg.showModal();
});
$("p-create-cancel").addEventListener("click", () => createDlg.close());
$("p-create-type").addEventListener("change", () => {
  const t = $("p-create-type").value;
  const isCustom = t === "custom";
  $("p-create-key-wrap").classList.toggle("hidden", !isCustom);
  if (!isCustom) {
    const labels = {
      system: "Системная роль",
      answer_policy: "Правила ответа",
      channel_style: "Стиль общения",
      fallback: "Если нет данных в базе",
    };
    $("p-create-title").value = labels[t] || t;
    $("p-create-key").value = t;
  }
});
function renderTunePreview(data) {
  const box = $("p-tune-results");
  box.innerHTML = "";
  const sum = document.createElement("div");
  sum.className = "tune-summary";
  sum.innerHTML = `<strong>Итог:</strong> ${esc(data.summary || "")}`;
  box.appendChild(sum);
  if (data.log_entry) {
    const log = document.createElement("p");
    log.className = "field-hint";
    log.innerHTML = `<strong>Запись в журнал:</strong> ${esc(data.log_entry)}`;
    box.appendChild(log);
  }
  const changes = data.changes || [];
  if (!changes.length) {
    box.insertAdjacentHTML(
      "beforeend",
      '<p class="empty-hint">Правок в блоках не предложено — возможно, нужна база знаний, а не промпт.</p>',
    );
    $("p-tune-apply").classList.add("hidden");
    return;
  }
  for (const ch of changes) {
    const card = document.createElement("div");
    card.className = "tune-change";
    const actionLabel = ch.action === "create" ? "новый блок" : "обновление";
    card.innerHTML = `
      <h4>${esc(ch.prompt_key)} · ${esc(actionLabel)}</h4>
      <div class="meta">${esc(ch.rationale || "")}</div>
      <pre>${esc(ch.content || "")}</pre>
    `;
    box.appendChild(card);
  }
  $("p-tune-apply").classList.remove("hidden");
}

$("p-tune-run").addEventListener("click", async () => {
  const feedback = ($("p-tune-feedback").value || "").trim();
  $("p-tune-err").textContent = "";
  $("p-tune-status").textContent = "";
  pendingTune = null;
  $("p-tune-apply").classList.add("hidden");
  $("p-tune-results").innerHTML = "";
  if (!feedback) {
    $("p-tune-err").textContent = "Опишите, что не устраивает в ответах.";
    return;
  }
  $("p-tune-run").disabled = true;
  $("p-tune-status").textContent = "ИИ анализирует промпты…";
  try {
    const data = await api("/api/orch/prompts/tune", {
      method: "POST",
      body: JSON.stringify({ feedback }),
    });
    pendingTune = data;
    renderTunePreview(data);
    $("p-tune-status").textContent = "Модель: " + (data.model || "—");
    toast("Предпросмотр готов");
  } catch (e) {
    $("p-tune-err").textContent = String(e.message || e);
    $("p-tune-status").textContent = "";
  } finally {
    $("p-tune-run").disabled = false;
  }
});

$("p-tune-apply").addEventListener("click", async () => {
  if (!pendingTune) return;
  $("p-tune-err").textContent = "";
  $("p-tune-apply").disabled = true;
  try {
    const data = await api("/api/orch/prompts/tune/apply", {
      method: "POST",
      body: JSON.stringify({
        changes: pendingTune.changes || [],
        log_entry: pendingTune.log_entry || "",
      }),
    });
    toast(data.summary || "Промпты обновлены");
    pendingTune = null;
    $("p-tune-apply").classList.add("hidden");
    $("p-tune-feedback").value = "";
    const lines = (data.applied || [])
      .map((a) => `${a.prompt_key} → v${a.version}`)
      .join(", ");
    $("p-tune-results").innerHTML =
      `<div class="tune-summary"><strong>Применено:</strong> ${esc(lines || "журнал")}</div>`;
    await loadPromptList();
    setPromptTab("editor");
  } catch (e) {
    $("p-tune-err").textContent = String(e.message || e);
  } finally {
    $("p-tune-apply").disabled = false;
  }
});

$("p-create-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const type = $("p-create-type").value;
  let key = type === "custom" ? ($("p-create-key").value || "").trim() : type;
  const title = ($("p-create-title").value || "").trim();
  const content = ($("p-create-content").value || "").trim();
  if (type === "custom" && !key) key = slugKey(title);
  if (!/^[a-z][a-z0-9_]*$/.test(key)) {
    $("p-err").textContent = "Ключ: только латиница, цифры и _, например rules_billing";
    createDlg.close();
    return;
  }
  if (!content) {
    $("p-err").textContent = "Введите текст инструкции.";
    createDlg.close();
    return;
  }
  try {
    await api("/api/orch/prompts", {
      method: "POST",
      body: JSON.stringify({
        prompt_key: key,
        description: title || key,
        content,
      }),
    });
    createDlg.close();
    toast("Блок создан");
    await loadPromptList();
    await selectPrompt(key);
  } catch (err) {
    $("p-err").textContent = String(err.message || err);
    createDlg.close();
  }
});

// ---------- Init ----------

applyEscalationDeepLink();
pingHealth();
setInterval(pingHealth, 30000);

document.addEventListener("visibilitychange", () => {
  if (document.visibilityState !== "visible") return;
  pingHealth();
  if (activeView === "chats" && selectedChatId) loadChatMessages(selectedChatId);
});
