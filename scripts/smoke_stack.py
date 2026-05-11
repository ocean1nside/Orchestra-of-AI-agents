#!/usr/bin/env python3
"""
Быстрая проверка стека после `docker compose up` (stdlib only).

Примеры:
  python scripts/smoke_stack.py
  python scripts/smoke_stack.py --orchestrator http://localhost:8000 --api-key YOUR_API_KEY_DEV
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request


def http_request(
    url: str,
    *,
    method: str = "GET",
    data: bytes | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[int, str]:
    req = urllib.request.Request(url, method=method, headers=headers or {}, data=data)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.status, resp.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace")


def main() -> int:
    p = argparse.ArgumentParser(description="Smoke: orchestrator + agent health / infrastructure")
    p.add_argument("--orchestrator", default="http://127.0.0.1:8000", help="orchestrator-api base URL")
    p.add_argument("--agent", default="http://127.0.0.1:8010", help="vendor-support-agent base URL")
    p.add_argument("--api-key", dest="api_key", default="", help="API_KEY_DEV if включён ORCHESTRATOR_REQUIRE_API_KEY")
    args = p.parse_args()
    orch = args.orchestrator.rstrip("/")
    ag = args.agent.rstrip("/")

    failed = False
    key_headers = {"X-Api-Key": args.api_key} if args.api_key.strip() else {}

    for url, label in (
        (f"{orch}/api/v1/health", "orchestrator /health"),
        (f"{orch}/api/v1/infrastructure/status", "orchestrator /infrastructure/status"),
        (f"{ag}/health", "agent /health"),
    ):
        code, body = http_request(url)
        ok = code == 200
        print(f"[{'OK' if ok else 'FAIL'}] {label} -> HTTP {code}")
        if not ok:
            failed = True
            if body:
                print(f"       {body[:300]}")
        elif "infrastructure" in label:
            try:
                j = json.loads(body)
                overall = j.get("status", "?")
                print(f"       overall={overall}")
                for name, svc in (j.get("services") or {}).items():
                    st = svc.get("status", "?")
                    extra = svc.get("note") or svc.get("error") or ""
                    if st not in ("ok",):
                        print(f"       {name}: {st} {extra}")
                    if st == "error":
                        failed = True
            except json.JSONDecodeError:
                print("       (invalid JSON)")
                failed = True

    code, _body = http_request(f"{orch}/api/v1/knowledge/index/status", headers=key_headers)
    if code == 200:
        print("[OK] orchestrator /knowledge/index/status (protected routes reachable with key or open)")
    elif code == 401:
        print("[SKIP] /knowledge/index/status -> 401 (задайте --api-key если ORCHESTRATOR_REQUIRE_API_KEY=true)")
    else:
        print(f"[??] /knowledge/index/status -> HTTP {code}")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
