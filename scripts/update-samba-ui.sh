#!/usr/bin/env bash
# Safe deployment of Samba Share Manager application code only.
# Never resets /etc/samba-share-manager/auth.json or existing smb.conf/share definitions.
set -Eeuo pipefail
[[ $EUID -eq 0 ]] || { echo "Als root ausführen" >&2; exit 1; }
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[[ -f /etc/systemd/system/samba-share-manager.service ]] || { echo "Samba Share Manager ist noch nicht installiert. Zuerst: bash install.sh --samba-only" >&2; exit 1; }
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y python3-cryptography
install -d -o root -g root -m 0755 /usr/local/lib/samba-share-manager
install -o root -g root -m 0755 "$ROOT/samba-share-manager/app.py" /usr/local/lib/samba-share-manager/app.py
install -o root -g root -m 0755 "$ROOT/samba-share-manager/helper.py" /usr/local/lib/samba-share-manager/helper.py
python3 -m py_compile /usr/local/lib/samba-share-manager/app.py /usr/local/lib/samba-share-manager/helper.py
# Root helper needs to create system accounts (/etc) and Samba passdb (/var/lib/samba).
# Keep other system paths read-only and preserve all existing credentials.
install -d -m 0755 /etc/systemd/system/samba-share-manager.service.d
cat > /etc/systemd/system/samba-share-manager.service.d/10-account-storage.conf <<'EOF'
[Service]
ReadWritePaths=
ReadWritePaths=/run /srv /etc /var/lib/samba /var/cache/samba /opt/Stirling-PDF/pipeline
EOF
systemctl daemon-reload
systemctl restart samba-share-manager.service
systemctl --no-pager status samba-share-manager.service
echo "Bestehende SMB-Freigaben und GUI-Admin-Passwort wurden beibehalten."
