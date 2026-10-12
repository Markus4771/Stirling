# Pilot: automatische QR-Trennung mit OCR – Stirling PDF 3.1.0

Stand: 12.10.2026. **Entwurf / noch nicht aktiviert.**

## Ausgangslage
Produktive Instanz `scanner` (Port 8080) mit funktionierendem Login, manuellem Split und erweitertem QR-Abgleich (`qrMode=exact`, `qrValue=SCAN:TEST`, `keepQrPage=true`, `duplexMode=false`). Manueller Funktionstest mit zehn Seiten erfolgreich: 1 / 2–4 / 5–6 / 7–10.

Bestehende grafische Processor-Automatisierung **Test**: `/srv/samba-shares/Scan-Eingang` → OCR → `/srv/samba-shares/Scan-Ausgang`. **Nicht umstellen und nicht denselben Eingangsordner mit einem zweiten Watcher überwachen.**

## Ziel
Separate kontrollierte Verarbeitung:
`/srv/samba-shares/Scan-QR-Eingang` → QR-Trennung → OCR pro Ergebnis-PDF → `/srv/samba-shares/Scan-QR-Ausgang`.

## Sicherheit und Voraussetzungen
1. Neue Ordner nur nach expliziter Einrichtung mit passendem Eigentümer, Samba-Berechtigungen und Aufnahme beider Pfade in `policies.allowedFolderRoots` der produktiven `configs/custom_settings.yml`.
2. Keine Jobs aktivieren, bevor die vorhandene Automatisierung `Test` unberührt bleibt, keine Endlosschleifen möglich sind und ein konsistentes Backup besteht.
3. Trennen liefert **mehrere PDFs** bzw. eine ZIP-Ausgabe, je nach API/Workflow-Kontext. **Nicht nachgewiesen**, ob der Processor `Split / Page Divider` als Schritt anbietet oder einen Multi-Output-Schritt an OCR und Ordnerziel weiterreichen kann. Nicht von der funktionierenden Editor-UI auf Processor-Kompatibilität schließen.

## Erstes UI-Prüfverfahren (nicht destruktiv)
1. Produktivoberfläche auf Port 8080 öffnen, anmelden.
2. **Processor → Pipelines → Neue benutzerdefinierte Pipeline** öffnen; vorerst **ohne Speichern/Aktivieren**.
3. `Add a tool` öffnen und prüfen, ob **Split / Aufteilen** verfügbar ist, insbesondere Methode **Nach Seitenteiler** einschließlich der Felder `qrMode` / `qrValue` / `keepQrPage`.
4. Falls vorhanden: Prüfen, ob nach diesem Schritt **OCR** hinzugefügt werden kann und ein **Folder**-Ziel auswählbar ist. Die Verfügbarkeit allein beweist noch nicht, dass vier Ergebnis-PDFs durchgereicht werden.
5. Falls Tool, Parameter oder Multi-Output-Unterstützung fehlen: keine Live-Pipeline aktivieren. Alternative ist eine getrennte lokale Staging-Verarbeitung mit Authentifizierung und kontrollierter ZIP-Entpackung oder eine gezielte Erweiterung des Processor-Backends – getrennt entwickeln und testen.

## Geplanter Abnahmetest
- Test-PDF `SCAN:TEST` auf Originalseiten 2, 5 und 7, QR-Seiten behalten, Duplex aus.
- Mit „Test with a file“ testen (dieser Test schreibt laut Dokumentation **nicht** ins konfigurierte Storage-Ziel).
- Vier Ergebnis-PDFs mit Seitenverteilung `1,3,2,4`.
- Danach durchsuchbaren OCR-Text in **allen vier** Ausgaben nachweisen.
- Erst anschließend einen einzelnen kontrollierten Live-Input in den **separaten** QR-Ordner geben und Ausgabe, Originaldatei-Verhalten, Fehler-/Dublettenbehandlung prüfen.

## Quellstellen
- https://docs.stirlingpdf.com/Processor/Pipelines/
- https://docs.stirlingpdf.com/Processor/Sources/
- https://docs.stirlingpdf.com/Configuration/Automation/Pipeline/
- https://docs.stirlingpdf.com/Tools/Guides/Page-Operations/

## Aktueller Status
**Noch nicht umgesetzt:** Es besteht aus dieser Sitzung kein direkter Zugriff auf die laufende Processor-Konfiguration. Zunächst ist die UI-Verfügbarkeit der QR-Split-Operation und die Multi-Output-Verarbeitung zu prüfen. In GitHub wurde nur dieser sichere Pilotplan hinterlegt.
