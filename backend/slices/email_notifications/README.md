# Email Templates & Notifications

Der Slice bündelt editierbare E-Mail- und Browser/App-Nachrichten, deren reine
Renderingregeln, Template-Persistenz und E-Mail-Zustellung.

Enthalten sind:

- unveränderliche, vollständig typisierte Template-, Rendering- und
  Zustellmodelle
- deterministische Variablenersetzung und HTML-/Notification-Rendering
- Empfängerbereinigung, Validierung und case-insensitive Deduplizierung
- kanonische Kategorien, Variablenkataloge und stabile Templatesortierung
- Ports für Template-Persistenz und E-Mail-Provider
- MongoDB-Repository mit idempotentem Startup-Seeding
- Service für Listen, Lesen, Bearbeiten, Zurücksetzen, Vorschau und Versand
- Pydantic-Modelle und HTTP-Fehlerabbildung für die Admin-API
- SMTP-Adapter unter `infrastructure/smtp_email_gateway.py`

Die Admin-Endpunkte und das Startup-Seeding delegieren an den Slice. Bestehende
Survey-, Partner- und Event-Aufrufer verwenden vorerst eine schmale
Kompatibilitätsfassade in `helpers.py`. Das persistente Domain-Event-System
bleibt bewusst ein eigenständiger, später zu extrahierender Slice.

Die bisherigen Defaultdefinitionen bleiben als importstabile Quelle bestehen;
`defaults.py` bildet sie an der Slice-Grenze in typisierte Modelle ab.

## Qualitätsprüfung

- 100 % Line- und Branch-Coverage für alle neuen Slice- und Adaptermodule
- striktes mypy für Slice und SMTP-Infrastruktur
- gezielte Mutationstests für die deterministische Domain und Modelle
- Regressionstests für Template-Administration, Partnerbenachrichtigungen und
  eventbasierte E-Mail-/Browser-Nachrichten
