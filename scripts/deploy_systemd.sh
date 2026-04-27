#!/usr/bin/env bash
set -euo pipefail

# One-shot deploy: build frontend, install systemd unit, enable + start.
# Re-run when systemd unit changes or after a frontend redeploy.

ROOT="/datapool/bigweld-portal"
UNIT="bigweld-portal.service"

echo "==> Building frontend (as invoking user, not root)"
if [[ "${EUID}" -eq 0 ]] && [[ -n "${SUDO_USER:-}" ]]; then
    sudo -u "${SUDO_USER}" -H bash -c "cd '$ROOT/frontend' && npm run build"
else
    (cd "$ROOT/frontend" && npm run build)
fi

echo "==> Installing systemd unit"
sudo cp "$ROOT/systemd/$UNIT" "/etc/systemd/system/$UNIT"
sudo systemctl daemon-reload
sudo systemctl enable "$UNIT"
sudo systemctl restart "$UNIT"

echo "==> Waiting for service to become active"
for i in 1 2 3 4 5 6 7 8 9 10; do
    if systemctl is-active --quiet "$UNIT"; then
        break
    fi
    sleep 1
done

echo "==> Service status"
sudo systemctl status "$UNIT" --no-pager --lines=10 || true

echo "==> Health probe"
curl -fsS http://127.0.0.1:8884/health
echo
