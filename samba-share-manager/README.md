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

## Neue Oberfläche und Freigabezugänge (12.10.2026)

- Optik im Stil der Stirling-PDF-Processor-Oberfläche; Verwaltungsoberfläche standardmäßig unter **http://SERVER-IP:8085/**.
- Pro Freigabe dedizierter **Samba-Benutzer** mit Präfix `share_` und eigenem Passwort (mindestens 12 Zeichen); Zugangsdaten können nach Erstellen oder bei einer bestehenden Freigabe in der GUI gesetzt/geändert werden.
- In der Freigabenübersicht wird der **Benutzername und Passwortstatus**, niemals das Passwort selbst angezeigt. Samba speichert lediglich den dafür vorgesehenen Kennwort-Hash; Klartext kann nicht zurückgelesen werden.
- Neuer Freigabetyp **Paperless Consume (Ausgang)** mit Ziel `/srv/samba-shares/Paperless-Consume`. Der Paperless-Host muss diese Freigabe explizit in sein Consume-Verzeichnis mounten oder synchronisieren. Die Freigabe allein verbindet Paperless nicht automatisch.
- Bestehende SMB-Freigaben werden beim GUI-Update nicht überschrieben.

Auf einem bereits installierten System **ohne erneute Passwortvergabe für GUI-admin** aktualisieren:

```bash
cd /root/Stirling
git pull
bash scripts/update-samba-ui.sh
```

Auf einer Neuinstallation wird die aktuelle Oberfläche automatisch mit `bash install.sh --fresh` installiert.

**Sicherheitsregeln:** Pro Freigabe ein eigenes `share_`-Konto, GUI nur in einem kontrollierten LAN oder per HTTPS und Zugangsschutz. Keine SMB-Passwörter in Git, Konfigurationsdateien oder Logs schreiben.

**Teststatus:** Änderungen sind im Repository hinterlegt; noch kein vollständiger Integrationstest auf Debian 13 durchgeführt.

## Passwortanzeige mit Augensymbol

Bei bereits angemeldeten GUI-Administratoren zeigt die Schaltfläche **„◉ Passwort anzeigen“** das SMB-Passwort der ausgewählten Freigabe **ohne zweite Admin-Abfrage** an. Das Passwort ist nur in dieser Antwortansicht sichtbar; nach einem erneuten Laden wieder verdeckt. Neue SMB-Passwörter werden bei ihrer Vergabe zusätzlich verschlüsselt in `/etc/samba-share-manager/passwords.json` gesichert. Der lokale Schlüssel liegt in `/etc/samba-share-manager/vault.key`; beide Dateien haben Modus `0600` und sind nur für root lesbar. Der Share Manager nutzt dafür `python3-cryptography`.

**Bestehende SMB-Passwörter kann Samba nicht zurückliefern.** Daher bei bereits vorhandenen Freigaben das Passwort einmal über „Zugang speichern“ neu vergeben. Die Anmeldung an der Weboberfläche muss geschützt erfolgen (HTTPS über vertrauenswürdigen Reverse Proxy oder nur kontrolliertes LAN). Administratoren der GUI können die SMB-Passwörter jetzt einsehen; den Zugriff entsprechend beschränken.

## SMB-Benutzernamen (verbindliche Programmregel)

Beim Anlegen und Bearbeiten dürfen SMB-Benutzernamen frei gewählt werden, z. B. `TestSamba`, `scanner01` oder `share_scan`. Kein festes Präfix erforderlich. Zulässig sind **3 bis 31 Zeichen**, der erste muss ein Buchstabe sein; danach sind Groß- und Kleinbuchstaben, Ziffern, Unterstrich und Bindestrich erlaubt. Das GUI prüft dies im Formular, der privilegierte Helper prüft dieselbe Regel serverseitig. Bereits anderweitig vergebene Linux-Konten werden aus Sicherheitsgründen nicht ungeprüft übernommen oder überschrieben. Bestehende Freigaben bleiben erhalten.

## Automatische Stirling-Dateirechte (13.10.2026)

Neue, vom Samba-Manager angelegte Freigaben erhalten automatisch eine POSIX-ACL für den Dienstbenutzer `stirling` auf dem Freigabe-Verzeichnis (`u:stirling:rwx`) sowie eine Default-ACL (`d:u:stirling:rwx`) für neue Unterordner/Dateien. Eigentümer und bestehende Dateien werden nicht geändert. Die GUI bietet unter **Vorhandene Freigaben → Stirling-Zugriffsrechte setzen** dieselbe Aktion nachträglich für bestehende Shares. Beim Pfadwechsel werden die Rechte am neuen Zielordner vergeben. Voraussetzung ist `acl` / `setfacl` auf dem Server.

**Getrennte Freigabe in Stirling:** ACL-Rechte allein erlauben noch keine Ordnerautomatisierung. Zusätzlich muss `/srv/samba-shares` in den Stirling-Einstellungen als zulässiges Stammverzeichnis konfiguriert werden. Für bereits bestehende Dateien (vor der ACL-Änderung) werden keine rekursiven Änderungen vorgenommen.

## Ein SMB-Benutzer für mehrere Freigaben (13.10.2026)

Der Samba-Share-Manager erlaubt jetzt die **Wiederverwendung eines bereits vom Manager verwalteten SMB-Benutzers** für mehrere Freigaben. Beim Erstellen einer weiteren Freigabe denselben Benutzernamen und dasselbe vorhandene Passwort eingeben. Die Benutzeranlage wird dabei übersprungen; der bisherige Samba-Benutzer bleibt bestehen, und das vorhandene Samba-Passwort wird beim Anlegen einer weiteren Freigabe **nicht geändert**. Stimmt das Passwort nicht überein, erscheint eine Fehlermeldung.

Bei Änderung des Passworts für einen mehrfach verwendeten Benutzer wird dieses eine Samba-Passwort aktualisiert und die verschlüsselte Passwortanzeige aller Freigaben mit diesem Benutzer synchronisiert. Das Ändern des Benutzernamens einer Freigabe auf einen vorhandenen Manager-Benutzer ist möglich; das Passwort kann dann leer bleiben und wird übernommen. Fremde Linux-/Samba-Konten ohne zugehörige Manager-Freigabe werden weiterhin nicht übernommen.

**Windows:** Freigaben auf derselben Server-IP müssen mit denselben SMB-Zugangsdaten verbunden werden, z. B. `\\\\192.168.0.54\\Scan-Eingang1` auf `W:` und `\\\\192.168.0.54\\Scan-Ausgang` auf `X:`. Bestehende Windows-Verbindungen mit abweichenden Zugangsdaten ggf. zuvor gezielt trennen.

Die Funktion ist im Repository implementiert; Live-Test auf dem Server steht noch aus.

## Erstanmeldung an der Samba-Weboberfläche (Stand 13.10.2026)

Bei einer **frischen Installation** erstellt das Setup ein **Startpasswort `admin123`** für den Webadministrator `admin` und zeigt es **einmal im Terminal** an. Beim ersten Login unter `http://SERVER-IP:8085` wird ausschließlich die Seite zur Passwortänderung freigeschaltet. Das neue Administratorpasswort muss mindestens **12 Zeichen** lang sein. Erst danach kann die Freigabenverwaltung genutzt werden.

Aus Sicherheitsgründen wird kein allgemein bekanntes festes Startpasswort ausgeliefert. Bei Updates bleiben bereits bestehende Zugangsdaten unverändert; eine Neuinstallation darf bestehende Anmeldedaten nicht überschreiben. Das Samba-GUI-Passwort ist unabhängig von den SMB-Passwörtern für Windows-Netzlaufwerke. Die Oberfläche nur im vertrauenswürdigen LAN oder hinter TLS betreiben.


## GUI-Startpasswort (13.10.2026)

Bei einer **neuen** Samba-Share-Manager-Installation ist der Webzugang zunächst **Benutzer `admin` / Passwort `admin123`**. Beim ersten Login ist die Vergabe eines individuellen neuen Passworts mit **mindestens 12 Zeichen** verpflichtend; bis dahin bleibt die Verwaltung gesperrt. Bestehende Passwortdateien werden beim Installieren nicht überschrieben. **Achtung:** Das bekannte Startpasswort ist unsicher; bis zur Änderung den Zugriff auf Port 8085 auf ein vertrauenswürdiges Administrationsnetz beschränken und keinesfalls öffentlich anbieten.
