# QR-Trennung ohne Trennblatt

Für den Debian-Scanserver mit Stirling PDF als JAR. **Nur QR-Codes mit Präfix `SCAN:`** starten ein neues Dokument. Ein QR-Code auf der ersten Seite wird als Beginn des Dokuments erkannt. Die QR-Seite bleibt erhalten. QR-Inhalte werden als bereinigter Teil des Dateinamens verwendet.

## Beispiel

QR auf Seite 1: `SCAN:Rechnung-4711`, Seiten 2–3 ohne QR, Seite 4 mit `SCAN:Rechnung-4712`, Seite 5 ohne QR. Ergebnis: zwei PDF-Dateien (Seiten 1–3 und 4–5). Vorlaufseiten ohne passendes QR werden separat als `Ohne_QR` ausgegeben. PDF-Dateien ganz ohne passenden QR bleiben im Quellordner und werden nicht automatisch an Stirling übergeben.

## Ablauf

Scanner → **separate** Samba-Freigabe `Scan-QR` (`/srv/samba-shares/Scan-QR`) → Python-Splitter → bestehender `/srv/samba-shares/Scan-Eingang` → vorhandene grafische Stirling-Automatisierung (OCR, Scanbereinigung) → `/srv/samba-shares/Scan-Ausgang`.

Im Stirling-Automatisierungseditor für diesen Pfad **die Funktion „Aufteilen nach Seitenteiler“ entfernen**. Sie erwartet den speziellen Stirling-Trenncode und soll nicht zusätzlich auf die vom Python-Dienst bereits aufgeteilten PDFs angewendet werden.

## Installation (auf dem Server, noch NICHT automatisch über install.sh aktiviert)

```bash
git clone https://github.com/Markus4771/Stirling.git
cd Stirling/qr-splitter
sudo bash install-qr.sh
sudo -u stirling python3 /opt/Stirling-PDF/qr-splitter/qr_splitter.py --dry-run
sudo systemctl enable --now stirling-qr-splitter.timer
sudo journalctl -u stirling-qr-splitter.service -n 60 --no-pager
```

Danach im eigenen Samba-Verwaltungstool **Scan-QR** mit Pfad `/srv/samba-shares/Scan-QR` freigeben; SMB-Schreibrechte des Scanners und die ACL-Vererbung prüfen. Teste vor Produktivbetrieb mit einem Kopie-Teststapel.

## Betrieb und Sicherheit

- Standardpräfix: `SCAN:` (genauer Textabgleich, Groß-/Kleinschreibung beachten). Änderbar in der systemd-Service-Datei über `--prefix`.
- Die Eingangsdatei muss mindestens 30 Sekunden alt sein, damit noch laufende Scanner-Schreibvorgänge nicht erfasst werden. Für Netzwerkscanner mit langen Übertragungen ggf. anpassen.
- Originale werden nach der Ausgabe in `Scan-QR/_archiv` verschoben und nicht gelöscht.
- Ausgaben werden zunächst vollständig in einem temporären Ordner erzeugt; anschließend einzeln in den Stirling-Eingang übertragen. Bei Unterbrechung während des Transfers sind Teilausgaben möglich und müssen vor einem erneuten Lauf kontrolliert werden.
- Jede Seite bleibt erhalten; Sonderfall mehrere passende QR-Codes auf einer Seite führt zum Fehler statt stiller Trennung.
- Mit fehlendem oder nicht erkennbarem QR bleibt die Eingangsdatei zur manuellen Prüfung liegen.
- Dies ist eine erste Implementierung, **noch nicht auf deinem Server produktiv getestet**. Große oder beschädigte PDFs können Fehler verursachen.
- Die Installation führt keine Änderungen an der laufenden Automatisierung oder am vorhandenen Samba-Verwaltungstool durch.
- Bei abweichender Samba-`create mask` / ACL-Maske können geerbte Rechte eingeschränkt werden. Einen echten Upload per Scanner testen.
