#!/usr/bin/env bash
# Stirling PDF v3.1.0 with native QR splitter: complete Debian 13 installer.
# Build from pinned upstream tag; no downloaded stock JAR that lacks the QR patch.
# Existing installations are protected by scripts/install.sh.
set -Eeuo pipefail

log() { printf '\n==> %s\n' "$*"; }
die() { echo "FEHLER: $*" >&2; exit 1; }
trap 'echo "Installation abgebrochen (Zeile $LINENO). Bestehende Installation nicht manuell löschen." >&2' ERR

[[ "${EUID}" -eq 0 ]] || die "Als root starten: sudo bash install.sh --fresh"
[[ $# -eq 1 && ( "$1" == "--fresh" || "$1" == "--upgrade" ) ]] || die "Aufruf: sudo bash install.sh --fresh|--upgrade"
MODE="$1"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. /etc/os-release
[[ "${ID:-}" == "debian" && "${VERSION_ID%%.*}" == "13" ]] || die "Nur Debian 13 wird unterstützt."
[[ "$(uname -m)" == "x86_64" ]] || die "Derzeit nur amd64 getestet."

# Strictly verify target before apt/package or build changes.
if [[ "$MODE" == "--fresh" ]]; then
  [[ ! -e /etc/systemd/system/stirlingpdf.service && ! -e /opt/Stirling-PDF/Stirling-PDF-with-login.jar && ! -e /opt/Stirling-PDF/configs ]] || die "Stirling-Konfiguration/Installation vorhanden. --fresh wird zum Schutz abgebrochen."
else
  [[ -f /etc/systemd/system/stirlingpdf.service && -f /opt/Stirling-PDF/Stirling-PDF-with-login.jar ]] || die "Keine vorhandene Installation zum Aktualisieren gefunden."
fi

export DEBIAN_FRONTEND=noninteractive
log "Debian-Abhängigkeiten installieren"
apt-get update
apt-get install -y \
  ca-certificates curl git python3 unzip wget bash build-essential \
  openjdk-25-jdk nodejs npm golang-go \
  libreoffice tesseract-ocr tesseract-ocr-deu tesseract-ocr-eng \
  ocrmypdf ghostscript poppler-utils qpdf pngquant \
  python3-opencv imagemagick acl fonts-dejavu-core

JAVA_MAJOR="$(java -version 2>&1 | sed -n '1s/.*version "\([0-9]*\).*/\1/p')"
[[ "$JAVA_MAJOR" =~ ^[0-9]+$ && "$JAVA_MAJOR" -ge 25 ]] || die "Java 25 erforderlich."
NODE_VERSION="$(node -p 'process.versions.node')"
node -e 'let [a,b]=process.versions.node.split(".").map(Number);process.exit(a>20||(a===20&&b>=19)?0:1)' || die "Node >=20.19 erforderlich (gefunden: $NODE_VERSION)."

if [[ "$(npm --version | cut -d. -f1)" -lt 11 ]]; then
  log "npm 11.21.0 für Stirling-Frontend installieren"
  npm install -g npm@11.21.0
  hash -r
fi
[[ "$(npm --version | cut -d. -f1)" -ge 11 ]] || die "npm 11 konnte nicht aktiviert werden."

if ! command -v task >/dev/null 2>&1; then
  log "go-task v3.48.0 installieren"
  GOBIN=/usr/local/bin go install github.com/go-task/task/v3/cmd/task@v3.48.0
fi
task --version

TOTAL_MEM_KB="$(awk '/MemTotal:/ {print $2}' /proc/meminfo)"
if (( TOTAL_MEM_KB < 7*1024*1024 )); then
  die "Für den vollständigen Frontend-Build mindestens 8 GB VM-RAM empfohlen; aktuell $(awk "BEGIN {printf \"%.1f\", $TOTAL_MEM_KB/1024/1024}") GiB. VM-RAM erhöhen und erneut starten."
fi
export NODE_OPTIONS="${NODE_OPTIONS:---max-old-space-size=6144}"

log "QR-Stirling aus Upstream v3.1.0 bauen"
# Use explicit build root for root; prevent checkout from an unrelated user.
export CHECKOUT=/root/stirling-qr-gui-src
bash "$ROOT/scripts/build.sh"
JAR="$CHECKOUT/app/core/build/libs/stirling-pdf-3.1.0.jar"
[[ -s "$JAR" ]] || die "Build lieferte keine JAR."

log "Stirling installieren: $MODE"
bash "$ROOT/scripts/install.sh" "$MODE" "$JAR"

log "Webserver auf Port 8080 prüfen (Start kann dauern)"
READY=0
for i in $(seq 1 45); do
  if curl --silent --fail --max-time 3 --output /dev/null http://127.0.0.1:8080/; then
    READY=1
    break
  fi
  if ! systemctl is-active --quiet stirlingpdf.service; then
    echo "Dienst noch nicht aktiv oder neu gestartet; Log folgt:"
    journalctl -u stirlingpdf.service -n 40 --no-pager || true
  fi
  sleep 2
done
if (( READY == 0 )); then
  echo "Webserver nach Prüfung nicht erreichbar. Diagnose:"
  systemctl status stirlingpdf.service --no-pager -l || true
  journalctl -u stirlingpdf.service -n 60 --no-pager || true
  exit 1
fi
echo "HTTP antwortet: http://$(hostname -I | awk '{print $1}'):8080"
echo "Anmeldung, QR-Split und Processor im Browser testen."
echo "Das Skript richtet KEINE SMB-Freigaben und KEINE Automatisierungs-Pipelines ein."
