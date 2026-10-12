# NEUER-CHAT – Stirling PDF Scanserver

Stand: 12.10.2026

## System
- Hostname: `scanner`
- Debian 13.7, Stirling PDF v3.1.0 (JAR, **kein Docker**), Java 25
- Installation: `/opt/Stirling-PDF`
- systemd-Dienst: `stirlingpdf.service`, Benutzer: `stirling`
- Samba-Freigaben werden mit dem **eigenen Samba-Verwaltungstool**, nicht mit Webmin, verwaltet

## Aktuelle Ordner
- SMB-Eingang: `/srv/samba-shares/Scan-Eingang`
- SMB-Ausgang: `/srv/samba-shares/Scan-Ausgang`
- Alte dateibasierte Pipeline: `/opt/Stirling-PDF/pipeline/watchedFolders` (nicht mit dem Processor verwechseln)
- Alte `finishedFolders`-Verzeichnisse waren Ziel der Bereinigung.

## Grafische Automatisierung
- Name: **Test**
- Ablauf: **Scan-Eingang → OCR & Scans bereinigen → Scan-Ausgang**
- Test-PDFs wurden im SMB-Eingang abgelegt.

## Verifizierte Diagnosen
- `sudo -u stirling ls -la` funktioniert auf Eingang und Ausgang.
- `sudo -u stirling touch` funktioniert auf Eingang und Ausgang.
- Service läuft mit `User=stirling`, `Group=stirling`.
- Frühere Logs: `Failed to resolve source 'folder' ... /srv/samba-shares/Scan-Eingang`.
- Parallel meldete der Legacy-Watcher fehlende JSON-Dateien in `pipeline/watchedFolders`; diese Warnung betrifft **nicht zwingend** die grafische Automatisierung.
- Nach dem Dienstneustart zeigte das Log `Running policy ... (Test)`, was einen Start, noch keinen erfolgreichen Abschluss belegt.

## Zuletzt angepasste Konfiguration
In der zuvor leeren Datei `/opt/Stirling-PDF/configs/custom_settings.yml` wurde empfohlen, folgendes einzutragen:

```yaml
policies:
  allowedFolderRoots:
    - /srv/samba-shares/Scan-Eingang
    - /srv/samba-shares/Scan-Ausgang
```

Danach Dienst neu starten:
```bash
sudo systemctl restart stirlingpdf.service
```

Der Benutzer meldete: **„jetzt geht es scheinbar“**. Ein vollständiger End-to-End-Test ist noch zu dokumentieren.

## Samba-Verwaltung
- Freigaben `Scan-Eingang` und `Scan-Ausgang` im eigenen Tool verwalten.
- `install.sh` richtet lokale Verzeichnisse und ACLs ein, aber keine SMB-Freigaben; Integration mit dem eigenen Tool setzt eine bekannte Schnittstelle voraus.
- Keine Webmin-Abhängigkeit.

## QR-GUI-Erweiterung: ursprünglicher Teststand 12.10.2026

Die native QR-Code-Funktion wurde im **separaten Testsystem** auf Stirling PDF v3.1.0 erfolgreich erstellt und manuell getestet.

- GitHub-Patch: `patches/apply-qr-gui-v3.1.0.py` und `patches/prepare-qr-gui.sh`
- Lokal geändertes offizielles Source-Checkout: `~/stirling-qr-gui-src`; **nicht** erneut `prepare-qr-gui.sh` auf das bereits geänderte Checkout anwenden
- Gebautes JAR: `~/stirling-qr-gui-src/app/core/build/libs/stirling-pdf-3.1.0.jar`
- Isoliertes Testverzeichnis `~/stirling-qr-test`; Start auf `127.0.0.1:8081`, Zugriff im Browser per SSH-Tunnel `http://localhost:8081/split`
- Für die Testinstanz: `-Djava.io.tmpdir="$HOME/stirling-qr-test/tmp"` sowie `--security.enableLogin=false`, nur mit `--server.address=127.0.0.1`
- `curl` für `/split` und `/api/v1/config/endpoints-availability` ergab zuletzt jeweils HTTP 200, nachdem die Testinstanz wieder lief.
- Test: Zehnseitige PDF mit QR-Inhalt `SCAN:TEST` auf den Seiten 2, 5 und 7. Einstellung **Exakter Inhalt**, **SCAN:TEST**, **QR-Code-Seite behalten an**, **Duplex aus**. Vier PDFs mit Seiten **1**, **2–4**, **5–6**, **7–10** wurden erzeugt. Screenshot bestätigt QR-Seiten in den Ausgaben.
- Ein zeitweise nur kurz angezeigtes „Aufteilen“-Untermenü ist noch nicht als Navigationsbug eingegrenzt; direkter Werkzeugaufruf `/split` funktioniert nach Serverneustart.
- **Historischer Stand:** Zu diesem Zeitpunkt war Port 8080 noch nicht umgestellt. Siehe aktuellen Produktivstand unten.

## Nächste Aufgaben
1. Mit frischer Test-PDF bestätigen: Eingang aufgenommen, OCR erfolgt, Datei im Ausgang, inhaltlich durchsuchbar.
2. Originaldatei-Verhalten der Automatisierung klären.
3. Ordnerzugriff/ACL-Vererbung und Samba-Konfiguration dokumentieren, damit Rechte für neue Dateien zuverlässig bleiben.
4. Native QR-Trennung mit echten Scanner-PDFs (schief, gedreht, unscharf), weiteren QR-Inhalten und dem Processor testen.
5. Alte nicht genutzte Watched-Folder-Struktur erst nach Prüfung bereinigen; keine produktiven Dateien löschen.
6. Backup der Konfiguration, Samba-Konfiguration und systemd-Service.
7. Navigation/Untermenü unter Testbedingungen prüfen, dann Deploy- und Rollback-Plan erstellen.

Weitere Installationsdetails: [README.md](README.md).

## Vorbereitung Produktivbetrieb (12.10.2026, historischer Plan)

**Historischer Plan vor der inzwischen durchgeführten Produktivumstellung.** Vor dem Austausch der produktiven JAR den Dienstpfad, die tatsächliche Version und ein vollständiges Backup prüfen. Das einzige bestätigte End-to-End-Ergebnis ist bislang der manuelle digitale QR-Test. Ungeprüft sind Scanner-PDFs und Automation.

### Nichtinvasive Bestandsaufnahme

```bash
sudo systemctl cat stirlingpdf.service
sudo systemctl status stirlingpdf.service --no-pager
ls -lh /opt/Stirling-PDF/Stirling-PDF-with-login.jar ~/stirling-qr-gui-src/app/core/build/libs/stirling-pdf-3.1.0.jar
sha256sum /opt/Stirling-PDF/Stirling-PDF-with-login.jar ~/stirling-qr-gui-src/app/core/build/libs/stirling-pdf-3.1.0.jar
```

### Sicherungsumfang

- Original-JAR unter `/opt/Stirling-PDF/Stirling-PDF-with-login.jar`
- Konfiguration `/opt/Stirling-PDF/configs` und `.env` (Zugangsdaten geschützt behandeln)
- `/opt/Stirling-PDF/pipeline`, ggf. `/opt/Stirling-PDF/customFiles`
- `/etc/systemd/system/stirlingpdf.service`
- Datenbank und anwendungsspezifische Daten nach Prüfung ihrer tatsächlichen Verzeichnisse und des Sicherungsverfahrens
- Samba-Konfiguration (separat); keine Scandateien überschreiben

### Rollout-Vorgehen, erst nach Freigabe

1. Laufende automatisierte Verarbeitung anhalten und konsistentes Backup verifizieren.
2. Alte JAR als unveränderbare Rückfallversion sichern; prüfbare Hashes dokumentieren.
3. Test-JAR in Staging unter dem endgültigen Benutzer und **mit einer Kopie**, nicht dem produktiven Datenverzeichnis testen.
4. Wartungsfenster: Dienst stoppen, JAR atomar austauschen, Eigentümer/Rechte prüfen, Dienst starten.
5. API, Login, UI, bestehende OCR-/Ordner-Automatisierung und native QR-Trennung verifizieren.
6. Bei Fehlfunktion Dienst stoppen, Original-JAR wiederherstellen und zurückstarten; Konfigurations-/Datenbankmigrationen gesondert betrachten.

**Kein automatischer Austausch der JAR:** Die produktive und die selbst gebaute v3.1.0-Version müssen hinsichtlich Konfiguration, Datenbank und Funktionen kompatibel sein.

## Produktivstand nach QR-Fix – 12.10.2026 (aktuell)

**Bestätigt durch den Anwender:** Die mit Anmeldung ausgelieferte, erweiterte Stirling-PDF-v3.1.0-JAR läuft produktiv auf `scanner`, Port `8080`. Anmeldung, Werkzeug **Aufteilen/Split** und native QR-Code-Trennung funktionieren. Screenshot vom 12.10.2026 zeigt vier Ergebnisdateien mit 1, 3, 2 und 4 Seiten nach Teilung einer 10-seitigen Test-PDF.

### Ursache und Lösung des UI-/Login-Problems

- Erster Eigenbau nutzte `-PfrontendMode=core -PbuildWithPortal=false`. Bei eingeschalteter Anmeldung zeigte `/login` nicht die Login-Maske; ein `401` auf Auth-/Konfigurations-APIs führte zu Navigationsproblemen, auch bei `/split`.
- Auch die isolierte Instanz auf `127.0.0.1:8082` reproduzierte den Fehler **mit** aktivierter Anmeldung; ohne Anmeldung war die QR-Trennung bereits erfolgreich.
- Der erste vollständige Build scheiterte zunächst daran, dass der externe Befehl `task` (go-task Task-Runner) nicht installiert war. Debian-Pakete `tasksel`, `task-german` etc. sind kein Ersatz.
- Nach Bereitstellung des Task-Runners wurde das Frontend mit Modus `proprietary` und Portal gebaut. Im Build-Log: `BUILD SUCCESSFUL` (34 actionable tasks, 33 executed, 1 up-to-date).

### Reproduzierbarer Build

Im bereits gepatchten Checkout `/home/markus/stirling-qr-gui-src`:

```bash
cd ~/stirling-qr-gui-src
./gradlew :stirling-pdf:bootJar \\
  -PbuildWithFrontend=true \\
  -PfrontendMode=proprietary \\
  -PbuildWithPortal=true \\
  --rerun-tasks \\
  --no-daemon
```

JAR-Ausgabe: `app/core/build/libs/stirling-pdf-3.1.0.jar`. Die vorbereitenden QR-Patches **nicht nochmals** auf den geänderten Checkout anwenden.

### Tests und Rollout

- Isoliertes Testsystem: `/opt/Stirling-PDF-qr-test-isolated`, Port `127.0.0.1:8082`, Login aktiviert; Anwender bestätigte Login und Split inklusive QR-Test.
- Produktiv: `/opt/Stirling-PDF/Stirling-PDF-with-login.jar`, `stirlingpdf.service`, Port `8080`; Anwender meldete erfolgreichen Start, Login und QR-Test.
- Test-PDF: 10 Originalseiten, QR-Inhalt `SCAN:TEST` auf Seiten 2, 5, 7. Optionen: **Exakter Inhalt**, **QR-Seite behalten = an**, **Duplex = aus**. Ergebnis: vier PDFs mit Originalseiten **1**, **2–4**, **5–6**, **7–10** (Screenshot bestätigt).
- Vor der Umstellung angelegte Rückfallebene: `/root/stirling-backup/Stirling-PDF-with-login.jar` (Original-JAR); zusätzlich war vor dem Austausch eine Sicherung unter `/root/stirling-backup/vor-qr-fix` vorgesehen. Existenz der letzteren bei Bedarf auf dem Server prüfen.
- Einstellungen/Benutzer/Datenbank wurden beim JAR-Austausch nicht absichtlich zurückgesetzt; Integrität im laufenden Betrieb beobachten.

### Offen / nächste sinnvolle Tests

1. End-to-End-Ausführung der grafischen OCR-Ordnerautomatisierung `Test` nach dem Produktiv-Rollout separat verifizieren: Scan-Eingang → OCR → Scan-Ausgang, OCR-Durchsuchbarkeit und Originaldatei-Verhalten.
2. Mit echten gescannten, gedrehten, schiefen, schwachen und Duplex-QR-Seiten testen.
3. Separat prüfen, ob die native QR-Trennung in der grafischen Automatisierung/Processor eingebunden werden kann. Der GUI-Test belegt dies **nicht**.
4. Rückfall-JAR, produktive Datenbank und Konfiguration regelmäßig sichern; funktionierenden Stand mit Build-Flags reproduzierbar halten.
