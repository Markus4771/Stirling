# Samba Share Manager

Eigenständige Weboberfläche für die Verwaltung zusätzlicher Samba-Freigaben auf dem Debian-Server `scanner`. Keine Abhängigkeit zu ScanPro oder Stirling PDF.

## Funktionen

- Neue Freigaben per Browser anlegen
- Vom Manager angelegte Freigaben anzeigen und entfernen
- Verzeichnisse unter `/srv/samba-shares/<Freigabename>` erzeugen
- Zugriffsbenutzer `markus`
- Samba-Konfiguration mit `testparm` prüfen und `smbd` neu laden
- Beim Entfernen einer Freigabe bleiben die Dateien erhalten

**Einschränkungen:** Vorhandene, außerhalb des Managers erstellte Freigaben (z. B. in Webmin) werden nicht angezeigt oder verändert. Die Verwaltung beliebiger Pfade und weiterer Benutzer ist noch nicht implementiert.

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
