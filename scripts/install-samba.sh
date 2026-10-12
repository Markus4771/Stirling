#!/usr/bin/env bash
# Installs the bundled Samba Share Manager (port 8085 by default).
# Existing Samba shares are not reset or deleted.
set -Eeuo pipefail
[[ $EUID -eq 0 ]] || { echo "Als root ausführen." >&2; exit 1; }
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[[ -f "$ROOT/samba-share-manager/install.sh" ]] || { echo "Samba-Manager-Quellen fehlen" >&2; exit 1; }
[[ -d /opt/Stirling-PDF ]] || { echo "Stirling PDF nicht installiert." >&2; exit 1; }
if [[ -e /etc/systemd/system/samba-share-manager.service ]]; then
  echo "Samba Share Manager ist bereits installiert; zum Schutz vorhandener Zugangsdaten keine Neuinstallation."
  systemctl is-active samba-share-manager.service || true
  exit 0
fi
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y samba smbclient sudo python3 python3-cryptography acl
id stirling >/dev/null || { echo "Systembenutzer stirling fehlt." >&2; exit 1; }
# The bundled manager uses the SMB login 'markus'; create the account only if absent.
if ! id markus >/dev/null 2>&1; then
  useradd -m -s /bin/bash markus
  echo "Linux-Konto markus angelegt (ohne initiales Linux-Passwort)."
fi
install -d -o stirling -g stirling -m 0750 /opt/Stirling-PDF/pipeline/watchedFolders
install -d -o stirling -g stirling -m 0750 /opt/Stirling-PDF/pipeline/finishedFolders
install -d -o root -g root -m 0755 /srv/samba-shares
systemctl enable --now smbd.service
if ! pdbedit -L 2>/dev/null | grep -q '^markus:'; then
  if [[ ! -t 0 ]]; then
    echo "Interaktive Eingabe erforderlich: SMB-Passwort für markus. Führe im Terminal aus: sudo smbpasswd -a markus" >&2
    exit 1
  fi
  echo "Bitte jetzt ein eigenes SMB-Passwort für den Benutzer markus vergeben:"
  smbpasswd -a markus
fi
cd "$ROOT/samba-share-manager"
export SHARE_GUI_PORT="${SHARE_GUI_PORT:-8085}"
bash install.sh
echo "Samba Share Manager: http://$(hostname -I | awk '{print $1}'):${SHARE_GUI_PORT}/"
echo "Benutzername GUI: admin; das Passwort wurde interaktiv vergeben."
echo "Hinweis: SMB-Freigaben müssen in der Weboberfläche angelegt werden."
