const $ = (id) => document.getElementById(id);

const VIEW_META = {
  widget: { title: "Виджет", subtitle: "Тест канала widget → POST /api/v1/widget/invoke" },
  chats: { title: "Диалоги", subtitle: "Operator API: все каналы, ответы, контроль ИИ/менеджер" },
  knowledge: { title: "База знаний", subtitle: "Оркестратор: документы, загрузка файлов, reindex" },
  prompts: { title: "Промпты", subtitle: "Шаблоны в Postgres (агент пока читает файлы в образе)" },
  system: { title: "Система", subtitle: "Health агента, оркестратора и инфраструктуры" },
};

let activeView = "widget";
let pollChats = null;
let pollMsgs = null;
let selectedChatId = null;
let selectedDocId = null;
let selectedPromptKey = null;
let jobPollTimer = null;

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

async function api(path, opts = {}) {
  const r = await fetch(path, {
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
  if (view === "prompts") loadPromptList();
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
    const r = await fetch("/api/health/agent", { cache: "no-store" });
    setDot("dot-agent", r.ok);
  } catch {
    setDot("dot-agent", false);
  }
  try {
    const r = await fetch("/api/health/orchestrator", { cache: "no-store" });
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
      const r = await fetch(c.url, { cache: "no-store" });
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

async function loadDocList() {
  $("k-errL").textContent = "";
  try {
    const data = await api("/api/orch/knowledge/documents");
    const list = $("k-list");
    list.innerHTML = "";
    for (const d of data.items || []) {
      const id = d.document_id || d.id;
      const row = document.createElement("div");
      row.className = "doc-row" + (id === selectedDocId ? " active" : "");
      row.innerHTML = `<div class="title">${esc(d.title || id)}</div><div class="status">${esc(d.status || "")}</div>`;
      row.addEventListener("click", () => selectDoc(id));
      list.appendChild(row);
    }
    $("k-reindexDoc").disabled = !selectedDocId;
  } catch (e) {
    $("k-errL").textContent = String(e.message || e);
  }
}

async function selectDoc(id) {
  selectedDocId = id;
  $("k-reindexDoc").disabled = !id;
  $("k-errR").textContent = "";
  await loadDocList();
  try {
    const d = await api("/api/orch/knowledge/documents/" + encodeURIComponent(id));
    const meta = d.metadata && Object.keys(d.metadata).length ? JSON.stringify(d.metadata, null, 2) : "—";
    $("k-detail").innerHTML = `
      <h3 style="margin:0 0 8px">${esc(d.title || id)}</h3>
      <p style="font-size:13px;color:var(--muted);margin:0 0 12px">
        Статус: <strong>${esc(d.status)}</strong> · ID: <code>${esc(d.document_id || id)}</code>
      </p>
      <p style="font-size:13px;color:var(--muted)">
        Текст хранится в <code>storage/knowledge/originals/</code> — API отдаёт только метаданные.
        После загрузки или правок запустите reindex.
      </p>
      <h4 style="margin:16px 0 8px">metadata</h4>
      <pre style="font-size:12px;background:#f8fafc;padding:10px;border-radius:8px;overflow:auto">${esc(meta)}</pre>
      <div class="toolbar" style="margin-top:12px">
        <button type="button" class="btn btn-danger" id="k-delete">Удалить документ</button>
      </div>
    `;
    $("k-delete").onclick = async () => {
      if (!confirm("Удалить документ из базы?")) return;
      try {
        await api("/api/orch/knowledge/documents/" + encodeURIComponent(id), { method: "DELETE" });
        selectedDocId = null;
        toast("Документ удалён");
        await loadDocList();
        $("k-detail").innerHTML = "<p style=\"color:var(--muted)\">Выберите документ или загрузите файл.</p>";
      } catch (err) {
        $("k-errR").textContent = String(err.message || err);
      }
    };
  } catch (e) {
    $("k-errR").textContent = String(e.message || e);
  }
}

async function uploadFile(file) {
  if (!file) return;
  $("k-errR").textContent = "";
  $("k-jobStatus").textContent = "Загрузка…";
  try {
    const buf = await file.arrayBuffer();
    const r = await fetch("/api/orch/knowledge/documents/upload", {
      method: "POST",
      headers: {
        "X-Filename": encodeURIComponent(file.name),
        "Content-Type": file.type || "application/octet-stream",
      },
      body: buf,
    });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(errMsg(data, r.status));
    toast("Файл загружен: " + (data.document_id || ""));
    $("k-jobStatus").textContent = "";
    await loadDocList();
    if (data.document_id) await selectDoc(data.document_id);
  } catch (e) {
    $("k-errR").textContent = String(e.message || e);
    $("k-jobStatus").textContent = "";
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
  if (f) uploadFile(f);
});
$("k-file").addEventListener("change", (e) => {
  const f = e.target.files?.[0];
  if (f) uploadFile(f);
  e.target.value = "";
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
      $("k-jobStatus").textContent = `${j.status} · docs ${p.processed_documents || 0}/${p.total_documents || 0} · chunks ${p.total_chunks || 0}`;
      if (j.status === "completed" || j.status === "failed") {
        stopJobPoll();
        toast(j.status === "completed" ? "Reindex завершён" : "Reindex failed");
        await loadDocList();
        if (selectedDocId) await selectDoc(selectedDocId);
      }
    } catch (e) {
      $("k-jobStatus").textContent = String(e.message || e);
      stopJobPoll();
    }
  };
  await tick();
  jobPollTimer = setInterval(tick, 2000);
}

async function runReindex(mode, document_id) {
  $("k-errR").textContent = "";
  const body = document_id ? { mode, document_id } : { mode };
  try {
    const j = await api("/api/orch/knowledge/reindex", { method: "POST", body: JSON.stringify(body) });
    toast("Job: " + (j.job_id || ""));
    if (j.job_id) await pollJob(j.job_id);
  } catch (e) {
    $("k-errR").textContent = String(e.message || e);
  }
}

$("k-reindexFull").addEventListener("click", () => runReindex("full"));
$("k-reindexDoc").addEventListener("click", () => {
  if (selectedDocId) runReindex("document", selectedDocId);
});

// ---------- Prompts ----------

async function loadPromptList() {
  $("p-err").textContent = "";
  try {
    const data = await api("/api/orch/prompts");
    const list = $("p-list");
    list.innerHTML = "";
    for (const p of data.items || []) {
      const row = document.createElement("div");
      row.className = "prompt-row" + (p.prompt_key === selectedPromptKey ? " active" : "");
      row.innerHTML = `${esc(p.prompt_key)}<small>v${p.latest_version} · ${esc(p.description || "")}</small>`;
      row.addEventListener("click", () => selectPrompt(p.prompt_key));
      list.appendChild(row);
    }
  } catch (e) {
    $("p-err").textContent = String(e.message || e);
  }
}

async function selectPrompt(key) {
  selectedPromptKey = key;
  $("p-keyLabel").textContent = key;
  $("p-save").disabled = false;
  $("p-content").disabled = false;
  $("p-err").textContent = "";
  await loadPromptList();
  try {
    const d = await api("/api/orch/prompts/" + encodeURIComponent(key));
    $("p-content").value = String(d.content || "");
  } catch (e) {
    $("p-err").textContent = String(e.message || e);
  }
}

$("p-save").addEventListener("click", async () => {
  if (!selectedPromptKey) return;
  try {
    await api("/api/orch/prompts/" + encodeURIComponent(selectedPromptKey), {
      method: "PUT",
      body: JSON.stringify({ content: $("p-content").value }),
    });
    toast("Промпт сохранён");
    await loadPromptList();
  } catch (e) {
    $("p-err").textContent = String(e.message || e);
  }
});

// ---------- Init ----------

pingHealth();
setInterval(pingHealth, 30000);

document.addEventListener("visibilitychange", () => {
  if (document.visibilityState !== "visible") return;
  pingHealth();
  if (activeView === "chats" && selectedChatId) loadChatMessages(selectedChatId);
});
