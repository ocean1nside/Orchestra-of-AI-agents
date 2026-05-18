#!/bin/bash
# Usage: ./server_set_telegram_webhook.sh 'https://HOST/api/v1/telegram/webhook'
set -euo pipefail
WEBHOOK_URL="${1:?Usage: $0 https://host/api/v1/telegram/webhook}"
TOKEN=$(docker exec infra-vendor-support-agent-1 printenv TELEGRAM_BOT_TOKEN | tr -d '\r\n')
SECRET=$(docker exec infra-vendor-support-agent-1 printenv TELEGRAM_WEBHOOK_SECRET 2>/dev/null | tr -d '\r\n' || true)
ARGS=( -d "url=${WEBHOOK_URL}" -d "allowed_updates[]=message" -d "allowed_updates[]=edited_message" )
if [ -n "$SECRET" ]; then
  ARGS+=( -d "secret_token=${SECRET}" )
fi
echo "Setting webhook to: $WEBHOOK_URL"
curl -s "https://api.telegram.org/bot${TOKEN}/setWebhook" "${ARGS[@]}" | python3 -m json.tool
echo
curl -s "https://api.telegram.org/bot${TOKEN}/getWebhookInfo" | python3 -m json.tool
