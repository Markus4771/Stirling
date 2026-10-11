# Stirling PDF – Installation und Scanserver

Dokumentation für den Server `scanner` auf **Debian 13.7**, ohne Docker. Dieses Repository dokumentiert die Installation von Stirling PDF als geplanten Ersatz für ScanPro; es enthält nicht die Stirling-PDF-Quellsoftware.

## Bestätigter Ist-Stand (11.10.2026)

- OpenJDK 25.0.4.1
- Stirling PDF unter `/opt/Stirling-PDF`
- systemd-Dienst `stirlingpdf` läuft und startet automatisch
- Weboberfläche funktioniert auf `http://SERVER-IP:8080`
- Samba-Freigaben `Scan-Eingang` und `Scan-Ausgang` sind vorhanden; lokale Lese- und Schreibtests als Benutzer `stirling` waren erfolgreich.
- Grafische Automatisierung `Test`: Scan-Eingang → OCR & Scans bereinigen → Scan-Ausgang; nach Konfigurationsanpassung meldet der Anwender, dass es scheinbar funktioniert. Ein nachgewiesener End-to-End-Test der resultierenden PDF steht noch aus.

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

### B. Scan-Geräte sollen auf dem Debian-Server direkt in SMB-Freigaben schreiben

Dann wird **Samba auf Debian** benötigt. Vorgesehene Ordner:

```bash
sudo apt install -y samba smbclient
sudo mkdir -p /opt/Stirling-PDF/pipeline/watchedFolders/{Standard,QR-Code,OCR,Optimierung}
sudo mkdir -p /opt/Stirling-PDF/pipeline/finishedFolders/{Standard,QR-Code,OCR,Optimierung}
sudo chown -R stirling:stirling /opt/Stirling-PDF/pipeline
sudo smbpasswd -a markus
sudo cp /etc/samba/smb.conf /etc/samba/smb.conf.bak
```

Die passenden Samba-Abschnitte mit `valid users = markus`, `force user = stirling` und einem jeweiligen `path` zu den Eingangsordnern müssen in `/etc/samba/smb.conf` ergänzt werden. Für den Ausgang auf `/opt/Stirling-PDF/pipeline/finishedFolders` verweisen. Anschließend:

```bash
sudo testparm -s
sudo systemctl restart smbd
smbclient -L localhost -U markus
```

Geplante Freigaben: `Scan-Standard`, `Scan-QR`, `Scan-OCR`, `Scan-Optimierung`, `Scan-Ausgang`. Eingangs- und Ausgangsordner voneinander trennen und Pipeline-Konfigurationen vor unberechtigtem SMB-Zugriff schützen. Der lokale Folder-Scanning-Mechanismus und der neuere Processor sind **verschiedene** Automatisierungswege; vor dem Produktivbetrieb pro Eingang genau einen festlegen.

## 5. Webmin zur Verwaltung der Samba-Freigaben

**Stand 10.10.2026:** Webmin wurde auf dem Debian-Server `scanner` installiert und seine Weboberfläche funktioniert. Der Webmin-Dienst läuft auf Port 10000; lokaler HTTPS-Test lieferte HTTP 200.

### Installation ohne Docker

```bash
sudo apt update
sudo apt install -y curl ca-certificates gnupg
cd /tmp
curl -fsSLO https://raw.githubusercontent.com/webmin/webmin/master/webmin-setup-repo.sh
less webmin-setup-repo.sh  # Skript vor Ausführung prüfen
sudo sh webmin-setup-repo.sh
# Beim Dialog das stabile Repository mit y bestätigen
sudo apt update
sudo apt install -y webmin
```

Weboberfläche: `https://SERVER-IP:10000`. Ein selbstsigniertes Zertifikat kann eine Browserwarnung verursachen; die Identität des Servers prüfen. Zugriff nur aus vertrauenswürdigem LAN bzw. VPN gestatten.

### Prüfung und Fehlersuche

```bash
sudo systemctl status webmin --no-pager
sudo ss -tlnp | grep 10000
curl -kI https://127.0.0.1:10000
hostname -I
```

Auf dem vorhandenen Server bestätigten die Tests: `active (running)`, Listener auf `0.0.0.0:10000` und `[::]:10000` sowie `HTTP/1.0 200 Document follows`. Falls der Browser trotzdem nicht lädt: `https://SERVER-IP:10000` nutzen, ggf. Client-Netzwerk und Firewall prüfen. Ein früherer PAM-Fehler für `root` ist ein Login-Thema, nicht der Beleg für einen ausgefallenen Webserver.

### Samba über Webmin verwalten

1. In Webmin **Servers → Samba Windows File Sharing** öffnen.
2. Falls nötig Samba installieren: `sudo apt install -y samba smbclient`.
3. Für jeden Eingang eine neue SMB-Freigabe mit dem jeweiligen absoluten Verzeichnispfad anlegen (siehe Abschnitt 4B).
4. Gastzugriff ausschalten, erlaubte Benutzer eingrenzen und Zugriffsrechte für den Verarbeitungsbenutzer `stirling` setzen.
5. Konfiguration mit `sudo testparm -s` prüfen, `smbd` neu starten und die Freigaben mit `smbclient -L localhost -U markus` testen.

**Aktueller Stand (11.10.2026):** Die Freigaben `Scan-Eingang` und `Scan-Ausgang` unter `/srv/samba-shares/` sind eingerichtet. Lese- und Schreibzugriff als lokaler Benutzer `stirling` wurde geprüft. Die oben genannten fünf Freigaben sind ein ursprünglicher Plan, nicht der derzeitige Ist-Zustand. Webmin verwaltet Samba; Stirling PDF übernimmt die Verarbeitung.

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

## 8. Noch offen

- [x] Webmin installieren und Weboberfläche testen (10.10.2026)
- [x] SMB-Ordner `Scan-Eingang` und `Scan-Ausgang` erstellen und lokale Dateirechte für `stirling` testen (11.10.2026)
- [ ] Vier ursprünglich geplante Eingangsquellen und Profile ggf. später konfigurieren
- [ ] Erfolgreichen End-to-End-Lauf von `Test` (inkl. Ausgabedatei, OCR und Originaldatei-Verhalten) dokumentieren
- [ ] QR-Code-Trennung praktisch prüfen
- [ ] Erst nach erfolgreichem Test ScanPro abschalten
- [ ] Backup: `/opt/Stirling-PDF/configs`, Pipeline-Dateien, `.env`, systemd-Service, Samba-Konfiguration

## Quellen

- [Stirling PDF – Dokumentation](https://docs.stirlingpdf.com/)
- [Processor – Integrations](https://docs.stirlingpdf.com/Processor/Integrations/)
- [Processor – Sources](https://docs.stirlingpdf.com/Processor/Sources/)
- [Stirling PDF – Projekt](https://github.com/Stirling-Tools/Stirling-PDF)
