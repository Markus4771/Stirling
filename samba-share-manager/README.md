# Samba Share Manager

Eigenständige Weboberfläche für die Verwaltung zusätzlicher Samba-Freigaben auf dem Debian-Server `scanner`. Keine Abhängigkeit zu ScanPro oder Stirling PDF.

## Funktionen

- Neue Freigaben per Browser anlegen
- Vom Manager angelegte Freigaben anzeigen und entfernen
- Verzeichnisse unter `/srv/samba-shares/<Freigabename>` erzeugen
- Stirling PDF Eingang: `/opt/Stirling-PDF/pipeline/watchedFolders/<Freigabename>`
- Stirling PDF Ausgang: `/opt/Stirling-PDF/pipeline/finishedFolders/<Freigabename>`
- Schreib- und Lesezugriff für verwaltete Freigaben ändern
- Zugriffsbenutzer `markus`
- Samba-Konfiguration mit `testparm` prüfen und `smbd` neu laden
- Beim Entfernen einer Freigabe bleiben die Dateien erhalten

**Einschränkungen:** Vorhandene, außerhalb des Managers erstellte Freigaben (z. B. in Webmin) werden nicht angezeigt oder verändert. Bestehende Freigaben können hinsichtlich Schreibzugriff, aber nicht Zielpfad oder Name bearbeitet werden. Beliebige Pfade und weitere Samba-Benutzer werden nicht angeboten.

## Installation auf Debian

Voraussetzungen: `samba`, `sudo`, `python3`, Linux- und Samba-Benutzer `markus`.

```bash
sudo apt update
sudo apt install -y samba smbclient sudo python3
git clone https://github.com/Markus4771/Stirling.git
cd Stirling/samba-share-manager
sudo bash install.sh
```

Im Installer ein eigenes Admin-Passwort mit mindestens zwölf Zeichen vergeben.

Aufruf: `http://SERVER-IP:8765/`, Benutzer: `admin`.

## Sicherheit

Die Benutzeroberfläche verwendet HTTP Basic Authentication. Ohne TLS werden Anmeldedaten im Netzwerk nicht verschlüsselt. Deshalb Port 8765 **ausschließlich in einem vertrauenswürdigen, kontrollierten LAN** verwenden; für Remote-Zugriff HTTPS über Reverse Proxy und zusätzliche Zugriffsbeschränkungen einrichten. **Nicht direkt ins Internet freigeben.**

Ein privilegierter Helper verwaltet ausschließlich die eigene Include-Datei `/etc/samba/share-manager.conf`. Das Installationsskript ergänzt hierzu `/etc/samba/smb.conf`. Vor der ersten Installation Samba-Konfiguration sichern und Installation prüfen.

## Dienst prüfen

```bash
sudo systemctl status samba-share-manager
sudo journalctl -u samba-share-manager -n 50 --no-pager
sudo testparm -s
```

## Bezug zu Stirling PDF

Der Share Manager ist unabhängig von der PDF-Verarbeitung. Eingangs- oder Ausgangsordner von Stirling PDF können später durch eine Erweiterung explizit auswählbar gemacht werden. Derzeit erzeugt er neue Freigaben nur unter `/srv/samba-shares`.


## Installation nach bestehender Stirling-PDF-Installation

```bash
sudo apt install -y samba smbclient sudo python3 git
sudo smbpasswd -a markus
cd ~/Stirling
git pull
cd samba-share-manager
sudo bash install.sh
```

Erforderlich sind der Linux-Benutzer `markus` sowie die bereits angelegten Pipeline-Verzeichnisse aus dem Stirling-PDF-Installer. Das Skript fragt ein neues Web-GUI-Passwort ab. Es ersetzt die bestehende GUI-Passwortdatei bei erneuter Ausführung und startet den Dienst neu.

Für ein neues Eingangs-Share den Typ **Stirling PDF Eingang** wählen. Ein Ausgabe-Share kann entsprechend als **Stirling PDF Ausgang** erzeugt werden. **Achtung:** Die Einrichtung der Freigaben allein aktiviert keine Stirling-Verarbeitungspipeline. Diese muss separat konfiguriert und getestet werden.

Nach dem Erstellen einer Freigabe:
```bash
sudo testparm -s
sudo smbclient -L localhost -U markus
sudo systemctl status samba-share-manager --no-pager
```

Die Verzeichnisse der Stirling-Pipelines verwenden intern den Systembenutzer `stirling` als SMB-Dateibesitzer; andere Manager-Shares den Benutzer `markus`. Vor produktivem Betrieb Zugriffsbeschränkungen, Netzwerk-Firewall und Schreib-/Leserechte testen.
