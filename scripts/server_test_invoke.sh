#!/bin/bash
set -euo pipefail
KEY=$(docker exec infra-vendor-support-agent-1 printenv WIDGET_API_KEY)
echo "WIDGET_API_KEY length: ${#KEY}"
echo "--- new conversation ---"
curl -s -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
  -d '{"channel":"widget","conversation_id":"studio_diag_new","user_id":"u1","message":"hello","context":{}}' \
  http://127.0.0.1:8010/api/v1/widget/invoke | head -c 900
echo
echo "--- migrate_test ---"
curl -s -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
  -d '{"channel":"widget","conversation_id":"migrate_test","user_id":"u1","message":"hello","context":{}}' \
  http://127.0.0.1:8010/api/v1/widget/invoke | head -c 900
echo
