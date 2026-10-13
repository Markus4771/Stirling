#!/bin/bash
set -euo pipefail
SHARE_GUI_PORT="${SHARE_GUI_PORT:-8085}"
[[ "$SHARE_GUI_PORT" =~ ^[0-9]+$ ]] || { echo 'Ungueltiger Port'; exit 1; }
if [[ $EUID -ne 0 ]]; then echo 'Bitte mit sudo ausfuehren: sudo bash install.sh'; exit 1; fi
for c in testparm systemctl python3 visudo; do command -v "$c" >/dev/null || { echo "Fehlt: $c (Samba und sudo zuerst installieren)"; exit 1; }; done
test -d /opt/Stirling-PDF/pipeline/watchedFolders && test -d /opt/Stirling-PDF/pipeline/finishedFolders || { echo 'Stirling-PDF-Pipeline-Verzeichnisse fehlen'; exit 1; }
id stirling >/dev/null || { echo 'Stirling-Benutzer fehlt'; exit 1; }
id markus >/dev/null || { echo 'Linux-Benutzer markus fehlt.'; exit 1; }
if ! id samba-gui >/dev/null 2>&1; then useradd --system --home /nonexistent --shell /usr/sbin/nologin samba-gui; fi
install -d -o root -g root -m 755 /usr/local/lib/samba-share-manager
install -d -o root -g samba-gui -m 750 /etc/samba-share-manager
install -m 755 helper.py /usr/local/lib/samba-share-manager/helper.py
install -m 755 app.py /usr/local/lib/samba-share-manager/app.py
if [[ ! -f /etc/samba-share-manager/auth.json ]]; then
python3 - <<'PY'
import hashlib,json,secrets
from pathlib import Path
password='admin123'
salt=secrets.token_bytes(16)
rounds=600000
auth=Path('/etc/samba-share-manager/auth.json')
auth.write_text(json.dumps({'salt':salt.hex(),'rounds':rounds,
  'digest':hashlib.pbkdf2_hmac('sha256',password.encode(),salt,rounds).hex(),
  'must_change':True}))
print('GUI-Startzugang: admin / admin123; Passwort beim ersten Login sofort aendern.')
PY
chown root:samba-gui /etc/samba-share-manager/auth.json
chmod 640 /etc/samba-share-manager/auth.json
fi
python3 - <<'PY'
from pathlib import Path
import re
p=Path('/etc/samba/smb.conf');s=p.read_text()
inc='   include = /etc/samba/share-manager.conf'
if not re.search(r'^\s*\[global\]\s*$',s,re.M|re.I):raise SystemExit('Kein [global]-Block in smb.conf gefunden')
if '/etc/samba/share-manager.conf' not in s:
    s=re.sub(r'^(\s*\[global\]\s*)$',lambda m:m.group(1)+'\n'+inc,s,count=1,flags=re.M|re.I)
    p.with_suffix('.conf.bak-samba-gui').write_text(p.read_text())
    p.write_text(s)
PY
touch /etc/samba/share-manager.conf
chmod 644 /etc/samba/share-manager.conf
if ! testparm -s >/dev/null 2>&1; then echo 'Samba-Konfiguration ungueltig! smb.conf Backup: /etc/samba/smb.conf.bak-samba-gui'; exit 1; fi
cat > /etc/sudoers.d/samba-share-manager <<'EOF'
samba-gui ALL=(root) NOPASSWD: /usr/local/lib/samba-share-manager/helper.py *
EOF
chmod 440 /etc/sudoers.d/samba-share-manager
visudo -cf /etc/sudoers.d/samba-share-manager >/dev/null
cat > /etc/systemd/system/samba-share-manager.service <<EOF
[Unit]
Description=Simple Samba Share Manager
After=network.target smbd.service
[Service]
Type=simple
User=samba-gui
Group=samba-gui
ExecStart=/usr/bin/python3 /usr/local/lib/samba-share-manager/app.py
Restart=on-failure
NoNewPrivileges=no
ProtectSystem=strict
ProtectHome=yes
PrivateTmp=yes
ReadWritePaths=/run /srv /etc /var/lib/samba /var/cache/samba /opt/Stirling-PDF/pipeline
Environment=SHARE_GUI_HOST=0.0.0.0
Environment=SHARE_GUI_PORT=${SHARE_GUI_PORT}
[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable samba-share-manager.service
systemctl restart samba-share-manager.service
systemctl reload smbd
echo "Fertig. Browser: http://SERVER-IP:${SHARE_GUI_PORT}/  Login: admin"
echo 'Sicherheitsinfo: nur im vertrauenswuerdigen LAN verwenden; fuer Fernzugriff HTTPS via Reverse Proxy.'
