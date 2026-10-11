#!/usr/bin/env bash
# Prepare native QR GUI in an isolated Stirling PDF v3.1.0 checkout.
# Does not touch the live JAR, SMB shares or systemd services.
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CHECKOUT="${1:-$HOME/stirling-qr-gui-src}"
command -v git >/dev/null || { echo "git missing" >&2; exit 1; }
command -v python3 >/dev/null || { echo "python3 missing" >&2; exit 1; }
if [[ ! -e "$CHECKOUT" ]]; then
  git clone --branch v3.1.0 --depth 1 https://github.com/Stirling-Tools/Stirling-PDF.git "$CHECKOUT"
fi
[[ -d "$CHECKOUT/.git" ]] || { echo "Not a Git checkout: $CHECKOUT" >&2; exit 1; }
cd "$CHECKOUT"
[[ "$(git status --porcelain)" == "" ]] || { echo "Checkout contains local changes; stop to protect them." >&2; exit 1; }
[[ "$(git rev-parse HEAD)" == "$(git rev-list -n 1 v3.1.0)" ]] || { echo "Checkout is not v3.1.0" >&2; exit 1; }
python3 "$ROOT/patches/apply-qr-gui-v3.1.0.py" "$CHECKOUT"
echo "Source changes prepared. Build and functional testing still required."
