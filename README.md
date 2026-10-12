# Stirling PDF – Installation und Scanserver

Dokumentation für den Server `scanner` auf **Debian 13.7**, ohne Docker. Dieses Repository dokumentiert die Installation von Stirling PDF als geplanten Ersatz für ScanPro; es enthält nicht die Stirling-PDF-Quellsoftware.

## Bestätigter Ist-Stand (12.10.2026)

- OpenJDK 25.0.4.1
- Stirling PDF unter `/opt/Stirling-PDF`
- systemd-Dienst `stirlingpdf` läuft und startet automatisch
- Weboberfläche funktioniert auf `http://SERVER-IP:8080`
- Samba-Freigaben `Scan-Eingang` und `Scan-Ausgang` sind vorhanden; lokale Lese- und Schreibtests als Benutzer `stirling` waren erfolgreich.
- Grafische Automatisierung `Test`: Scan-Eingang → OCR & Scans bereinigen → Scan-Ausgang; nach Konfigurationsanpassung funktionierte die Verarbeitung nach Anwenderangabe. Ein erneuter End-to-End-Test **nach dem JAR-Austausch** ist noch sinnvoll.
- **Produktiver QR-Code-Fix (12.10.2026):** Login, PDF-Aufteilen und native QR-Code-Trennung auf Port `8080` erfolgreich vom Anwender getestet; vier Dateien aus der 10-seitigen Test-PDF korrekt erzeugt.

## 1. Debian vorbereiten

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y wget curl git unzip libreoffice tesseract-ocr tesseract-ocr-deu tesseract-ocr-eng ocrmypdf poppler-utils python3 python3-pip python3-opencv pngquant
sudo apt install -y openjdk-25-jdk
java -version
```

Java 25 ist auf der vorhandenen Debian-13-Installation verfügbar. Auf anderen Debian-Versionen zuerst Paketverfügbarkeit prüfen.

## 2. JAR installieren

```bash
sudo mkdir -p /opt/Stirling-PDF
cd /opt/Stirling-PDF
sudo wget -O Stirling-PDF-with-login.jar https://files.stirlingpdf.com/Stirling-PDF-with-login.jar
cd /tmp
git clone --depth 1 https://github.com/Stirling-Tools/Stirling-PDF.git
sudo cp -r Stirling-PDF/scripts /opt/Stirling-PDF/
cd /opt/Stirling-PDF
java -jar Stirling-PDF-with-login.jar
```

Mit Strg+C beenden. Für reproduzierbare Updates JAR-Version und dazu passende Skripte festhalten.

## 3. systemd-Dienst

```bash
id stirling || sudo useradd --system --home-dir /opt/Stirling-PDF --shell /usr/sbin/nologin stirling
sudo chown -R stirling:stirling /opt/Stirling-PDF
sudo nano /opt/Stirling-PDF/.env
```

`.env`:

```ini
SYSTEM_DEFAULTLOCALE=de-DE
SERVER_ADDRESS=0.0.0.0
SERVER_PORT=8080
SECURITY_ENABLELOGIN=true
```

```bash
sudo chown stirling:stirling /opt/Stirling-PDF/.env
sudo chmod 600 /opt/Stirling-PDF/.env
sudo nano /etc/systemd/system/stirlingpdf.service
```

```ini
[Unit]
Description=Stirling PDF Server
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
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now stirlingpdf
sudo systemctl status stirlingpdf
curl -I http://127.0.0.1:8080
sudo journalctl -u stirlingpdf -n 50 --no-pager
```

Weboberfläche über `http://SERVER-IP:8080` aufrufen. Admin-Anmeldedaten umgehend absichern; nicht ohne HTTPS und Zugangskontrolle aus dem Internet erreichbar machen.

## 4. SMB-Integration: zwei Varianten

### A. Stirling PDF liest von bestehenden SMB-Shares (empfohlen, wenn diese bereits existieren)

Neuere Stirling-PDF-Versionen bieten unter **Processor → Integrations → SMB / Network Share** eine integrierte SMB-*Eingangsquelle*.

1. Unter **Processor → Integrations** eine SMB-Verbindung mit Host, Share und Zugangsdaten anlegen.
2. Unter **Processor → Sources** eine Quelle vom Typ Network Drive (SMB) erstellen.
3. Unter **Processor → Pipelines** einen Verarbeitungsablauf zuweisen.
4. Unter **After processing** einstellen, ob Originale gelöscht oder behalten werden sollen.
5. Zunächst mit Testdateien prüfen.

Bei SMB-Servern im privaten LAN gegebenenfalls in `/opt/Stirling-PDF/.env` gezielt erlauben:

```ini
POLICIES_ALLOWEDPRIVATENETWORKHOSTS=nas.intern.example
```

Der Name ist ein Beispiel und durch den tatsächlichen Host zu ersetzen. Alternativ, weniger restriktiv: `POLICIES_ALLOWPRIVATENETWORKSOURCES=true`. Danach `sudo systemctl restart stirlingpdf`.

**Wichtig:** Laut aktueller Dokumentation ist SMB in Processor als Eingangsquelle verfügbar; eine SMB-*Zielquelle* ist noch als „Coming soon“ markiert. Ausgabe daher in einen lokalen Ordner und optional über Samba exportieren.

### B. Scan-Geräte schreiben direkt auf SMB-Freigaben des Debian-Servers

Samba wird über das eigene Samba-Verwaltungstool eingerichtet. Für die aktuelle Installation gelten ausschließlich die Verzeichnisse unter `/srv/samba-shares/`. Ursprünglicher Plan für weitere Profile (noch nicht der Ist-Stand):

```bash
sudo apt install -y samba smbclient
sudo mkdir -p /opt/Stirling-PDF/pipeline/watchedFolders/{Standard,QR-Code,OCR,Optimierung}
sudo mkdir -p /opt/Stirling-PDF/pipeline/finishedFolders/{Standard,QR-Code,OCR,Optimierung}
sudo chown -R stirling:stirling /opt/Stirling-PDF/pipeline
sudo smbpasswd -a markus
sudo cp /etc/samba/smb.conf /etc/samba/smb.conf.bak
```

Die frühere Vorlage mit `force user = stirling` und Ausgaben unter `/opt/Stirling-PDF/pipeline/finishedFolders` ist **nicht** die aktuelle Konfiguration. Bereits bestehende Freigaben im eigenen Verwaltungstool nicht überschreiben. Nach Anpassungen:

```bash
sudo testparm -s
sudo systemctl restart smbd
smbclient -L localhost -U markus
```

Geplante Freigaben: `Scan-Standard`, `Scan-QR`, `Scan-OCR`, `Scan-Optimierung`, `Scan-Ausgang`. Eingangs- und Ausgangsordner voneinander trennen und Pipeline-Konfigurationen vor unberechtigtem SMB-Zugriff schützen. Der lokale Folder-Scanning-Mechanismus und der neuere Processor sind **verschiedene** Automatisierungswege; vor dem Produktivbetrieb pro Eingang genau einen festlegen.

## 5. Samba-Freigaben über das eigene Samba-Verwaltungstool

**Kein Webmin erforderlich.** Auf `scanner` wird die vorhandene eigene Samba-Verwaltungsoberfläche zur Anlage und Verwaltung von SMB-Freigaben verwendet.

| Name der SMB-Freigabe | Lokaler Ordner |
| --- | --- |
| `Scan-Eingang` | `/srv/samba-shares/Scan-Eingang` |
| `Scan-Ausgang` | `/srv/samba-shares/Scan-Ausgang` |

Die Freigaben sind bereits eingerichtet. In der Verwaltungsoberfläche Schreibzugriff für den Scanner beziehungsweise berechtigte SMB-Benutzer und passende Linux-Dateirechte sicherstellen. Für `stirling` lokalen Lese-/Schreibzugriff einrichten; ACLs ermöglichen das unabhängig vom Eigentümer. Für neu über Samba hochgeladene Dateien auch die effektiven Samba-Rechte und Vererbung prüfen.

Nach Änderungen an der Samba-Konfiguration:

```bash
sudo testparm -s
sudo systemctl reload smbd
sudo -u stirling ls -la /srv/samba-shares/Scan-Eingang
sudo -u stirling ls -la /srv/samba-shares/Scan-Ausgang
```

Die lokale Anwendung kann nur dann automatisiert durch `install.sh` angesprochen werden, wenn ihre Schnittstelle und Befehle bekannt sind. Das Stirling-Installationsskript bereitet lediglich die lokalen Ordner und ACLs vor. Es installiert weder Webmin noch überschreibt es vorhandene Samba-Freigaben.

## 6. Aktuelle Ordnerautomatisierung und Fehlerbehebung (11.10.2026)

### Tatsächlicher Aufbau

| Komponente | Pfad / Einstellung |
| --- | --- |
| Betrieb | Debian, Stirling PDF als JAR (ohne Docker) |
| Dienst | `stirlingpdf.service` (Benutzer/Gruppe: `stirling`) |
| SMB-Eingang | `/srv/samba-shares/Scan-Eingang` |
| SMB-Ausgang | `/srv/samba-shares/Scan-Ausgang` |
| Grafische Automatisierung | `Test`: Ordnerquelle → `OCR & Scans bereinigen` → Ausgabeordner |
| Legacy-Watcher | `/opt/Stirling-PDF/pipeline/watchedFolders` (separater Mechanismus) |

Die SMB-Freigaben sind lokale Verzeichnisse auf dem Server `scanner`, welche per Samba im Netzwerk angeboten werden. Daher verwendet die Ordnerautomatisierung **lokale Dateipfade**.

### Zugriffsrechte nachweisen

Auf dem Server wurden diese Befehle **erfolgreich** ausgeführt:

```bash
sudo -u stirling ls -la /srv/samba-shares/Scan-Eingang
sudo -u stirling ls -la /srv/samba-shares/Scan-Ausgang
sudo -u stirling touch /srv/samba-shares/Scan-Eingang/test-stirling.txt
sudo -u stirling touch /srv/samba-shares/Scan-Ausgang/test-stirling.txt
sudo -u stirling rm -f /srv/samba-shares/Scan-Eingang/test-stirling.txt
sudo -u stirling rm -f /srv/samba-shares/Scan-Ausgang/test-stirling.txt
```

Die Ordner gehören `markus:markus` und besitzen Gruppenrechte; der Benutzer `stirling` kann nachweislich Dateien lesen und erstellen. **Nicht pauschal mit `chmod 777` lösen**; für dauerhaft getrennte Benutzerrechte sind Gruppen oder ACLs vorzuziehen. Vor weiteren Änderungen `id stirling` und `getfacl` prüfen. `SupplementaryGroups=` in `systemctl show` allein beweist nicht, dass der Linux-Benutzer keine ergänzenden Gruppen hat.

### Berechtigung der grafischen Automatisierung

Zuvor gab es in den Service-Logs folgenden Fehler:

```text
PolicyRunner - Failed to resolve source 'folder' for policy ... (Test): /srv/samba-shares/Scan-Eingang
```

Als Abhilfe wurde in der zuvor leeren `/opt/Stirling-PDF/configs/custom_settings.yml` die Pfadfreigabe konfiguriert:

```yaml
policies:
  allowedFolderRoots:
    - /srv/samba-shares/Scan-Eingang
    - /srv/samba-shares/Scan-Ausgang
```

Daraufhin Stirling PDF neu starten:

```bash
sudo systemctl restart stirlingpdf.service
sudo systemctl status stirlingpdf.service --no-pager
```

Der Anwender meldete danach, dass die Verarbeitung **scheinbar funktioniert**. Die bestätigten Logeinträge vor der Konfigurationsänderung zeigten bereits den Start der Policy `Test`, beweisen aber noch keinen erfolgreichen Abschluss. Deshalb Ergebnisdatei und OCR-Qualität getrennt prüfen.

### Legacy-Pipeline nicht mit der grafischen Automatisierung verwechseln

Die wiederkehrende Warnung

```text
PipelineDirectoryProcessor - No .JSON settings file found. No processing will happen for dir /opt/Stirling-PDF/pipeline/watchedFolders/Scan-Eingang
```

betrifft die **alte dateibasierte Pipeline**. Sie ist nicht gleichbedeutend mit einem Fehler in der grafischen Automatisierung `Test`. Keine JSON-Datei nur wegen dieser Warnung erstellen, solange ausschließlich die grafische Ordnerautomatisierung genutzt wird. Pro Eingangsordner nicht versehentlich zwei konkurrierende Verarbeitungsmechanismen aktivieren.

### Diagnose bei erneutem Problem

```bash
sudo systemctl status stirlingpdf.service --no-pager
sudo journalctl -u stirlingpdf.service --since "10 minutes ago" --no-pager | grep -Ei 'PolicyRunner|Failed to resolve|folder|denied|ERROR'
sudo -u stirling ls -la /srv/samba-shares/Scan-Eingang
sudo -u stirling ls -la /srv/samba-shares/Scan-Ausgang
```

Bei Bedarf die Automatisierung `Test` in der Weboberfläche speichern und mit einer neuen Test-PDF ausführen. Prüfen, ob im Ausgang wirklich eine fertig bearbeitete Datei entsteht und ob die OCR durchsuchbar ist.

## 7. Geplante Verarbeitungsprofile

| Eingang | Ziel |
| --- | --- |
| Scan-Standard | OCR Deutsch, Ausrichtung, Deskew, Leerseitenprüfung |
| Scan-QR | QR-Trennblätter; eigene QR-Inhalte noch testen |
| Scan-OCR | Nur Texterkennung |
| Scan-Optimierung | PDF-Komprimierung |
| Scan-Ausgang | Ergebnisablage über lokalen Ordner/Samba |

## 8. Native QR-Trennung: erfolgreicher Test und Produktivbetrieb (12.10.2026)

Die selbst entwickelte GUI-Erweiterung für den offiziellen Stirling-PDF-Quellstand `v3.1.0` wurde isoliert gebaut, anschließend mit vollständigem Frontend korrigiert und am 12.10.2026 erfolgreich auf Port `8080` produktiv getestet.

- Quellcheckout: `/home/markus/stirling-qr-gui-src`
- Patch im Projekt: `patches/apply-qr-gui-v3.1.0.py`; Vorbereitung über `patches/prepare-qr-gui.sh`
- Test-JAR: `/home/markus/stirling-qr-gui-src/app/core/build/libs/stirling-pdf-3.1.0.jar`
- Separate Testinstanz: `/home/markus/stirling-qr-test`, gebunden an `127.0.0.1:8081` (Browserzugriff per SSH-Portweiterleitung als `http://localhost:8081`)
- Starten im Testverzeichnis mit separatem temporären Verzeichnis und ohne Anmeldung **nur auf Loopback**:

```bash
cd ~/stirling-qr-test
mkdir -p tmp
java -Djava.io.tmpdir="$HOME/stirling-qr-test/tmp" \
  -jar "$HOME/stirling-qr-gui-src/app/core/build/libs/stirling-pdf-3.1.0.jar" \
  --server.port=8081 --server.address=127.0.0.1 --security.enableLogin=false
```

**Nachgewiesener manueller Test:** 10-seitige PDF, QR-Wert `SCAN:TEST` auf den Originalseiten 2, 5 und 7; in der GUI „Nach Seitenteiler“, „Exakter Inhalt“, `SCAN:TEST`, „QR-Code-Seite behalten“ aktiviert, Duplex deaktiviert. Vier PDFs erstellt: Originalseiten **1**, **2–4**, **5–6**, **7–10**. Der Nutzer bestätigte das Ergebnis per Screenshot; QR-Codes sind in den geteilten Dateien sichtbar.

**Login-/Split-Fehler behoben:** Der zunächst verwendete Build mit `-PfrontendMode=core -PbuildWithPortal=false` zeigte bei aktivierter Anmeldung weder die korrekte Login-Seite noch eine zuverlässig nutzbare Split-Oberfläche (401-Weiterleitungen). Mit `-PfrontendMode=proprietary -PbuildWithPortal=true` funktionieren Anmeldung und Split sowohl isoliert auf Port `8082` als auch produktiv auf `8080` (Anwenderbestätigung). Der vollständige Frontend-Build benötigt den externen `task`-Befehl von go-task.

**Noch nicht geprüft:** QR-Erkennung bei echten Scans, gedrehten und schiefen Seiten, schlechten Druckvorlagen, Duplexbetrieb, leeren Seiten und anderen QR-Inhalten; Integration in die automatische Ordnerverarbeitung und umfassende Regressionstests. Der manuelle produktive QR-Test ersetzt keinen End-to-End-Test des Processors.

### Build der produktiven Erweiterung

```bash
cd ~/stirling-qr-gui-src
./gradlew :stirling-pdf:bootJar \\
  -PbuildWithFrontend=true \\
  -PfrontendMode=proprietary \\
  -PbuildWithPortal=true \\
  --rerun-tasks \\
  --no-daemon
```

Artefakt: `app/core/build/libs/stirling-pdf-3.1.0.jar`. Vor produktiven Änderungen auf der isolierten Instanz unter `/opt/Stirling-PDF-qr-test-isolated` (Port `127.0.0.1:8082`) mit Anmeldung testen. Die Original-JAR wurde unter `/root/stirling-backup/Stirling-PDF-with-login.jar` gesichert; die Sicherungen der produktiven Konfiguration und Datenbank sind separat zu behandeln.

**Produktiver Abnahmetest am 12.10.2026:** QR-Wert `SCAN:TEST` auf Originalseiten 2, 5 und 7; QR-Seiten behalten, Duplex aus. Vier Ergebnisse mit 1, 3, 2 und 4 Seiten; Screenshot vom Anwender bestätigt. Weitere Einzelheiten und offene Tests stehen in [NEUER-CHAT.md](NEUER-CHAT.md).

## 9. Noch offen

- [x] Eigene Samba-Verwaltung verwenden; kein Webmin für die Stirling-PDF-Einrichtung erforderlich
- [x] SMB-Ordner `Scan-Eingang` und `Scan-Ausgang` erstellen und lokale Dateirechte für `stirling` testen (11.10.2026)
- [ ] Vier ursprünglich geplante Eingangsquellen und Profile ggf. später konfigurieren
- [ ] Erfolgreichen End-to-End-Lauf von `Test` (inkl. Ausgabedatei, OCR und Originaldatei-Verhalten) dokumentieren
- [x] Native QR-Code-Trennung mit digitaler Test-PDF auf Testinstanz prüfen (12.10.2026; vier korrekt getrennte PDFs)
- [ ] QR-Code-Trennung mit echten gescannten Seiten und in der Automatisierung prüfen
- [x] Navigationsproblem und Login-Fehler durch vollständigen Frontend-/Portal-Build beheben (12.10.2026)
- [x] Produktive JAR mit Login und QR-Trennung auf Port `8080` umstellen; Anwender bestätigte erfolgreichen Test (12.10.2026)
- [ ] Erst nach erfolgreichem Test ScanPro abschalten
- [ ] Backup: `/opt/Stirling-PDF/configs`, Pipeline-Dateien, `.env`, systemd-Service, Samba-Konfiguration

## Quellen

- [Stirling PDF – Dokumentation](https://docs.stirlingpdf.com/)
- [Processor – Integrations](https://docs.stirlingpdf.com/Processor/Integrations/)
- [Processor – Sources](https://docs.stirlingpdf.com/Processor/Sources/)
- [Stirling PDF – Projekt](https://github.com/Stirling-Tools/Stirling-PDF)
