#!/bin/bash
curl -s -H "Content-Type: application/json" \
  -d '{"channel":"widget","conversation_id":"studio_via_proxy","user_id":"u1","message":"hello","context":{}}' \
  http://127.0.0.1:8790/api/widget/invoke | head -c 900
echo
