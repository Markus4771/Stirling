# Stirling PDF – Installation und Scanserver

Dokumentation für den Server `scanner` auf **Debian 13.7**, ohne Docker. Dieses Repository dokumentiert die Installation von Stirling PDF als geplanten Ersatz für ScanPro; es enthält nicht die Stirling-PDF-Quellsoftware.

## Bestätigter Ist-Stand (10.10.2026)

- OpenJDK 25.0.4.1
- Stirling PDF unter `/opt/Stirling-PDF`
- systemd-Dienst `stirlingpdf` läuft und startet automatisch
- Weboberfläche funktioniert auf `http://SERVER-IP:8080`
- SMB-Eingänge, Verarbeitungsprofile und automatischer Ausgang müssen noch konfiguriert/getestet werden

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

## 5. Geplante Verarbeitungsprofile

| Eingang | Ziel |
| --- | --- |
| Scan-Standard | OCR Deutsch, Ausrichtung, Deskew, Leerseitenprüfung |
| Scan-QR | QR-Trennblätter; eigene QR-Inhalte noch testen |
| Scan-OCR | Nur Texterkennung |
| Scan-Optimierung | PDF-Komprimierung |
| Scan-Ausgang | Ergebnisablage über lokalen Ordner/Samba |

## 6. Noch offen

- [ ] SMB-Variante auswählen und einrichten
- [ ] Vier Eingangsquellen und Profile testen
- [ ] Scan-Ausgang und Originaldatei-Sicherung konfigurieren
- [ ] QR-Code-Trennung praktisch prüfen
- [ ] Erst nach erfolgreichem Test ScanPro abschalten
- [ ] Backup: `/opt/Stirling-PDF/configs`, Pipeline-Dateien, `.env`, systemd-Service, Samba-Konfiguration

## Quellen

- [Stirling PDF – Dokumentation](https://docs.stirlingpdf.com/)
- [Processor – Integrations](https://docs.stirlingpdf.com/Processor/Integrations/)
- [Processor – Sources](https://docs.stirlingpdf.com/Processor/Sources/)
- [Stirling PDF – Projekt](https://github.com/Stirling-Tools/Stirling-PDF)
