# E2E-Ergebnis vom 10.08.2026

| Suite | Ergebnis | Screenshots |
| --- | ---: | ---: |
| Landingpages und Admin-Survey-Seiten | 8/8 bestanden | 12 |
| Flow-Builder-Walkthrough | 15/15 bestanden | 15 |
| E-Mail-Vorlagen-Walkthrough | 10/10 bestanden | 10 |
| Visueller Smoke-Test aller Routen | 7/7 bestanden | 7 |
| Browser-Test ohne Builder-Telemetrie | 1/1 bestanden | 0 |
| Admin-/Partner-Paginierung | 2/2 bestanden | 2 |
| FIA-Partner-Step und Eventsteuerung | 1/1 bestanden | 3 |
| **Gesamt** | **44/44 bestanden** | **49** |

Die Screenshots wurden mit Playwright im Headless-Chromium als vollständige
Seitenaufnahmen (`full_page=True`) erzeugt. Testdaten und temporäre Änderungen
der Walkthroughs wurden nach den Läufen bereinigt.

## Ergänzung vom 16.08.2026

| Suite | Ergebnis | Screenshots |
| --- | ---: | ---: |
| Step-Editor: Referenzsuche, Multi-Select, Mapping und Pflichtangaben | 1/1 bestanden | 3 |

Der fokussierte Test speichert eine Mehrfachwert-Bedingung mit Redirect,
übernimmt ein Feld aus einem referenzierten Schritt und wählt Pflichtfelder
sowie Dokumenttypen über die neuen Suchlisten. Die gespeicherte Konfiguration
wurde anschließend über die Admin-API verifiziert; temporäre Schritte wurden
entfernt.

### Login und Passwort-Zurücksetzen

| Suite | Ergebnis | Screenshots |
| --- | ---: | ---: |
| Admin-Login über den realen Frontend-Proxy | 1/1 bestanden | 2 |
| Passwort-Reset bis zum Login mit neuem Passwort | 1/1 bestanden | 5 |

Diese Suite verwendet absichtlich kein Playwright-Routing für API-Aufrufe. Sie
prüft damit die echte Kette Browser → `localhost:3001/api` → CRACO-Proxy →
Backend. Temporäre Benutzer und Reset-Tokens werden nach dem Lauf entfernt.

### Visueller Survey-Form-Builder

| Suite | Ergebnis | Screenshots |
| --- | ---: | ---: |
| Builder: bestehende Felder, Inhaltsbausteine und Persistenz | 1/1 bestanden | 3 |
| Nutzeransicht: Rendering, Pflichtfelder und Mehrfachauswahl | 1/1 bestanden | 2 |

Die beiden fokussierten Tests verifizieren die gespeicherte Builder-Konfiguration
zusätzlich über die Admin-API. Der Nutzer-Test prüft außerdem HTML-Bereinigung,
Bild, zweispaltiges Layout, Textbereich, Datei-Attribute, Pflichtvalidierung und
Mehrfachauswahl. Temporäre Schritte und Benutzer werden nach jedem Lauf entfernt.

### Nutzergruppen und Einzelberechtigungen

| Suite | Ergebnis | Screenshots |
| --- | ---: | ---: |
| Gruppen-CRUD und Benutzer-Overrides im Adminbereich | 1/1 bestanden | 6 |
| Rechte-API, Rollen- und Auth-Regressionen | 83/83 bestanden | 0 |

Der Browser-Test läuft über den echten Frontend-Proxy und prüft das Anlegen,
Bearbeiten und Löschen einer Gruppe sowie Gruppen-Multi-Select und individuelle
Allow-/Deny-Overrides. Die API-Suite prüft zusätzlich Deny-Priorität,
unbekannte Rechte, Schutz vor Rechteausweitung, Systemgruppen und die sofortige
serverseitige Durchsetzung. Temporäre Benutzer und Gruppen werden bereinigt.
