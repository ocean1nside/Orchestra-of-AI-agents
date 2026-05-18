#!/bin/bash
set -euo pipefail
DOMAIN="212-67-10-140.sslip.io"
CONF="/etc/nginx/sites-available/agent-webhook"

cat > "$CONF" <<NGINX
server {
    listen 80;
    server_name ${DOMAIN};

    location /api/v1/telegram/webhook {
        proxy_pass http://127.0.0.1:8010;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        client_max_body_size 2m;
        proxy_read_timeout 300s;
    }

    location /api/v1/max/webhook {
        proxy_pass http://127.0.0.1:8010;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_read_timeout 300s;
    }

    location /health {
        proxy_pass http://127.0.0.1:8010;
    }
}
NGINX

ln -sf "$CONF" /etc/nginx/sites-enabled/agent-webhook
nginx -t
systemctl reload nginx

if ! command -v certbot >/dev/null; then
  apt-get update -qq
  DEBIAN_FRONTEND=noninteractive apt-get install -y -qq certbot python3-certbot-nginx
fi

certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos --register-unsafely-without-email --redirect || \
  certbot certonly --nginx -d "$DOMAIN" --non-interactive --agree-tos --register-unsafely-without-email

systemctl reload nginx
echo "HTTPS ready: https://${DOMAIN}/health"
