#!/usr/bin/env bash
# Safe first-time installation or controlled update of a locally built QR JAR.
# Does not create/alter Samba shares, pipelines, users in the Stirling database.
set -Eeuo pipefail
usage() { echo "Usage: sudo bash scripts/install.sh --fresh|--upgrade /absolute/path/stirling-pdf-3.1.0.jar"; exit 2; }
[[ $# -eq 2 ]] || usage
MODE="$1"; SOURCE="$2"
[[ "$MODE" == --fresh || "$MODE" == --upgrade ]] || usage
[[ "$EUID" -eq 0 ]] || { echo "Run with sudo" >&2; exit 1; }
[[ "$SOURCE" = /* && -s "$SOURCE" ]] || { echo "JAR path must be absolute and non-empty" >&2; exit 1; }
for tool in java install systemctl; do command -v "$tool" >/dev/null || { echo "Missing: $tool" >&2; exit 1; }; done
BASE=/opt/Stirling-PDF
TARGET="$BASE/Stirling-PDF-with-login.jar"
UNIT=/etc/systemd/system/stirlingpdf.service
BACKUPS=/root/stirling-backup
if [[ "$MODE" == --fresh ]]; then
  [[ ! -e "$TARGET" && ! -e "$UNIT" && ! -e "$BASE/configs" ]] || {
    echo "Existing installation/config found. Use --upgrade (does not reset configuration) or investigate manually." >&2; exit 1;
  }
else
  [[ -f "$TARGET" && -f "$UNIT" ]] || { echo "No existing Stirling installation to upgrade." >&2; exit 1; }
fi
id stirling >/dev/null 2>&1 || useradd --system --home-dir "$BASE" --shell /usr/sbin/nologin stirling
mkdir -p "$BACKUPS"
if [[ "$MODE" == --fresh ]]; then
  install -d -o stirling -g stirling -m 0750 "$BASE"
  install -d -o stirling -g stirling -m 0750 "$BASE/logs"
fi
STAGED="$(mktemp "$BASE/.stirling-new.XXXXXXXX.jar")"
trap 'rm -f "$STAGED"' EXIT
install -o stirling -g stirling -m 0640 "$SOURCE" "$STAGED"
if [[ "$MODE" == --upgrade ]]; then
  SNAP="$BACKUPS/pre-upgrade-$(date +%Y%m%d-%H%M%S)"
  mkdir -m 0700 "$SNAP"
  cp -a "$UNIT" "$SNAP/stirlingpdf.service"
  # Stop before copying H2 DB for consistency.
  systemctl stop stirlingpdf.service
  cp -a "$TARGET" "$SNAP/Stirling-PDF-with-login.jar"
  for p in "$BASE/.env" "$BASE/configs" "$BASE/customFiles" "$BASE/pipeline"; do
    [[ -e "$p" ]] && cp -a "$p" "$SNAP/"
  done
  printf '%s\n' "$SNAP" > "$BACKUPS/last-upgrade-backup.txt"
  echo "Stopped-service backup: $SNAP"
else
  install -d -o stirling -g stirling -m 0750 "$BASE/configs"
  install -d -o stirling -g stirling -m 0750 "$BASE/pipeline"
  install -d -o stirling -g stirling -m 0750 "$BASE/customFiles"
  cat > "$BASE/.env" <<'ENV'
SYSTEM_DEFAULTLOCALE=de-DE
SERVER_ADDRESS=0.0.0.0
SERVER_PORT=8080
SECURITY_ENABLELOGIN=true
ENV
  chown stirling:stirling "$BASE/.env"
  chmod 0600 "$BASE/.env"
  cat > "$UNIT" <<'UNIT'
[Unit]
Description=Stirling PDF QR Server
After=network-online.target
Wants=network-online.target
[Service]
Type=simple
User=stirling
Group=stirling
WorkingDirectory=/opt/Stirling-PDF
EnvironmentFile=/opt/Stirling-PDF/.env
ExecStart=/usr/bin/java -Xms256m -Xmx2048m -jar /opt/Stirling-PDF/Stirling-PDF-with-login.jar
Restart=on-failure
RestartSec=10
[Install]
WantedBy=multi-user.target
UNIT
fi
mv -f "$STAGED" "$TARGET"
trap - EXIT
systemctl daemon-reload
if [[ "$MODE" == --fresh ]]; then systemctl enable stirlingpdf.service; fi
systemctl start stirlingpdf.service
echo "Service status:"
systemctl is-active stirlingpdf.service
echo "Check login, split, QR test and Processor after startup."
if [[ "$MODE" == --upgrade ]]; then echo "Rollback backup: $SNAP"; fi
