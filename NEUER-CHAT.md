# NEUER-CHAT – Stirling PDF Scanserver

Stand: 11.10.2026

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

## Nächste Aufgaben
1. Mit frischer Test-PDF bestätigen: Eingang aufgenommen, OCR erfolgt, Datei im Ausgang, inhaltlich durchsuchbar.
2. Originaldatei-Verhalten der Automatisierung klären.
3. Ordnerzugriff/ACL-Vererbung und Samba-Konfiguration dokumentieren, damit Rechte für neue Dateien zuverlässig bleiben.
4. Später QR-Code-Trennung und weitere Scanprofile testen.
5. Alte nicht genutzte Watched-Folder-Struktur erst nach Prüfung bereinigen; keine produktiven Dateien löschen.
6. Backup der Konfiguration, Samba-Konfiguration und systemd-Service.

Weitere Installationsdetails: [README.md](README.md).
