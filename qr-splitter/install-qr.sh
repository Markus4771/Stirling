#!/usr/bin/env bash
set -Eeuo pipefail
(( EUID == 0 )) || { echo "Bitte sudo verwenden" >&2; exit 1; }
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
id stirling >/dev/null || { echo "Stirling PDF muss zuerst installiert sein" >&2; exit 1; }
apt-get update
apt-get install -y python3-fitz python3-opencv python3-numpy acl
install -d -m 755 /opt/Stirling-PDF/qr-splitter
install -o root -g root -m 755 "$ROOT/qr_splitter.py" /opt/Stirling-PDF/qr-splitter/qr_splitter.py
install -d -m 755 /srv/samba-shares
install -d -m 2770 -o stirling -g stirling /srv/samba-shares/Scan-QR
for name in Scan-QR Scan-Eingang; do
  folder="/srv/samba-shares/$name"
  [[ -d "$folder" ]] || { echo "Ordner fehlt: $folder" >&2; exit 1; }
  setfacl -m u:stirling:rwx,m::rwx "$folder"
  setfacl -m d:u:stirling:rwx,d:m::rwx "$folder"
done
cat > /etc/systemd/system/stirling-qr-splitter.service <<'EOF'
[Unit]
Description=Stirling QR Prefix Splitter
After=local-fs.target
[Service]
Type=oneshot
User=stirling
Group=stirling
ExecStart=/usr/bin/python3 /opt/Stirling-PDF/qr-splitter/qr_splitter.py --prefix SCAN:
EOF
cat > /etc/systemd/system/stirling-qr-splitter.timer <<'EOF'
[Unit]
Description=Run Stirling QR Prefix Splitter every minute
[Timer]
OnBootSec=2min
OnUnitInactiveSec=1min
Unit=stirling-qr-splitter.service
[Install]
WantedBy=timers.target
EOF
systemctl daemon-reload
echo "Installation bereit, aber noch nicht aktiviert."
echo "Test: sudo -u stirling python3 /opt/Stirling-PDF/qr-splitter/qr_splitter.py --dry-run"
echo "Start: sudo systemctl enable --now stirling-qr-splitter.timer"
echo "Samba-Freigabe Scan-QR im eigenen Verwaltungstool anlegen."
