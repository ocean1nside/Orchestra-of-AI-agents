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
  console.error("Set WIDGET_API_KEY (and optionally OPERATOR_API_KEY) in .env / .env.local for console.");
  process.exit(1);
}

function sendJson(res, status, body) {
  res.setHeader("Cache-Control", "no-store, no-cache, must-revalidate");
  res.setHeader("Pragma", "no-cache");
  res.status(status).json(body);
}

async function proxyJson(targetUrl, { headers = {}, method = "GET", body } = {}) {
  const r = await fetch(targetUrl, {
    method,
    cache: "no-store",
    headers: { Accept: "application/json", "Content-Type": "application/json", ...headers },
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

const app = express();
app.use(express.json({ limit: "5mb" }));

// ---- Static SPA ----

function sendIndex(res) {
  res.type("html").send(readFileSync(join(__dirname, "public", "index.html"), "utf8"));
}

app.get("/", (_req, res) => sendIndex(res));
app.get("/widjet", (_req, res) => sendIndex(res));
app.get("/agents", (_req, res) => sendIndex(res));

app.get("/app.js", (_req, res) => {
  res.type("application/javascript").send(readFileSync(join(__dirname, "public", "app.js"), "utf8"));
});

// ---- Agent: widget invoke ----

app.post("/api/widget/invoke", async (req, res) => {
  try {
    const url = `${AGENT_URL}/api/v1/widget/invoke`;
    const { status, body } = await proxyJson(url, {
      method: "POST",
      headers: { Authorization: `Bearer ${WIDGET_API_KEY}` },
      body: JSON.stringify(req.body || {}),
    });
    sendJson(res, status, body);
  } catch (e) {
    sendJson(res, 502, { detail: String(e?.cause?.message || e?.message || e) });
  }
});

// ---- Agent: operator API (chats) ----

function operatorHeaders() {
  return { Authorization: `Bearer ${OPERATOR_API_KEY}` };
}

app.get("/api/operator/conversations", async (req, res) => {
  const q = new URLSearchParams(req.query).toString();
  const url = `${AGENT_URL}/api/v1/operator/conversations${q ? `?${q}` : ""}`;
  try {
    const { status, body } = await proxyJson(url, { headers: operatorHeaders() });
    sendJson(res, status, body);
  } catch (e) {
    sendJson(res, 502, { detail: String(e?.cause?.message || e?.message || e) });
  }
});

app.get("/api/operator/conversations/:id", async (req, res) => {
  const url = `${AGENT_URL}/api/v1/operator/conversations/${encodeURIComponent(req.params.id)}`;
  try {
    const { status, body } = await proxyJson(url, { headers: operatorHeaders() });
    sendJson(res, status, body);
  } catch (e) {
    sendJson(res, 502, { detail: String(e?.cause?.message || e?.message || e) });
  }
});

app.get("/api/operator/conversations/:id/messages", async (req, res) => {
  const q = new URLSearchParams(req.query).toString();
  const url = `${AGENT_URL}/api/v1/operator/conversations/${encodeURIComponent(
    req.params.id,
  )}/messages${q ? `?${q}` : ""}`;
  try {
    const { status, body } = await proxyJson(url, { headers: operatorHeaders() });
    sendJson(res, status, body);
  } catch (e) {
    sendJson(res, 502, { detail: String(e?.cause?.message || e?.message || e) });
  }
});

app.post("/api/operator/conversations/:id/reply", async (req, res) => {
  const url = `${AGENT_URL}/api/v1/operator/conversations/${encodeURIComponent(req.params.id)}/reply`;
  try {
    const { status, body } = await proxyJson(url, {
      method: "POST",
      headers: operatorHeaders(),
      body: JSON.stringify(req.body || {}),
    });
    sendJson(res, status, body);
  } catch (e) {
    sendJson(res, 502, { detail: String(e?.cause?.message || e?.message || e) });
  }
});

app.post("/api/operator/conversations/:id/control", async (req, res) => {
  const url = `${AGENT_URL}/api/v1/operator/conversations/${encodeURIComponent(req.params.id)}/control`;
  try {
    const { status, body } = await proxyJson(url, {
      method: "POST",
      headers: operatorHeaders(),
      body: JSON.stringify(req.body || {}),
    });
    sendJson(res, status, body);
  } catch (e) {
    sendJson(res, 502, { detail: String(e?.cause?.message || e?.message || e) });
  }
});

app.post("/api/operator/conversations/:id/visibility", async (req, res) => {
  const url = `${AGENT_URL}/api/v1/operator/conversations/${encodeURIComponent(req.params.id)}/visibility`;
  try {
    const { status, body } = await proxyJson(url, {
      method: "POST",
      headers: operatorHeaders(),
      body: JSON.stringify(req.body || {}),
    });
    sendJson(res, status, body);
  } catch (e) {
    sendJson(res, 502, { detail: String(e?.cause?.message || e?.message || e) });
  }
});

// ---- Orchestrator: knowledge ----

function orchHeaders() {
  const h = { Accept: "application/json", "Content-Type": "application/json" };
  if (ORCH_API_KEY) {
    h["X-Api-Key"] = ORCH_API_KEY;
    h.Authorization = `Bearer ${ORCH_API_KEY}`;
  }
  return h;
}

app.get("/api/orch/knowledge/documents", async (_req, res) => {
  const url = `${ORCH_URL}/api/v1/knowledge/documents`;
  try {
    const { status, body } = await proxyJson(url, { headers: orchHeaders() });
    sendJson(res, status, body);
  } catch (e) {
    sendJson(res, 502, { detail: String(e?.cause?.message || e?.message || e) });
  }
});

app.post("/api/orch/knowledge/documents", async (req, res) => {
  const url = `${ORCH_URL}/api/v1/knowledge/documents`;
  try {
    const { status, body } = await proxyJson(url, {
      method: "POST",
      headers: orchHeaders(),
      body: JSON.stringify(req.body || {}),
    });
    sendJson(res, status, body);
  } catch (e) {
    sendJson(res, 502, { detail: String(e?.cause?.message || e?.message || e) });
  }
});

app.get("/api/orch/knowledge/documents/:id", async (req, res) => {
  const url = `${ORCH_URL}/api/v1/knowledge/documents/${encodeURIComponent(req.params.id)}`;
  try {
    const { status, body } = await proxyJson(url, { headers: orchHeaders() });
    sendJson(res, status, body);
  } catch (e) {
    sendJson(res, 502, { detail: String(e?.cause?.message || e?.message || e) });
  }
});

// ---- Orchestrator: prompts ----

app.get("/api/orch/prompts", async (_req, res) => {
  const url = `${ORCH_URL}/api/v1/prompts`;
  try {
    const { status, body } = await proxyJson(url, { headers: orchHeaders() });
    sendJson(res, status, body);
  } catch (e) {
    sendJson(res, 502, { detail: String(e?.cause?.message || e?.message || e) });
  }
});

app.get("/api/orch/prompts/:key", async (req, res) => {
  const url = `${ORCH_URL}/api/v1/prompts/${encodeURIComponent(req.params.key)}`;
  try {
    const { status, body } = await proxyJson(url, { headers: orchHeaders() });
    sendJson(res, status, body);
  } catch (e) {
    sendJson(res, 502, { detail: String(e?.cause?.message || e?.message || e) });
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
    sendJson(res, 502, { detail: String(e?.cause?.message || e?.message || e) });
  }
});

// ---- Orchestrator: agents registry ----

app.get("/api/orch/agents", async (_req, res) => {
  const url = `${ORCH_URL}/api/v1/agents`;
  try {
    const { status, body } = await proxyJson(url, { headers: orchHeaders() });
    sendJson(res, status, body);
  } catch (e) {
    sendJson(res, 502, { detail: String(e?.cause?.message || e?.message || e) });
  }
});

app.listen(PORT, "0.0.0.0", () => {
  console.log(`Console UI: http://127.0.0.1:${PORT}`);
  console.log(`Agent: ${AGENT_URL}`);
  console.log(`Orchestrator: ${ORCH_URL}`);
});

