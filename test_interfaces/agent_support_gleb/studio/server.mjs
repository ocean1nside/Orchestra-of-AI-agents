import dotenv from "dotenv";
import express from "express";
import { readFileSync } from "fs";
import { dirname, join } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
dotenv.config({ path: join(__dirname, ".env.local") });
dotenv.config({ path: join(__dirname, ".env") });

const AGENT_URL = (process.env.AGENT_URL || "http://127.0.0.1:8010").replace(/\/$/, "");
const ORCH_URL = (process.env.ORCHESTRATOR_URL || "http://127.0.0.1:8000").replace(/\/$/, "");
const ORCH_API_KEY = (process.env.ORCHESTRATOR_API_KEY || process.env.API_KEY_DEV || "").trim();
const WIDGET_API_KEY = (process.env.WIDGET_API_KEY || "").trim();
const OPERATOR_API_KEY = (process.env.OPERATOR_API_KEY || WIDGET_API_KEY).trim();
const PORT = Number(process.env.PORT || 8790);

if (!WIDGET_API_KEY || !OPERATOR_API_KEY) {
  console.error("Set WIDGET_API_KEY (and optionally OPERATOR_API_KEY) in .env.local");
  process.exit(1);
}

function sendJson(res, status, body) {
  res.setHeader("Cache-Control", "no-store");
  res.status(status).json(body);
}

async function proxyJson(targetUrl, { headers = {}, method = "GET", body } = {}) {
  const r = await fetch(targetUrl, {
    method,
    cache: "no-store",
    headers: { Accept: "application/json", ...headers },
    body,
  });
  const text = await r.text();
  let data;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = { raw: text };
  }
  return { status: r.status, body: data };
}

function agentHeaders() {
  return { Authorization: `Bearer ${WIDGET_API_KEY}` };
}

function operatorHeaders() {
  return { Authorization: `Bearer ${OPERATOR_API_KEY}` };
}

function orchHeaders(json = true) {
  const h = {};
  if (ORCH_API_KEY) {
    h["X-Api-Key"] = ORCH_API_KEY;
    h.Authorization = `Bearer ${ORCH_API_KEY}`;
  }
  if (json) {
    h.Accept = "application/json";
    h["Content-Type"] = "application/json";
  }
  return h;
}

const app = express();
app.use(express.json({ limit: "12mb" }));

const publicDir = join(__dirname, "public");
app.get("/", (_req, res) => res.type("html").send(readFileSync(join(publicDir, "index.html"), "utf8")));
app.get("/styles.css", (_req, res) =>
  res.type("text/css").send(readFileSync(join(publicDir, "styles.css"), "utf8")),
);
app.get("/app.js", (_req, res) =>
  res.type("application/javascript").send(readFileSync(join(publicDir, "app.js"), "utf8")),
);

// Health proxies (no secrets to browser)
app.get("/api/health/agent", async (_req, res) => {
  try {
    const r = await fetch(`${AGENT_URL}/health`, { cache: "no-store" });
    sendJson(res, r.status, await r.json().catch(() => ({})));
  } catch (e) {
    sendJson(res, 502, { detail: String(e?.message || e) });
  }
});

app.get("/api/health/orchestrator", async (_req, res) => {
  try {
    const r = await fetch(`${ORCH_URL}/api/v1/health`, { cache: "no-store" });
    sendJson(res, r.status, await r.json().catch(() => ({})));
  } catch (e) {
    sendJson(res, 502, { detail: String(e?.message || e) });
  }
});

app.get("/api/health/infrastructure", async (_req, res) => {
  try {
    const { status, body } = await proxyJson(`${ORCH_URL}/api/v1/infrastructure/status`, {
      headers: orchHeaders(),
    });
    sendJson(res, status, body);
  } catch (e) {
    sendJson(res, 502, { detail: String(e?.message || e) });
  }
});

// Widget
app.post("/api/widget/invoke", async (req, res) => {
  try {
    const { status, body } = await proxyJson(`${AGENT_URL}/api/v1/widget/invoke`, {
      method: "POST",
      headers: { ...agentHeaders(), "Content-Type": "application/json" },
      body: JSON.stringify(req.body || {}),
    });
    sendJson(res, status, body);
  } catch (e) {
    sendJson(res, 502, { detail: String(e?.message || e) });
  }
});

// Operator
app.get("/api/operator/conversations", async (req, res) => {
  const q = new URLSearchParams(req.query).toString();
  const url = `${AGENT_URL}/api/v1/operator/conversations${q ? `?${q}` : ""}`;
  try {
    const { status, body } = await proxyJson(url, { headers: operatorHeaders() });
    sendJson(res, status, body);
  } catch (e) {
    sendJson(res, 502, { detail: String(e?.message || e) });
  }
});

app.get("/api/operator/conversations/:id", async (req, res) => {
  const url = `${AGENT_URL}/api/v1/operator/conversations/${encodeURIComponent(req.params.id)}`;
  try {
    const { status, body } = await proxyJson(url, { headers: operatorHeaders() });
    sendJson(res, status, body);
  } catch (e) {
    sendJson(res, 502, { detail: String(e?.message || e) });
  }
});

app.get("/api/operator/conversations/:id/messages", async (req, res) => {
  const q = new URLSearchParams(req.query).toString();
  const url = `${AGENT_URL}/api/v1/operator/conversations/${encodeURIComponent(req.params.id)}/messages${q ? `?${q}` : ""}`;
  try {
    const { status, body } = await proxyJson(url, { headers: operatorHeaders() });
    sendJson(res, status, body);
  } catch (e) {
    sendJson(res, 502, { detail: String(e?.message || e) });
  }
});

app.post("/api/operator/conversations/:id/reply", async (req, res) => {
  const url = `${AGENT_URL}/api/v1/operator/conversations/${encodeURIComponent(req.params.id)}/reply`;
  try {
    const { status, body } = await proxyJson(url, {
      method: "POST",
      headers: { ...operatorHeaders(), "Content-Type": "application/json" },
      body: JSON.stringify(req.body || {}),
    });
    sendJson(res, status, body);
  } catch (e) {
    sendJson(res, 502, { detail: String(e?.message || e) });
  }
});

app.post("/api/operator/conversations/:id/control", async (req, res) => {
  const url = `${AGENT_URL}/api/v1/operator/conversations/${encodeURIComponent(req.params.id)}/control`;
  try {
    const { status, body } = await proxyJson(url, {
      method: "POST",
      headers: { ...operatorHeaders(), "Content-Type": "application/json" },
      body: JSON.stringify(req.body || {}),
    });
    sendJson(res, status, body);
  } catch (e) {
    sendJson(res, 502, { detail: String(e?.message || e) });
  }
});

app.post("/api/operator/conversations/:id/visibility", async (req, res) => {
  const url = `${AGENT_URL}/api/v1/operator/conversations/${encodeURIComponent(req.params.id)}/visibility`;
  try {
    const { status, body } = await proxyJson(url, {
      method: "POST",
      headers: { ...operatorHeaders(), "Content-Type": "application/json" },
      body: JSON.stringify(req.body || {}),
    });
    sendJson(res, status, body);
  } catch (e) {
    sendJson(res, 502, { detail: String(e?.message || e) });
  }
});

// Orchestrator knowledge
app.get("/api/orch/knowledge/documents", async (_req, res) => {
  try {
    const { status, body } = await proxyJson(`${ORCH_URL}/api/v1/knowledge/documents`, {
      headers: orchHeaders(),
    });
    sendJson(res, status, body);
  } catch (e) {
    sendJson(res, 502, { detail: String(e?.message || e) });
  }
});

app.post("/api/orch/knowledge/documents", async (req, res) => {
  try {
    const { status, body } = await proxyJson(`${ORCH_URL}/api/v1/knowledge/documents`, {
      method: "POST",
      headers: orchHeaders(),
      body: JSON.stringify(req.body || {}),
    });
    sendJson(res, status, body);
  } catch (e) {
    sendJson(res, 502, { detail: String(e?.message || e) });
  }
});

app.post("/api/orch/knowledge/documents/upload", express.raw({ type: "*/*", limit: "50mb" }), async (req, res) => {
  try {
    const filename = decodeURIComponent(String(req.headers["x-filename"] || "document.bin"));
    const url = `${ORCH_URL}/api/v1/knowledge/documents`;
    const form = new FormData();
    form.append("file", new Blob([req.body]), filename);
    const h = orchHeaders(false);
    const r = await fetch(url, { method: "POST", headers: h, body: form });
    const text = await r.text();
    let data;
    try {
      data = text ? JSON.parse(text) : null;
    } catch {
      data = { raw: text };
    }
    sendJson(res, r.status, data);
  } catch (e) {
    sendJson(res, 502, { detail: String(e?.message || e) });
  }
});

app.get("/api/orch/knowledge/documents/:id", async (req, res) => {
  const url = `${ORCH_URL}/api/v1/knowledge/documents/${encodeURIComponent(req.params.id)}`;
  try {
    const { status, body } = await proxyJson(url, { headers: orchHeaders() });
    sendJson(res, status, body);
  } catch (e) {
    sendJson(res, 502, { detail: String(e?.message || e) });
  }
});

app.delete("/api/orch/knowledge/documents/:id", async (req, res) => {
  const url = `${ORCH_URL}/api/v1/knowledge/documents/${encodeURIComponent(req.params.id)}`;
  try {
    const { status, body } = await proxyJson(url, { method: "DELETE", headers: orchHeaders() });
    sendJson(res, status, body);
  } catch (e) {
    sendJson(res, 502, { detail: String(e?.message || e) });
  }
});

app.post("/api/orch/knowledge/reindex", async (req, res) => {
  try {
    const { status, body } = await proxyJson(`${ORCH_URL}/api/v1/knowledge/reindex`, {
      method: "POST",
      headers: orchHeaders(),
      body: JSON.stringify(req.body || { mode: "full" }),
    });
    sendJson(res, status, body);
  } catch (e) {
    sendJson(res, 502, { detail: String(e?.message || e) });
  }
});

app.get("/api/orch/jobs/:id", async (req, res) => {
  const url = `${ORCH_URL}/api/v1/jobs/${encodeURIComponent(req.params.id)}`;
  try {
    const { status, body } = await proxyJson(url, { headers: orchHeaders() });
    sendJson(res, status, body);
  } catch (e) {
    sendJson(res, 502, { detail: String(e?.message || e) });
  }
});

// Prompts
app.get("/api/orch/prompts", async (_req, res) => {
  try {
    const { status, body } = await proxyJson(`${ORCH_URL}/api/v1/prompts`, { headers: orchHeaders() });
    sendJson(res, status, body);
  } catch (e) {
    sendJson(res, 502, { detail: String(e?.message || e) });
  }
});

app.get("/api/orch/prompts/:key", async (req, res) => {
  const url = `${ORCH_URL}/api/v1/prompts/${encodeURIComponent(req.params.key)}`;
  try {
    const { status, body } = await proxyJson(url, { headers: orchHeaders() });
    sendJson(res, status, body);
  } catch (e) {
    sendJson(res, 502, { detail: String(e?.message || e) });
  }
});

app.put("/api/orch/prompts/:key", async (req, res) => {
  const url = `${ORCH_URL}/api/v1/prompts/${encodeURIComponent(req.params.key)}`;
  try {
    const { status, body } = await proxyJson(url, {
      method: "PUT",
      headers: orchHeaders(),
      body: JSON.stringify({ content: String(req.body?.content || "") }),
    });
    sendJson(res, status, body);
  } catch (e) {
    sendJson(res, 502, { detail: String(e?.message || e) });
  }
});

app.listen(PORT, "0.0.0.0", () => {
  console.log(`Agent Support Studio: http://127.0.0.1:${PORT}`);
  console.log(`Agent: ${AGENT_URL} | Orchestrator: ${ORCH_URL}`);
});
