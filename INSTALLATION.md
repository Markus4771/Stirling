# Installation und Updates – QR-erweitertes Stirling PDF 3.1.0

Stand 12.10.2026 · Debian 13 · native JAR, **kein Docker**.

**Status:** Installationsskripte im Repository; noch **nicht** auf einem frisch installierten Zielsystem getestet. Eine erfolgreiche manuelle produktive Bereitstellung auf `scanner` ist dokumentiert. Dieses Repository enthält den QR-Patch und Installer, **nicht** die vollständige Stirling-Quellsoftware oder eine fertige JAR.

## 1. Voraussetzungen
- Debian 13 (amd64), Java 25 JDK, Node 20.19+ inklusive npm, git, curl, Python 3, go-task (`task`) und Gradle-Wrapper aus dem Stirling-Checkout.
- Auf dem Zielsystem: OCRmyPDF, Tesseract (Deutsch/Englisch), Ghostscript, LibreOffice, pdf tools nach den Anforderungen der genutzten Funktionen.
- `task` ist **go-task** (nicht Debians `tasksel`). Offizieller Installationsweg: https://taskfile.dev/installation/
- Für einen reproduzierbaren Build sind die Upstream-Quellen am **Tag v3.1.0**, Netzverbindung sowie passende npm/Gradle-Abhängigkeiten erforderlich.

```bash
sudo apt update
sudo apt install -y git curl python3 unzip libreoffice tesseract-ocr tesseract-ocr-deu tesseract-ocr-eng ocrmypdf ghostscript poppler-utils pngquant
java -version
node --version
npm --version
task --version
```

Java, Node und go-task gegebenenfalls separat installieren; oben wird ihre Verfügbarkeit **nur geprüft**.

## 2. Projekt und QR-Patch bauen

```bash
git clone https://github.com/Markus4771/Stirling.git
cd Stirling
bash scripts/build.sh
```

Build ohne erneutes Patchen auf einem bereits modifizierten Checkout. Bevorzugte Build-Flags:

```bash
./gradlew :stirling-pdf:bootJar \
  -PbuildWithFrontend=true \
  -PfrontendMode=proprietary \
  -PbuildWithPortal=true \
  --rerun-tasks --no-daemon
```

Das Core-only-Frontend `-PfrontendMode=core -PbuildWithPortal=false` **nicht** für eine Installation mit aktiver Benutzeranmeldung verwenden: Login und Split-Navigation waren damit fehlerhaft.

Ergebnis: `$HOME/stirling-qr-gui-src/app/core/build/libs/stirling-pdf-3.1.0.jar`.

## 3. Neuinstallation

Nur für einen **leeren, noch nicht eingerichteten** Host. Das Skript bricht bei gefundenem Dienst, JAR oder Konfigurationsverzeichnis ab. Es legt Serviceuser `stirling`, Basisverzeichnisse, `.env` und systemd-Dienst an.

```bash
sudo bash scripts/install.sh --fresh "$HOME/stirling-qr-gui-src/app/core/build/libs/stirling-pdf-3.1.0.jar"
```

Danach Port 8080, Anmeldemaske, PDF-Aufteilen und QR-Test prüfen. Neue Benutzer/Passwörter und Scanner-Einrichtungen über die Anwendung erstellen. Port 8080 **nicht ohne TLS/Reverse Proxy öffentlich bereitstellen**.

## 4. Update der bestehenden Installation

Vorher Wartungsfenster und Stillstand der Scanverarbeitung sicherstellen:

```bash
sudo bash scripts/install.sh --upgrade "$HOME/stirling-qr-gui-src/app/core/build/libs/stirling-pdf-3.1.0.jar"
```

Das Skript stoppt den Dienst und kopiert **bei gestopptem Dienst** die alte JAR, `.env`, Konfiguration, Pipeline und ggf. `customFiles` nach `/root/stirling-backup/pre-upgrade-ZEITSTEMPEL`. Anschließend wird die neue JAR installiert und der vorhandene Dienst gestartet.

**Achtung:** Für eine Produktionsumgebung existierende Daten, Volumes, externe Ressourcen und Dienste separat inventarisieren und vollständig sichern. Das Skript sichert nur die genannten Pfade; es ist kein vollumfänglicher Disaster-Recovery-Mechanismus. Auf `scanner` ist bereits eine funktionierende QR-JAR produktiv installiert; ein erneutes Update ist **nicht notwendig**, um dieses Repository vorzubereiten.

## 5. Rückfall

```bash
sudo bash scripts/rollback.sh /root/stirling-backup/pre-upgrade-ZEITSTEMPEL
```

Nur die vorherige JAR wird wiederhergestellt; **keine automatische Datenbankrücksetzung**. Nach dem Rückfall Anmeldung, Datenbankkompatibilität, Pipelines und Ausgabe prüfen.

## 6. Funktionstest vor Freigabe

1. Neue Instanz isoliert mit Login testen.
2. 10-seitige QR-Testdatei: `SCAN:TEST` auf Seiten 2,5,7; QR-Seiten behalten; Duplex aus → vier PDFs (1,3,2,4 Seiten).
3. Mit der separaten automatischen QR-Pipeline testen; prüfen, ob vier Einzeldateien einschließlich OCR wirklich im Ausgang erscheinen.
4. Originaldatei-Verhalten, Dubletten und Queue-Limit unter Last verifizieren.
5. Bestehende `Test`-OCR-Automatisierung nicht unbeabsichtigt überschreiben.

## Grenzen
- `scripts/install.sh` verändert **keine** Samba-Freigaben oder bestehenden Processor-Pipelines; diese sind installationsspezifisch.
- QR-Erweiterung basiert auf einem Patch auf einen festgehaltenen Upstream-Tag; Updates auf eine neue Stirling-Version benötigen Patch-Anpassung und Regressionstests.
- Skripte sind noch nicht durch ein automatisiertes Integrations-/CI-Testverfahren validiert.
