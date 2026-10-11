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

## QR-GUI-Erweiterung: Teststand 12.10.2026

Die native QR-Code-Funktion wurde im **separaten Testsystem** auf Stirling PDF v3.1.0 erfolgreich erstellt und manuell getestet.

- GitHub-Patch: `patches/apply-qr-gui-v3.1.0.py` und `patches/prepare-qr-gui.sh`
- Lokal geändertes offizielles Source-Checkout: `~/stirling-qr-gui-src`; **nicht** erneut `prepare-qr-gui.sh` auf das bereits geänderte Checkout anwenden
- Gebautes JAR: `~/stirling-qr-gui-src/app/core/build/libs/stirling-pdf-3.1.0.jar`
- Isoliertes Testverzeichnis `~/stirling-qr-test`; Start auf `127.0.0.1:8081`, Zugriff im Browser per SSH-Tunnel `http://localhost:8081/split`
- Für die Testinstanz: `-Djava.io.tmpdir="$HOME/stirling-qr-test/tmp"` sowie `--security.enableLogin=false`, nur mit `--server.address=127.0.0.1`
- `curl` für `/split` und `/api/v1/config/endpoints-availability` ergab zuletzt jeweils HTTP 200, nachdem die Testinstanz wieder lief.
- Test: Zehnseitige PDF mit QR-Inhalt `SCAN:TEST` auf den Seiten 2, 5 und 7. Einstellung **Exakter Inhalt**, **SCAN:TEST**, **QR-Code-Seite behalten an**, **Duplex aus**. Vier PDFs mit Seiten **1**, **2–4**, **5–6**, **7–10** wurden erzeugt. Screenshot bestätigt QR-Seiten in den Ausgaben.
- Ein zeitweise nur kurz angezeigtes „Aufteilen“-Untermenü ist noch nicht als Navigationsbug eingegrenzt; direkter Werkzeugaufruf `/split` funktioniert nach Serverneustart.
- **Produktive Instanz auf 8080 blieb unverändert.** Keine Inbetriebnahme ohne Tests mit echten Scans und Rollback.

## Nächste Aufgaben
1. Mit frischer Test-PDF bestätigen: Eingang aufgenommen, OCR erfolgt, Datei im Ausgang, inhaltlich durchsuchbar.
2. Originaldatei-Verhalten der Automatisierung klären.
3. Ordnerzugriff/ACL-Vererbung und Samba-Konfiguration dokumentieren, damit Rechte für neue Dateien zuverlässig bleiben.
4. Native QR-Trennung mit echten Scanner-PDFs (schief, gedreht, unscharf), weiteren QR-Inhalten und dem Processor testen.
5. Alte nicht genutzte Watched-Folder-Struktur erst nach Prüfung bereinigen; keine produktiven Dateien löschen.
6. Backup der Konfiguration, Samba-Konfiguration und systemd-Service.\n7. Navigation/Untermenü unter Testbedingungen prüfen, dann Deploy- und Rollback-Plan erstellen.

Weitere Installationsdetails: [README.md](README.md).
