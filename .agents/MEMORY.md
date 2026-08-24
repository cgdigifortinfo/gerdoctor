# GerDoctor – Arbeitskontext

Stand: 2026-08-24

## Repository und Git

- Repository: `/Users/christophergunther/apps/gerdoctor`
- Aktiver Branch: `main`
- Remote: `origin/main`
- Letzter fachlicher Commit vor diesem Memory-Abschluss: `cdec7ec`
- Die früheren Remote-Branches `pflege` und `Pflege` sowie der lokale Branch
  `local-pflege` wurden nach dem Fast-Forward-Merge gelöscht.
- Der Arbeitsbaum war vor dem Memory-Abschluss sauber und `main` vollständig
  mit GitHub synchron.

## Lokale Umgebung

- Docker Compose startet MongoDB, FastAPI und React.
- Frontend: `http://localhost:3001`
- Backend: `http://localhost:8001`
- MongoDB: `localhost:27017`
- Keine Zugangsdaten oder Stripe-Schlüssel in Memory-Dateien ergänzen.

## Aktuelle URL-Struktur

- `/` – Partner-Landingpage und Self-Service-Registrierung
- `/aerzte` – öffentlicher Ärzte-Survey
- `/pflege` – öffentlicher Pflege-Survey
- `/partner-payment` – isolierter Partner-Zahlungsprozess
- `/partner-payment/success` und `/partner-payment/cancelled` – Checkout-Rückkehrseiten
- `/partner/dashboard` – Partneradministration nach erfolgreicher Zahlung
- `/admin` – Plattformadministration

## Partnerregistrierung und Freischaltung

- Self-Service-Registrierung legt Partnerorganisation und Partnernutzer an.
- Ein neuer Partner startet mit `registration_status=pending`,
  `is_active=false` und ohne `survey_ids`.
- Nach erfolgreicher Stripe-Zahlung ist nur der bezahlte Zugang bestätigt; die
  fachliche Freischaltung erfolgt separat durch eine Admin-Survey-Zuweisung.
- Operativer Partnerzugriff setzt alle drei Bedingungen voraus:
  - `registration_status == active`
  - `is_active == true`
  - mindestens eine ID in `survey_ids`
- Solange die Zuweisung fehlt, zeigt das Partnerdashboard eine gestaltete
  Infoseite mit dem Hinweis auf Freischaltung innerhalb von zwei Werktagen.
- In diesem Zustand bleiben verfügbar:
  - eigenes Profil und eigene Partnerdaten
  - Rechnungs- und Stripe-Einstellungen
  - Stripe-Kundenportal und Rechnungen
  - `Other users` als schreibgeschützte Übersicht
- Details und Änderungen an fremden Nutzerdaten werden sowohl in der UI als
  auch serverseitig gesperrt. Direkte API-Aufrufe erhalten HTTP 403.

## Stripe-Architektur

- Partner sind Stripe Customers, keine Stripe-Connect-Accounts.
- Bezahlung erfolgt über Stripe Checkout; Verwaltung über Customer Portal.
- Test- und Live-Schlüssel sowie Webhook-Secrets werden im Adminbereich
  konfiguriert und niemals über öffentliche Settings ausgeliefert.
- `stripe_sandbox_mode` wählt Test- oder Live-Schlüssel.
- Wichtige Backend-Routen liegen vollständig unter `/api/partner-payment`:
  `status`, `settings`, `checkout`, `portal`, `stripe-status`, `invoices`,
  `webhook`.
- Stripe ist bewusst nicht Bestandteil der neuen isolierten Unit-Test-Suite;
  die externe Integration soll später separat stabilisiert werden.

## Surveys und Step-Editor

- Ärzte- und Pflege-Surveys sind getrennt und im Adminbereich umschaltbar.
- Neben Listen- und Flow-Ansicht existiert die Abhängigkeitsansicht mit
  Dagre-Layout auf Basis realer Conditions, ohne künstliche Sequenzkanten.
- Rekursive UND-/ODER-Regeln, Feld-Mappings und Flow-Positionen besitzen
  validierte Pydantic-Modelle.
- Der Edit-Step-Dialog zeigt den Step-Titel prominent im Kopf.
- Kontextbezogene Tooltips sind per Portal gerendert sowie mit Maus und
  Tastatur bedienbar.

## Tests

- Bestehende Standardsuite bleibt unter `backend/tests` und wird über
  `backend/pytest.ini` gesammelt.
- Neue Kandidatensuite liegt getrennt unter `backend/unit_tests_next`.
- Ausführung der Kandidatensuite:
  `cd backend && pytest -c pytest.next.ini`
- Letzter Stand der Kandidatensuite: `98 passed`.
- Sie deckt Modelle, Auth, Berechtigungen, Formularnormalisierung,
  Condition-Auswertung, Metriken und Partnerfreischaltung mit Positiv-,
  Negativ-, Grenzwert- und Fallback-Fällen ab.
- Relevante bestehende Regressionstests: zuletzt `128 passed`.
- Frontend-Produktionsbuild war nach den Partnerfreischaltungsänderungen grün.
- Generierte E2E-Screenshots unter `test_results/e2e-screenshots/` wurden aus
  Git entfernt und per `.gitignore` ausgeschlossen.

## Gefundene Robustheitskorrekturen

- Beschädigte Passwort-Hashes führen zu einem fehlgeschlagenen Login statt zu
  einem Serverfehler.
- JWTs mit ungültiger ObjectId werden als ungültige Tokens mit HTTP 401
  behandelt.
- Ungültige Legacy-Werte für `rows` und `heading_level` brechen
  Formularmigrationen nicht mehr ab.
- Snapshots ohne `collections` werden sicher normalisiert.

## Weiterarbeiten

- Vor Änderungen zuerst `git status` prüfen; reguläre Arbeit erfolgt auf
  `main`, solange kein neuer Feature-Branch angelegt wird.
- Stripe-Test-Price-IDs und Live-Price-IDs gehören zu getrennten Stripe-Modi.
- Keine realen Stripe-Zugangsdaten, Webhook-Secrets, Datenbankexporte oder
  personenbezogenen Uploads committen.
- `backend/server.py` und `frontend/src/pages/AdminDashboard.js` sind weiterhin
  groß; eine spätere Zerlegung sollte als eigenes Refactoring erfolgen.
- Detaillierter Sessionabschluss:
  `memory/session-2026-08-24-partner-onboarding.md`.
