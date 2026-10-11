#!/usr/bin/env bash
# Stirling PDF installation for a fresh Debian 13 VM (without Docker)
set -Eeuo pipefail

INSTALL_DIR=/opt/Stirling-PDF
SERVICE=/etc/systemd/system/stirlingpdf.service
JAR_NAME=Stirling-PDF-with-login.jar
JAR_URL=https://files.stirlingpdf.com/Stirling-PDF-with-login.jar

log() { printf '\n==> %s\n' "$*"; }
die() { echo "FEHLER: $*" >&2; exit 1; }
trap 'echo "FEHLER in Zeile $LINENO. Details oben pruefen." >&2' ERR

(( EUID == 0 )) || die "Mit sudo ausfuehren: sudo bash install.sh"
[[ -r /etc/os-release ]] || die "Betriebssystem nicht erkannt"
. /etc/os-release
[[ "${ID:-}" == debian && "${VERSION_ID%%.*}" == 13 ]] || die "Dieses Skript ist fuer Debian 13 vorgesehen"
[[ ! -e "$SERVICE" ]] || die "stirlingpdf.service existiert bereits. Zum Schutz der bestehenden Installation Abbruch."
[[ ! -e "$INSTALL_DIR/$JAR_NAME" ]] || die "Stirling PDF ist offenbar schon installiert. Abbruch."

export DEBIAN_FRONTEND=noninteractive
log "Systempakete installieren"
apt-get update
apt-get install -y ca-certificates curl openjdk-25-jre-headless libreoffice tesseract-ocr tesseract-ocr-deu tesseract-ocr-eng ocrmypdf poppler-utils qpdf pngquant python3 python3-opencv fonts-dejavu-core

java -version
JAVA_MAJOR="$(java -version 2>&1 | sed -n '1s/.*version "\([0-9]*\).*/\1/p')"
[[ "$JAVA_MAJOR" =~ ^[0-9]+$ && "$JAVA_MAJOR" -ge 25 ]] || die "Java 25 oder neuer erforderlich"

log "Systembenutzer und Verzeichnisse einrichten"
if ! id stirling >/dev/null 2>&1; then
  useradd --system --home-dir "$INSTALL_DIR" --shell /usr/sbin/nologin stirling
fi
install -d -o stirling -g stirling -m 750 "$INSTALL_DIR"
for folder in configs logs pipeline/watchedFolders pipeline/finishedFolders; do
  install -d -o stirling -g stirling -m 750 "$INSTALL_DIR/$folder"
done

log "Stirling PDF herunterladen"
TMPFILE="$(mktemp)"
trap 'rm -f "$TMPFILE"' EXIT
curl -fL --retry 3 --connect-timeout 20 "$JAR_URL" -o "$TMPFILE"
[[ "$(stat -c %s "$TMPFILE")" -gt 10000000 ]] || die "JAR ungewoehnlich klein: Download nicht uebernehmen"
file "$TMPFILE" 2>/dev/null || true
install -o stirling -g stirling -m 640 "$TMPFILE" "$INSTALL_DIR/$JAR_NAME"

log "Konfiguration erstellen"
if [[ ! -f "$INSTALL_DIR/.env" ]]; then
  cat > "$INSTALL_DIR/.env" <<'EOF'
SYSTEM_DEFAULTLOCALE=de-DE
SERVER_ADDRESS=0.0.0.0
SERVER_PORT=8080
SECURITY_ENABLELOGIN=true
EOF
  chown stirling:stirling "$INSTALL_DIR/.env"
  chmod 600 "$INSTALL_DIR/.env"
fi

log "systemd-Dienst anlegen"
cat > "$SERVICE" <<'EOF'
[Unit]
Description=Stirling PDF (JAR)
Wants=network-online.target
After=network-online.target

[Service]
Type=simple
User=stirling
Group=stirling
WorkingDirectory=/opt/Stirling-PDF
EnvironmentFile=/opt/Stirling-PDF/.env
Environment=HOME=/opt/Stirling-PDF
ExecStart=/usr/bin/java -Xms256m -Xmx2048m -jar /opt/Stirling-PDF/Stirling-PDF-with-login.jar
Restart=on-failure
RestartSec=10
TimeoutStopSec=60
UMask=0027
NoNewPrivileges=true

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable --now stirlingpdf.service

log "Installation abgeschlossen"
systemctl --no-pager --full status stirlingpdf.service || true
echo
echo "Weboberflaeche: http://$(hostname -I | awk '{print $1}'):8080"
echo "Initialer Login laut Stirling-Dokumentation: admin / stirling"
echo "Passwort beim ersten Login sofort aendern und die Anwendung nicht ungeschuetzt ins Internet stellen."
echo "Loganzeige: sudo journalctl -u stirlingpdf -f"
