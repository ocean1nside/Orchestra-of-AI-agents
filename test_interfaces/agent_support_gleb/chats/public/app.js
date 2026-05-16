let selectedId = null;
let pollList = null;
let pollMsg = null;

const $ = (id) => document.getElementById(id);

async function api(path, opts = {}) {
  const r = await fetch(path, {
    cache: "no-store",
    ...opts,
    headers: { "Content-Type": "application/json", ...opts.headers },
  });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) {
    const d = data.detail;
    let msg =
      typeof d === "string"
        ? d
        : Array.isArray(d)
          ? d.map((x) => x.msg || JSON.stringify(x)).join("; ")
          : data.message || JSON.stringify(data);
    throw new Error(msg || r.statusText);
  }
  return data;
}

function esc(s) {
  const d = document.createElement("div");
  d.textContent = s;
  return d.innerHTML;
}

async function loadList() {
  $("errL").textContent = "";
  try {
    const data = await api("/api/conversations?limit=100");
    const list = $("chatList");
    list.innerHTML = "";
    for (const c of data.items || []) {
      const div = document.createElement("div");
      div.className = "chat-item" + (c.id === selectedId ? " active" : "");
      div.dataset.id = c.id;
      const h = c.conversation_holder === "human" ? "Менеджер" : "ИИ";
      div.innerHTML = `<div class="id">${esc(c.id)}</div><div class="meta">${esc(c.channel)} · ${h}</div>`;
      div.onclick = () => selectChat(c.id);
      list.appendChild(div);
    }
  } catch (e) {
    $("errL").textContent = String(e.message || e);
  }
}

function stopMsgPoll() {
  if (pollMsg) {
    clearInterval(pollMsg);
    pollMsg = null;
  }
}

async function loadDetailAndMessages(id) {
  $("errR").textContent = "";
  $("detailPanel").style.display = "block";
  try {
    const d = await api("/api/conversations/" + encodeURIComponent(id));
    $("dChannel").textContent = d.channel;
    $("dUser").textContent = d.user_id;
    $("dHolder").textContent = d.conversation_holder === "human" ? "Менеджер (ИИ молчит)" : "ИИ";
    const m = await api("/api/conversations/" + encodeURIComponent(id) + "/messages?limit=500");
    const box = $("messages");
    box.innerHTML = "";
    for (const msg of m.messages || []) {
      const div = document.createElement("div");
      div.className = "msg " + (msg.role === "user" ? "user" : msg.role === "operator" ? "operator" : "assistant");
      div.innerHTML = `<div class="role">${esc(msg.role)} · ${esc(String(msg.created_at))}</div><div>${esc(msg.content)}</div>`;
      box.appendChild(div);
    }
    box.scrollTop = box.scrollHeight;
  } catch (e) {
    $("errR").textContent = String(e.message || e);
  }
}

async function selectChat(id) {
  selectedId = id;
  document.querySelectorAll(".chat-item").forEach((el) => {
    el.classList.toggle("active", el.dataset.id === id);
  });
  stopMsgPoll();
  await loadDetailAndMessages(id);
  pollMsg = setInterval(() => loadDetailAndMessages(id), 2000);
}

$("btnAi").onclick = async () => {
  if (!selectedId) return;
  $("errR").textContent = "";
  try {
    await api("/api/conversations/" + encodeURIComponent(selectedId) + "/control", {
      method: "POST",
      body: JSON.stringify({ holder: "ai" }),
    });
    await loadList();
    await loadDetailAndMessages(selectedId);
  } catch (e) {
    $("errR").textContent = String(e.message || e);
  }
};

$("btnHuman").onclick = async () => {
  if (!selectedId) return;
  $("errR").textContent = "";
  try {
    await api("/api/conversations/" + encodeURIComponent(selectedId) + "/control", {
      method: "POST",
      body: JSON.stringify({ holder: "human" }),
    });
    await loadList();
    await loadDetailAndMessages(selectedId);
  } catch (e) {
    $("errR").textContent = String(e.message || e);
  }
};

$("btnSend").onclick = async () => {
  if (!selectedId) return;
  const text = $("outText").value.trim();
  if (!text) return;
  $("errR").textContent = "";
  try {
    await api("/api/conversations/" + encodeURIComponent(selectedId) + "/reply", {
      method: "POST",
      body: JSON.stringify({ text }),
    });
    $("outText").value = "";
    await loadDetailAndMessages(selectedId);
    await loadList();
  } catch (e) {
    $("errR").textContent = String(e.message || e);
  }
};

pollList = setInterval(loadList, 5000);
loadList();

document.addEventListener("visibilitychange", () => {
  if (document.visibilityState !== "visible") return;
  loadList();
  if (selectedId) loadDetailAndMessages(selectedId);
});
