#!/bin/bash
set -euo pipefail
TOKEN=$(docker exec infra-vendor-support-agent-1 printenv TELEGRAM_BOT_TOKEN | tr -d '\r\n')
SECRET=$(docker exec infra-vendor-support-agent-1 printenv TELEGRAM_WEBHOOK_SECRET 2>/dev/null | tr -d '\r\n' || true)
echo "TOKEN length: ${#TOKEN}"
echo "WEBHOOK_SECRET length: ${#SECRET}"
echo "--- getWebhookInfo ---"
curl -s "https://api.telegram.org/bot${TOKEN}/getWebhookInfo" | python3 -m json.tool 2>/dev/null || curl -s "https://api.telegram.org/bot${TOKEN}/getWebhookInfo"
echo
echo "--- getMe ---"
curl -s "https://api.telegram.org/bot${TOKEN}/getMe" | python3 -m json.tool 2>/dev/null | head -20
echo
echo "--- recent agent telegram logs ---"
docker logs infra-vendor-support-agent-1 2>&1 | grep -i telegram | tail -15 || echo "(none)"
