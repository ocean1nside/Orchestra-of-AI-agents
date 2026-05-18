#!/bin/bash
set -euo pipefail
cd /opt/orchestra/Orchestra-of-AI-agents
set -a
# shellcheck disable=SC1091
source apps/orchestrator-api/.env
set +a
WKEY=$(grep "^WIDGET_API_KEY=" apps/agents/vendor-support-agent/.env | cut -d= -f2- | tr -d '\r')

echo "=== infrastructure ==="
curl -sf -H "X-Api-Key: ${API_KEY_DEV}" http://127.0.0.1:8000/api/v1/infrastructure/status
echo

echo "=== upload documents ==="
for f in storage/knowledge/originals/*/*; do
  [ -f "$f" ] || continue
  echo "file: $f"
  curl -sf -X POST -H "X-Api-Key: ${API_KEY_DEV}" -F "file=@${f}" http://127.0.0.1:8000/api/v1/knowledge/documents
  echo
done

echo "=== reindex ==="
JOB=$(curl -sf -X POST -H "X-Api-Key: ${API_KEY_DEV}" -H "Content-Type: application/json" \
  -d '{"mode":"full"}' http://127.0.0.1:8000/api/v1/knowledge/reindex)
echo "$JOB"
JOB_ID=$(echo "$JOB" | python3 -c 'import sys,json; print(json.load(sys.stdin)["job_id"])')

for i in $(seq 1 30); do
  ST=$(curl -sf -H "X-Api-Key: ${API_KEY_DEV}" "http://127.0.0.1:8000/api/v1/jobs/${JOB_ID}")
  STATUS=$(echo "$ST" | python3 -c 'import sys,json; print(json.load(sys.stdin)["status"])')
  echo "poll $i: $STATUS"
  [ "$STATUS" = "completed" ] && break
  [ "$STATUS" = "failed" ] && echo "$ST" && exit 1
  sleep 5
done

echo "=== widget test ==="
curl -sf -X POST -H "Authorization: Bearer ${WKEY}" -H "Content-Type: application/json" \
  -d '{"channel":"widget","conversation_id":"migrate_test","user_id":"u1","message":"Кратко: что такое eBot?"}' \
  http://127.0.0.1:8010/api/v1/widget/invoke | python3 -c \
  'import sys,json; d=json.load(sys.stdin); print("status",d.get("status")); print("sources",len(d.get("sources",[]))); print("answer_len",len(d.get("answer","")))'

echo "=== done ==="
