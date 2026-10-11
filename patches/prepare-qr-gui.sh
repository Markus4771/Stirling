#!/usr/bin/env bash
# Safe local preparation of Stirling PDF v3.1.0 QR-GUI source.
# Does not touch /opt/Stirling-PDF or running services.
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CHECKOUT="${1:-$HOME/stirling-qr-gui-src}"
[[ ! -e "$CHECKOUT" ]] || { echo "Target already exists: $CHECKOUT" >&2; exit 1; }
command -v git >/dev/null || { echo "git missing" >&2; exit 1; }
git clone --branch v3.1.0 --depth 1 https://github.com/Stirling-Tools/Stirling-PDF.git "$CHECKOUT"
cd "$CHECKOUT"
git apply --check "$ROOT/patches/qr-gui-v1.patch"
git apply "$ROOT/patches/qr-gui-v1.patch"
echo "Patch applied to $CHECKOUT."
echo "Next: regenerate tool API types (task frontend:tool-models), run checks and build."
echo "Do not deploy until backend/frontend compilation and integration tests pass."
