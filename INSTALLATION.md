# Installation und Updates – QR-erweitertes Stirling PDF 3.1.0

Stand 12.10.2026 · Debian 13 · native JAR, **kein Docker**.

**Status:** Installationsskripte im Repository; noch **nicht** auf einem frisch installierten Zielsystem getestet. Eine erfolgreiche manuelle produktive Bereitstellung auf `scanner` ist dokumentiert. Dieses Repository enthält den QR-Patch und Installer, **nicht** die vollständige Stirling-Quellsoftware oder eine fertige JAR.

## Schnellinstallation: alles in einem Durchlauf

Auf einem frischen Debian-13-amd64-Server als root:

```bash
apt-get update && apt-get install -y git ca-certificates
git clone https://github.com/Markus4771/Stirling.git
cd Stirling
bash install.sh --fresh
```

Das Root-Skript installiert Java 25, Node/npm, go-task, OCR-/Office-Werkzeuge, baut den QR-Patch auf Stirling PDF v3.1.0 und legt den Dienst an. **Mindestens 8 GB RAM** für den Frontend-Build empfohlen; Node bekommt standardmäßig 6 GB Heap. Es setzt keine Samba-Freigaben und keine Processor-Pipelines auf. Die Anmeldung im Browser und ein QR-Test bleiben Teil der Abnahme.

Auf einer vorhandenen Installation nur bewusst und mit Wartungsfenster `bash install.sh --upgrade` verwenden (Sicherung durch untergeordnetes Installationsskript).

**Stand:** Dieses integrierte Ein-Befehl-Setup ist neu und noch nicht als Ganzes frisch getestet; manuelle Einzelabschnitte wurden auf `scanner2` erfolgreich geprüft.

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

## Samba-Verwaltungsoberfläche (ab 12.10.2026)

Die Root-`install.sh` ruft bei Neuinstallation bzw. Update zusätzlich den vorhandenen `samba-share-manager` auf. Dieser installiert Samba, den systemd-Dienst `samba-share-manager.service` und die Verwaltungs-GUI auf **Port 8085**. Die Oberfläche verwendet **Benutzer `admin`** und fragt bei der Einrichtung ein eigenes Passwort von mindestens 12 Zeichen ab. Für SMB-Freigaben wird ein `markus`-Konto verwendet; ein bestehendes Konto wird beibehalten, ein fehlendes Linux-Konto nur ohne initiales Linux-Passwort angelegt ; das SMB-Passwort wird später im Manager vergeben.

Auf einer bereits eingerichteten Stirling-Instanz (z. B. `scanner2`) **nicht `--fresh`** aufrufen, sondern:

```bash
cd /root/Stirling
git pull
bash install.sh --samba-only
```

Nach Installation:

```bash
systemctl status samba-share-manager.service --no-pager
ss -tlnp | grep ':8085'
```

Weboberfläche: `http://SERVER-IP:8085/`. Ohne TLS ausschließlich im geschützten LAN nutzen; **nicht ins Internet freigeben**. Das Skript legt **keine** Samba-Freigaben und **keine** Processor-Automatisierung an; diese müssen separat eingerichtet werden. Bestehende Share-Manager-Installationen werden zum Schutz der gespeicherten GUI-Zugangsdaten nicht automatisch überschrieben.

**Hinweis:** Die automatische Samba-Integration ist in GitHub implementiert, auf einem frischen System aber noch nicht end-to-end getestet.

## Aktueller Gesamtstand für frisches Debian 13 (13.10.2026)

Auf einer **leeren Debian-13-amd64-VM** als root installieren:

```bash
apt update && apt install -y git ca-certificates
cd /root
git clone https://github.com/Markus4771/Stirling.git
cd Stirling
bash install.sh --fresh
```

Das Skript baut Stirling PDF mit der QR-Erweiterung, installiert Stirling auf Port **8080** sowie Samba und den eigenen Samba-Share-Manager auf Port **8085**. Es installiert Java 25, Node/npm, go-task, Python/Cryptography und PDF-/OCR-Werkzeuge. Bei 4 GB RAM wird bei Bedarf Swap für den Build aktiviert. Das GUI-Admin-Passwort (mindestens 12 Zeichen) wird während der Installation vergeben. Ein SMB-Passwort für das lokale Dateisystemkonto `markus` wird **nicht mehr vorab verlangt**.

**SMB-Benutzer mehrfach verwenden:** Direkt beim Anlegen jeder Freigabe Benutzername und Passwort angeben. Bereits vom Manager verwaltete SMB-Benutzer können mit demselben Passwort für weitere Freigaben verwendet werden. Passwortänderungen an gemeinsam genutzten Konten betreffen alle verknüpften Freigaben. Passwortanzeige per Augensymbol innerhalb der angemeldeten Verwaltungsoberfläche. Für Windows-Verbindungen auf dieselbe Server-IP denselben SMB-Benutzer verwenden.

**Ordner und Rechte:** Der Share-Manager setzt ACLs für den Dienstbenutzer `stirling` automatisch bei neuen Freigaben und bietet für bereits vorhandene die Aktion **Stirling-Zugriffsrechte setzen**. In Stirling PDF muss `/srv/samba-shares` zusätzlich unter **Einstellungen für Ordnerzugriff** als zulässiges Stammverzeichnis eingetragen werden; diese Einstellung nimmt der Installer noch nicht automatisch vor. Paperless-Consume ist als zusätzlicher Share-Typ verfügbar, aber Paperless selbst benötigt noch eine Verbindung zu diesem Ordner.

**Prüfung:** `systemctl is-active stirlingpdf smbd samba-share-manager`, `testparm -s`, GUI-Login auf Port 8080 und 8085, QR-Trennung sowie SMB-Verbindung mit zwei Netzlaufwerken testen. Das Skript prüft Dienste und Erreichbarkeit, jedoch noch nicht sämtliche fachlichen Abläufe. **Der gesamte aktuelle Neuinstallationsstand wurde noch nicht auf einer frisch aufgesetzten VM end-to-end verifiziert.**

## Erstanmeldung an der Samba-Weboberfläche (Stand 13.10.2026)

Bei einer **frischen Installation** erstellt das Setup ein **zufälliges Einmalpasswort** für den Webadministrator `admin` und zeigt es **einmal im Terminal** an. Beim ersten Login unter `http://SERVER-IP:8085` wird ausschließlich die Seite zur Passwortänderung freigeschaltet. Das neue Administratorpasswort muss mindestens **12 Zeichen** lang sein. Erst danach kann die Freigabenverwaltung genutzt werden.

Aus Sicherheitsgründen wird kein allgemein bekanntes festes Startpasswort ausgeliefert. Bei Updates bleiben bereits bestehende Zugangsdaten unverändert; eine Neuinstallation darf bestehende Anmeldedaten nicht überschreiben. Das Samba-GUI-Passwort ist unabhängig von den SMB-Passwörtern für Windows-Netzlaufwerke. Die Oberfläche nur im vertrauenswürdigen LAN oder hinter TLS betreiben.
