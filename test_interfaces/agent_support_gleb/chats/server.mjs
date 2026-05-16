import dotenv from "dotenv";
import express from "express";
import { readFileSync } from "fs";
import { dirname, join } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
dotenv.config({ path: join(__dirname, ".env.local") });
dotenv.config({ path: join(__dirname, ".env") });

const AGENT_URL = (process.env.AGENT_URL || "http://127.0.0.1:8010").replace(/\/$/, "");
const OPERATOR_API_KEY = (process.env.OPERATOR_API_KEY || process.env.WIDGET_API_KEY || "").trim();
const PORT = Number(process.env.PORT || 8788);

if (!OPERATOR_API_KEY) {
  console.error("Set OPERATOR_API_KEY or WIDGET_API_KEY in .env / .env.local.");
  process.exit(1);
}

const authHeaders = {
  Authorization: `Bearer ${OPERATOR_API_KEY}`,
  Accept: "application/json",
};

function sendJson(res, status, body) {
  res.setHeader("Cache-Control", "no-store, no-cache, must-revalidate");
  res.setHeader("Pragma", "no-cache");
  res.status(status).json(body);
}

async function proxyFetch(path, opts = {}) {
  const url = `${AGENT_URL}${path.startsWith("/") ? path : `/${path}`}`;
  const r = await fetch(url, {
    cache: "no-store",
    ...opts,
    headers: { ...authHeaders, "Content-Type": "application/json", ...opts.headers },
  });
  const text = await r.text();
  let body;
  try {
    body = text ? JSON.parse(text) : null;
  } catch {
    body = { raw: text };
  }
  return { status: r.status, body };
}

const app = express();
app.use(express.json({ limit: "2mb" }));

app.get("/api/conversations", async (req, res) => {
  const q = new URLSearchParams(req.query).toString();
  const path = `/api/v1/operator/conversations${q ? `?${q}` : ""}`;
  const { status, body } = await proxyFetch(path);
  sendJson(res, status, body);
});

app.get("/api/conversations/:id", async (req, res) => {
  const { status, body } = await proxyFetch(`/api/v1/operator/conversations/${encodeURIComponent(req.params.id)}`);
  sendJson(res, status, body);
});

app.get("/api/conversations/:id/messages", async (req, res) => {
  const q = new URLSearchParams(req.query).toString();
  const path = `/api/v1/operator/conversations/${encodeURIComponent(req.params.id)}/messages${q ? `?${q}` : ""}`;
  const { status, body } = await proxyFetch(path);
  sendJson(res, status, body);
});

app.post("/api/conversations/:id/reply", async (req, res) => {
  const { status, body } = await proxyFetch(
    `/api/v1/operator/conversations/${encodeURIComponent(req.params.id)}/reply`,
    { method: "POST", body: JSON.stringify(req.body || {}) },
  );
  sendJson(res, status, body);
});

app.post("/api/conversations/:id/control", async (req, res) => {
  const { status, body } = await proxyFetch(
    `/api/v1/operator/conversations/${encodeURIComponent(req.params.id)}/control`,
    { method: "POST", body: JSON.stringify(req.body || {}) },
  );
  sendJson(res, status, body);
});

app.post("/api/conversations/:id/visibility", async (req, res) => {
  const { status, body } = await proxyFetch(
    `/api/v1/operator/conversations/${encodeURIComponent(req.params.id)}/visibility`,
    { method: "POST", body: JSON.stringify(req.body || {}) },
  );
  sendJson(res, status, body);
});

app.get("/", (_req, res) => {
  res.type("html").send(readFileSync(join(__dirname, "public", "index.html"), "utf8"));
});

app.get("/app.js", (_req, res) => {
  res.type("application/javascript").send(readFileSync(join(__dirname, "public", "app.js"), "utf8"));
});

app.listen(PORT, "0.0.0.0", () => {
  console.log(`Chats UI + proxy: http://127.0.0.1:${PORT}`);
  console.log(`Agent: ${AGENT_URL}`);
});
