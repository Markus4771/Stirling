# QR-Code-GUI für Stirling PDF – Entwicklungsstand

Stand: 11.10.2026

## Prototyp

Der erste Quellcode-Patch liegt unter [patches/qr-gui-v1.patch](../patches/qr-gui-v1.patch).

Er ergänzt das bestehende Werkzeug **Aufteilen nach Seitenteiler**:
- Offiziellen Stirling-PDF-Trenncode weiterhin erkennen.
- Alternatives QR-Präfix wie `SCAN:` auswählen.
- Optional einen exakten QR-Code-Inhalt angeben.
- Die QR-Code-Seite bei Bedarf behalten.
- Diese Auswahl als Werkzeugparameter einer Automatisierung weiterreichen.

## Einschränkungen / erforderliche nächste Entwicklung

**Noch nicht fertig gebaut oder installiert.** Der Patch wurde gegen den aktuellen öffentlich einsehbaren Quellcode vorbereitet, nicht gegen einen lokal ausgecheckten Build von **v3.1.0** getestet. Die Hunk-Positionen sowie API-Kompatibilität sind beim Anwenden gegen einen exakten Tag zu prüfen.

Insbesondere:
1. Die generierten Frontend-API-Typen (`toolApiTypes`) müssen nach Änderung des Backend-Anfragemodells regeneriert werden, sonst besteht ein TypeScript-Typfehler.
2. Der aktuelle QR-Decoder gibt bei mehreren QR-Codes auf einer Seite ggf. nur den ersten Treffer zurück. Für frei definierte Codes muss die Mehrfacherkennung verbessert werden.
3. Bestehende Einstellungen und Legacy-Automatisierungen müssen regressionstestet werden.
4. Einstellungen für Dateinamen aus QR-Code-Inhalten sind **noch nicht implementiert**.
5. Die Logik, QR-Seiten zu behalten, ist als erster Prototyp enthalten; korrekte Trennung am Dokumentanfang, bei Duplex und bei Mehrfachcodes muss getestet werden.
6. Frontend- und Backend-Build gegen Stirling PDF v3.1.0 erstellen und Integrationstest mit der 10-seitigen PDF durchführen.

## Erwarteter Test

Mit `qrMode=prefix`, `qrValue=SCAN:` und `keepQrPage=true` soll eine Test-PDF mit QR auf Seiten 2, 5 und 7 in vier Teile zerlegt werden: 1; 2–4; 5–6; 7–10.

## Wichtige Trennung zur vorhandenen Installation

- Die bestehende JAR auf `scanner` ist **unverändert**.
- Die schon bestehende separate Python-QR-Erweiterung unter `qr-splitter/` ist unabhängig vom geplanten nativen Stirling-PDF-Patch.
- Erst nach vollständigem Build und Test darf die bestehende JAR mit Backup ersetzt werden.
