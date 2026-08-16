# E2E-Screenshots

Die Playwright-End-to-End-Tests speichern hier automatisch vollständige
Seiten-Screenshots. Die Dateien sind nach Testsuite in Unterordnern gruppiert:

- `landing-pages/`
- `admin-survey-steps/`
- `flowbuilder/`
- `email-template-editor/`
- `auth-flows/`
- `form-builder/`
- `permissions/`

Der Ordner `admin-survey-steps/` enthält zusätzlich die fokussierten Ansichten
des Step-Editors für Bedingungen, Feld-Mappings und Pflichtangaben
(`11-...` bis `13-...`).

Der Ordner `auth-flows/` dokumentiert den ungemockten Admin-Login und den
vollständigen Passwort-Reset über den realen Frontend-Proxy (`/api`), inklusive
Login mit dem neu gesetzten Passwort.

Der Ordner `form-builder/` zeigt die Übernahme bestehender Felder, die visuelle
Konfiguration von HTML, Bild, Textbereich und Mehrfachauswahl sowie die daraus
gerenderte und validierte Nutzeransicht.

Der Ordner `permissions/` dokumentiert die Standardgruppen, das Anlegen und
Bearbeiten einer frei konfigurierten Nutzergruppe sowie gruppenbasierte und
individuelle Allow-/Deny-Rechte am Benutzer.

Bei einem erneuten Lauf werden gleichnamige Screenshots aktualisiert. Mit der
Umgebungsvariable `E2E_SCREENSHOT_DIR` kann ein anderer Ergebnisordner gewählt
werden.
