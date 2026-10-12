#!/usr/bin/env bash
# Restores backed-up JAR only; does not overwrite database, settings or SMB folders.
set -Eeuo pipefail
[[ "$EUID" -eq 0 ]] || { echo "Run with sudo" >&2; exit 1; }
[[ $# -eq 1 && "$1" = /* ]] || { echo "Usage: sudo bash scripts/rollback.sh /root/stirling-backup/pre-upgrade-TIMESTAMP"; exit 2; }
SNAP="$1"
[[ -f "$SNAP/Stirling-PDF-with-login.jar" ]] || { echo "Backup JAR not found" >&2; exit 1; }
systemctl stop stirlingpdf.service
install -o stirling -g stirling -m 0640 "$SNAP/Stirling-PDF-with-login.jar" /opt/Stirling-PDF/Stirling-PDF-with-login.jar
systemctl start stirlingpdf.service
systemctl is-active stirlingpdf.service
echo "JAR rolled back. Database/config NOT rolled back; verify compatibility and login."
