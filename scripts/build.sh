#!/usr/bin/env bash
# Reproducible Stirling PDF v3.1.0 QR build. Never touches the installed service.
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CHECKOUT="${CHECKOUT:-$HOME/stirling-qr-gui-src}"
if [[ ! -f "$CHECKOUT/gradlew" ]]; then
  "$ROOT/patches/prepare-qr-gui.sh" "$CHECKOUT"
elif [[ -z "$(git -C "$CHECKOUT" status --porcelain)" ]]; then
  "$ROOT/patches/prepare-qr-gui.sh" "$CHECKOUT"
else
  echo "Existing modified checkout: $CHECKOUT"
  echo "Assuming QR patch already applied; verifying required fields."
  grep -q 'keepQrPage' "$CHECKOUT/app/core/src/main/java/stirling/software/SPDF/model/api/misc/AutoSplitPdfRequest.java" || {
    echo "QR patch not detected; refusing to overwrite local changes." >&2; exit 1;
  }
fi
for tool in task node npm java; do command -v "$tool" >/dev/null || { echo "Missing dependency: $tool" >&2; exit 1; }; done
cd "$CHECKOUT"
./gradlew :stirling-pdf:bootJar \
  -PbuildWithFrontend=true \
  -PfrontendMode=proprietary \
  -PbuildWithPortal=true \
  --rerun-tasks --no-daemon
JAR="$CHECKOUT/app/core/build/libs/stirling-pdf-3.1.0.jar"
test -s "$JAR"
sha256sum "$JAR"
echo "JAR ready: $JAR"
