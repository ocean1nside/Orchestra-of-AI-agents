// Simple SPA navigation + routing
const $ = (id) => document.getElementById(id);

function setTopNav(view) {
  document.querySelectorAll("header nav button[data-view]").forEach((b) => b.classList.toggle("active", b.dataset.view === view));
  document.querySelectorAll(".view").forEach((v) => v.classList.toggle("active", v.id === `view-${view}`));
  document.body.classList.toggle("view-agents", view === "agents");
}

function setAgentSelected(agentId) {
  document.querySelectorAll(".agent-item[data-agent]").forEach((el) =>
    el.classList.toggle("active", el.dataset.agent === agentId),
  );
  const hasAgent = Boolean(agentId);
  $("agentTitle").textContent = agentId || "Выберите агента";
  $("agentTabs").style.display = hasAgent ? "flex" : "none";
  $("agentEmpty").style.display = hasAgent ? "none" : "block";
  $("agentBody").style.display = hasAgent ? "flex" : "none";
}

function setAgentTab(tab) {
  document.querySelectorAll("#agentTabs button[data-tab]").forEach((b) => b.classList.toggle("active", b.dataset.tab === tab));
  document.querySelectorAll("#agentBody .tab").forEach((t) => t.classList.toggle("active", t.id === `tab-${tab}`));
}

function navigate(path) {
  history.pushState({}, "", path);
  renderRoute();
}

function renderRoute() {
  const p = location.pathname || "/";
  if (p === "/" || p === "/widjet") {
    setTopNav("widget");
    return;
  }
  if (p === "/agents") {
    setTopNav("agents");
    setAgentSelected(null);
    return;
  }
  if (p.startsWith("/agents/")) {
    const agentId = decodeURIComponent(p.slice("/agents/".length));
    setTopNav("agents");
    setAgentSelected(agentId);
    // Default tab
    setAgentTab("chats");
    return;
  }
  // Fallback
  setTopNav("widget");
}

window.addEventListener("popstate", renderRoute);

// Render route ASAP to avoid layout flicker
renderRoute();

document.querySelectorAll("header nav button[data-view]").forEach((btn) => {
  btn.addEventListener("click", () => {
    const view = btn.dataset.view;
    navigate(view === "agents" ? "/agents" : "/widjet");
  });
});

// Agent list click
document.querySelectorAll(".agent-item[data-agent]").forEach((el) => {
  el.addEventListener("click", () => navigate("/agents/" + encodeURIComponent(el.dataset.agent)));
});

// Agent tabs click
document.querySelectorAll("#agentTabs button[data-tab]").forEach((btn) => {
  btn.addEventListener("click", () => setAgentTab(btn.dataset.tab));
});

// ---------- Widget view ----------

const STORAGE_CONV = "console_widget_conversation_id";
const STORAGE_USER = "console_widget_user_id";

function esc(s) {
  const d = document.createElement("div");
  d.textContent = s;
  return d.innerHTML;
}

function wLoadIds() {
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
  $("f-conv").value = conv;
  $("f-user").value = user;
}

function wSaveIds() {
  localStorage.setItem(STORAGE_CONV, $("f-conv").value.trim());
  localStorage.setItem(STORAGE_USER, $("f-user").value.trim());
}

function wAppendBubble(role, html) {
  const box = $("w-messages");
  const div = document.createElement("div");
  div.className = "bubble " + role;
  div.innerHTML = html;
  box.appendChild(div);
  box.scrollTop = box.scrollHeight;
}

(function initWidget() {
  const root = $("w-root");
  $("w-launcher").onclick = () => root.classList.add("open");
  $("w-close").onclick = () => root.classList.remove("open");
  $("f-conv").addEventListener("change", wSaveIds);
  $("f-user").addEventListener("change", wSaveIds);
  wLoadIds();

  async function sendMessage() {
    const text = $("w-input").value.trim();
    if (!text) return;
    const conversation_id = $("f-conv").value.trim();
    const user_id = $("f-user").value.trim();
    if (!conversation_id || !user_id) {
      wAppendBubble("err", '<div class="who">Ошибка</div>Заполни conversation_id и user_id.');
      return;
    }

    wSaveIds();
    wAppendBubble("user", `<div class="who">Вы</div><div>${esc(text)}</div>`);
    $("w-input").value = "";
    $("w-send").disabled = true;

    try {
      const r = await fetch("/api/widget/invoke", {
        method: "POST",
        cache: "no-store",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          channel: "widget",
          conversation_id,
          user_id,
          message: text,
          context: { source: "console/widget" },
        }),
      });
      const data = await r.json().catch(() => ({}));
      if (!r.ok) {
        const d = data.detail;
        const msg =
          typeof d === "string"
            ? d
            : Array.isArray(d)
              ? d.map((x) => x.msg || JSON.stringify(x)).join("; ")
              : JSON.stringify(data);
        wAppendBubble("err", `<div class="who">HTTP ${r.status}</div><div>${esc(msg)}</div>`);
        return;
      }

      const meta = data.meta || {};
      const muted = meta.ai_muted === true;
      const holder = meta.conversation_holder === "human" ? " (контроль: менеджер)" : "";

      let body = (data.answer || "").trim();
      if (muted) body = body || "ИИ не отвечает (диалог у менеджера).";

      let srcHtml = "";
      if (Array.isArray(data.sources) && data.sources.length) {
        const lines = data.sources.slice(0, 8).map((s) => esc(s.title || s.chunk_id || ""));
        srcHtml = `<div class="src">Источники: ${lines.join(" · ")}</div>`;
      }

      wAppendBubble(
        "bot",
        `<div class="who">Ассистент${esc(holder)}</div><div>${esc(body)}</div>${srcHtml}`,
      );
    } catch (e) {
      wAppendBubble("err", `<div class="who">Сеть</div><div>${esc(String(e.message || e))}</div>`);
    } finally {
      $("w-send").disabled = false;
    }
  }

  $("w-send").onclick = sendMessage;
  $("w-input").addEventListener("keydown", (ev) => {
    if (ev.key === "Enter" && !ev.shiftKey) {
      ev.preventDefault();
      sendMessage();
    }
  });
})();

// ---------- Shared fetch helper ----------

async function api(path, opts = {}) {
  const r = await fetch(path, {
    cache: "no-store",
    ...opts,
    headers: { "Content-Type": "application/json", ...(opts.headers || {}) },
  });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) {
    const d = data.detail;
    const msg =
      typeof d === "string"
        ? d
        : Array.isArray(d)
          ? d.map((x) => x.msg || JSON.stringify(x)).join("; ")
          : data.message || JSON.stringify(data);
    throw new Error(msg || r.statusText);
  }
  return data;
}

// ---------- Chats tab (operator API) ----------

let selectedChatId = null;
let pollList = null;
let pollMsg = null;

async function loadChatList() {
  $("chatErrL").textContent = "";
  try {
    const data = await api("/api/operator/conversations?limit=100");
    const list = $("chatList");
    list.innerHTML = "";
    for (const c of data.items || []) {
      const div = document.createElement("div");
      div.className = "chat-item" + (c.id === selectedChatId ? " active" : "");
      div.dataset.id = c.id;
      const h = c.conversation_holder === "human" ? "Менеджер" : "ИИ";
      div.innerHTML = `<div class="id">${esc(c.id)}</div><div class="meta">${esc(c.channel)} · ${h}</div>`;
      div.onclick = () => selectChat(c.id);
      list.appendChild(div);
    }
  } catch (e) {
    $("chatErrL").textContent = String(e.message || e);
  }
}

function stopMsgPoll() {
  if (pollMsg) {
    clearInterval(pollMsg);
    pollMsg = null;
  }
}

async function loadChatDetailAndMessages(id) {
  $("chatErrR").textContent = "";
  $("chatDetailPanel").style.display = "block";
  try {
    const d = await api("/api/operator/conversations/" + encodeURIComponent(id));
    $("dChannel").textContent = d.channel;
    $("dUser").textContent = d.user_id;
    $("dHolder").textContent = d.conversation_holder === "human" ? "Менеджер (ИИ молчит)" : "ИИ";
    const m = await api(
      "/api/operator/conversations/" + encodeURIComponent(id) + "/messages?limit=500",
    );
    const box = $("chatMessages");
    box.innerHTML = "";
    for (const msg of m.messages || []) {
      const div = document.createElement("div");
      div.className =
        "msg " +
        (msg.role === "user" ? "user" : msg.role === "operator" ? "operator" : "assistant");
      div.innerHTML = `<div class="role">${esc(msg.role)} · ${esc(
        String(msg.created_at),
      )}</div><div>${esc(msg.content)}</div>`;
      box.appendChild(div);
    }
    box.scrollTop = box.scrollHeight;
  } catch (e) {
    $("chatErrR").textContent = String(e.message || e);
  }
}

async function selectChat(id) {
  selectedChatId = id;
  document.querySelectorAll(".chat-item").forEach((el) => {
    el.classList.toggle("active", el.dataset.id === id);
  });
  stopMsgPoll();
  await loadChatDetailAndMessages(id);
  pollMsg = setInterval(() => loadChatDetailAndMessages(id), 2000);
}

$("btnAi").onclick = async () => {
  if (!selectedChatId) return;
  $("chatErrR").textContent = "";
  try {
    await api("/api/operator/conversations/" + encodeURIComponent(selectedChatId) + "/control", {
      method: "POST",
      body: JSON.stringify({ holder: "ai" }),
    });
    await loadChatList();
    await loadChatDetailAndMessages(selectedChatId);
  } catch (e) {
    $("chatErrR").textContent = String(e.message || e);
  }
};

$("btnHuman").onclick = async () => {
  if (!selectedChatId) return;
  $("chatErrR").textContent = "";
  try {
    await api(
      "/api/operator/conversations/" + encodeURIComponent(selectedChatId) + "/control",
      {
        method: "POST",
        body: JSON.stringify({ holder: "human" }),
      },
    );
    await loadChatList();
    await loadChatDetailAndMessages(selectedChatId);
  } catch (e) {
    $("chatErrR").textContent = String(e.message || e);
  }
};

$("btnSend").onclick = async () => {
  if (!selectedChatId) return;
  const text = $("outText").value.trim();
  if (!text) return;
  $("chatErrR").textContent = "";
  try {
    await api("/api/operator/conversations/" + encodeURIComponent(selectedChatId) + "/reply", {
      method: "POST",
      body: JSON.stringify({ text }),
    });
    $("outText").value = "";
    await loadChatDetailAndMessages(selectedChatId);
    await loadChatList();
  } catch (e) {
    $("chatErrR").textContent = String(e.message || e);
  }
};

pollList = setInterval(loadChatList, 5000);
loadChatList();

document.addEventListener("visibilitychange", () => {
  if (document.visibilityState !== "visible") return;
  loadChatList();
  if (selectedChatId) loadChatDetailAndMessages(selectedChatId);
});

// ---------- Knowledge tab ----------

let kDocsCache = [];
let kSelectedId = null;

function makeChunksFromContent(content, size = 600) {
  const chunks = [];
  const text = String(content || "");
  for (let i = 0; i < text.length; i += size) {
    chunks.push(text.slice(i, i + size));
  }
  return chunks;
}

async function kLoadList() {
  $("kErrL").textContent = "";
  try {
    const data = await api("/api/orch/knowledge/documents");
    kDocsCache = data.items || [];
    const list = $("k-docs");
    list.innerHTML = "";
    for (const d of kDocsCache) {
      const div = document.createElement("div");
      div.className = "k-doc" + (d.id === kSelectedId ? " active" : "");
      div.dataset.id = d.id;
      div.innerHTML = `<div class="title">${esc(d.title || d.id)}</div><div class="meta">${esc(
        d.status || "",
      )}</div>`;
      div.onclick = () => kSelect(d.id);
      list.appendChild(div);
    }
  } catch (e) {
    $("kErrL").textContent = String(e.message || e);
  }
}

async function kSelect(id) {
  kSelectedId = id;
  document.querySelectorAll(".k-doc").forEach((el) => {
    el.classList.toggle("active", el.dataset.id === id);
  });
  $("kErrR").textContent = "";
  $("kTitle").textContent = "Загрузка…";
  $("kChunks").innerHTML = "";
  try {
    const d = await api("/api/orch/knowledge/documents/" + encodeURIComponent(id));
    $("kTitle").textContent = d.title || d.id || "Документ";
    const chunks = makeChunksFromContent(d.content || "");
    const box = $("kChunks");
    box.innerHTML = "";
    if (!chunks.length) {
      box.innerHTML = "<p>Пустой документ.</p>";
      return;
    }
    chunks.forEach((c, i) => {
      const div = document.createElement("div");
      div.className = "k-chunk";
      div.innerHTML = `<small>Chunk #${i + 1}</small><div>${esc(c)}</div>`;
      box.appendChild(div);
    });
  } catch (e) {
    $("kErrR").textContent = String(e.message || e);
  }
}

$("kReload").onclick = () => kLoadList();

$("kAdd").onclick = async () => {
  const title = $("kNewTitle").value.trim();
  const content = $("kNewContent").value.trim();
  if (!title || !content) {
    $("kErrR").textContent = "Заполните название и содержимое.";
    return;
  }
  $("kErrR").textContent = "";
  try {
    await api("/api/orch/knowledge/documents", {
      method: "POST",
      body: JSON.stringify({ title, content, metadata: {}, auto_index: false }),
    });
    $("kNewTitle").value = "";
    $("kNewContent").value = "";
    await kLoadList();
  } catch (e) {
    $("kErrR").textContent = String(e.message || e);
  }
};

// ---------- Prompts tab ----------

$("pLoad").onclick = async () => {
  const key = $("pKey").value.trim();
  $("pErr").textContent = "";
  $("pContent").value = "";
  if (!key) {
    $("pErr").textContent = "Укажите prompt_key.";
    return;
  }
  try {
    const d = await api("/api/orch/prompts/" + encodeURIComponent(key));
    $("pContent").value = String(d.content || "");
  } catch (e) {
    $("pErr").textContent = String(e.message || e);
  }
};

$("pSave").onclick = async () => {
  const key = $("pKey").value.trim();
  const content = $("pContent").value;
  $("pErr").textContent = "";
  if (!key) {
    $("pErr").textContent = "Укажите prompt_key.";
    return;
  }
  try {
    await api("/api/orch/prompts/" + encodeURIComponent(key), {
      method: "PUT",
      body: JSON.stringify({ content }),
    });
  } catch (e) {
    $("pErr").textContent = String(e.message || e);
  }
};


