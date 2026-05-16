const STORAGE_CONV = "widget_test_conversation_id";
const STORAGE_USER = "widget_test_user_id";

const $ = (id) => document.getElementById(id);

function loadIds() {
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

function saveIds() {
  localStorage.setItem(STORAGE_CONV, $("f-conv").value.trim());
  localStorage.setItem(STORAGE_USER, $("f-user").value.trim());
}

function esc(s) {
  const d = document.createElement("div");
  d.textContent = s;
  return d.innerHTML;
}

function appendBubble(role, html) {
  const box = $("w-messages");
  const div = document.createElement("div");
  div.className = "bubble " + role;
  div.innerHTML = html;
  box.appendChild(div);
  box.scrollTop = box.scrollHeight;
}

const root = $("w-root");
$("w-launcher").onclick = () => root.classList.add("open");
$("w-close").onclick = () => root.classList.remove("open");

$("f-conv").addEventListener("change", saveIds);
$("f-user").addEventListener("change", saveIds);

loadIds();

async function sendMessage() {
  const text = $("w-input").value.trim();
  if (!text) return;
  const conversation_id = $("f-conv").value.trim();
  const user_id = $("f-user").value.trim();
  if (!conversation_id || !user_id) {
    appendBubble("err", '<div class="who">Ошибка</div>Заполни conversation_id и user_id.');
    return;
  }

  saveIds();
  appendBubble("user", `<div class="who">Вы</div><div>${esc(text)}</div>`);
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
        context: { source: "test_interfaces/widget" },
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
      appendBubble("err", `<div class="who">HTTP ${r.status}</div><div>${esc(msg)}</div>`);
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

    appendBubble(
      "bot",
      `<div class="who">Ассистент${esc(holder)}</div><div>${esc(body)}</div>${srcHtml}`,
    );
  } catch (e) {
    appendBubble("err", `<div class="who">Сеть</div><div>${esc(String(e.message || e))}</div>`);
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
