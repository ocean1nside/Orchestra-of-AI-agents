import dotenv from "dotenv";
import express from "express";
import { readFileSync } from "fs";
import { dirname, join } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
dotenv.config({ path: join(__dirname, ".env.local") });
dotenv.config({ path: join(__dirname, ".env") });

const AGENT_URL = (process.env.AGENT_URL || "http://127.0.0.1:8010").replace(/\/$/, "");
const WIDGET_API_KEY = (process.env.WIDGET_API_KEY || "").trim();
const PORT = Number(process.env.PORT || 8789);

if (!WIDGET_API_KEY) {
  console.error("Set WIDGET_API_KEY in .env.local (same as agent WIDGET_API_KEY).");
  process.exit(1);
}

const authHeaders = {
  Authorization: `Bearer ${WIDGET_API_KEY}`,
  Accept: "application/json",
};

function sendJson(res, status, body) {
  res.setHeader("Cache-Control", "no-store, no-cache, must-revalidate");
  res.setHeader("Pragma", "no-cache");
  res.status(status).json(body);
}

const app = express();
app.use(express.json({ limit: "1mb" }));

app.post("/api/widget/invoke", async (req, res) => {
  const url = `${AGENT_URL}/api/v1/widget/invoke`;
  try {
    const r = await fetch(url, {
      method: "POST",
      cache: "no-store",
      headers: { ...authHeaders, "Content-Type": "application/json" },
      body: JSON.stringify(req.body || {}),
    });
    const text = await r.text();
    let body;
    try {
      body = text ? JSON.parse(text) : null;
    } catch {
      body = { raw: text };
    }
    sendJson(res, r.status, body);
  } catch (e) {
    sendJson(res, 502, { detail: String(e?.cause?.message || e?.message || e) });
  }
});

app.get("/", (_req, res) => {
  res.type("html").send(readFileSync(join(__dirname, "public", "index.html"), "utf8"));
});

app.get("/app.js", (_req, res) => {
  res.type("application/javascript").send(readFileSync(join(__dirname, "public", "app.js"), "utf8"));
});

app.listen(PORT, "0.0.0.0", () => {
  console.log(`Widget test page: http://127.0.0.1:${PORT}`);
  console.log(`Agent: ${AGENT_URL}`);
});
