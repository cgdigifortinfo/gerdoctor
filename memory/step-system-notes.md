# GERdoctor Memory Index

Stand: 2026-06-23

Diese Datei ist der Einstiegspunkt fuer spaetere Sessions. Die Detailnotizen sind thematisch getrennt, damit Design, Datenmodell, Programmierung und Step-Logik nicht wieder neu rekonstruiert werden muessen.

## Wichtigster Kontext

- Das Produkt wird von einem Aerzte-Anerkennungsflow in Richtung Pflegekraefte aus dem Ausland verschoben.
- Die drei Rollen bleiben bestehen: `user`, `partner`, `admin`.
- Es gibt jetzt Survey-Grundstruktur fuer mehrere Surveys mit unterschiedlichen URLs.
- Der bisherige Default-Survey bleibt als `aerzte` erhalten.
- Der neue vorbereitete Pflege-Survey ist unter Slug `pflege` erreichbar.
- Die Pflege-Landingpage ist lokal unter `/s/pflege` aufrufbar.
- Registrierung ueber `/s/pflege/register` speichert den Nutzer mit `survey_slug=pflege`.
- Admin kann Surveys verwalten und Steps nach Survey filtern.
- Beim Anlegen eines normalen Nutzers im Adminbereich kann der sichtbare Survey
  ausgewählt werden; Progress wird nur für diesen Survey initialisiert.

## Detaildateien

- [Standards für Slice-Extraktionen](slice-extraction-standards.md): verbindliche
  Schichtengrenzen, Typisierung, Coverage-, Mutation- und Regression-Gates.
- [Design-System FSP Pflege](design-system-fsp-pflege.md): Farben, Fonts, Logos, Icons, Referenzseite, UI-Regeln.
- [Datenstrukturen und API](data-structures-surveys.md): Survey-/Step-/User-/Progress-Felder, neue Endpunkte, Scoping.
- [Programmierung und Betrieb](programming-notes.md): Architektur, Startanleitung, Login-Daten, Verifikation.
- [Step Chain Logic](step-chain-logic.md): Abhaengigkeiten, lineare Kette, Migration, bekannte Risiken.
- [Betrieb, Seed und Performance vom 22.06.2026](session-2026-06-22-operations-performance.md): persistente Services, kanonischer Baseline-Seed, Reload-Optimierung, Messwerte und Teststand.
- [Dokumentation und Toolstack](documentation-toolstack.md): Lastenheft, Pflichtenheft, Markdown/Pandoc/Mermaid-Workflow und DOCX-Export.

## Geaenderte Kernbereiche

Backend:

- `backend/models.py`
- `backend/server.py`
- `backend/helpers.py`
- `backend/seed_baseline.py` (ersetzt alle historischen Seed-Skripte)
- `backend/email_template_defaults.py`
- `backend/migrate_linear_step_chain.py`
- `backend/migrate_pflege_survey_stages.py`

Frontend:

- `frontend/src/index.css`
- `frontend/src/App.css`
- `frontend/src/App.js`
- `frontend/src/lib/api.js`
- `frontend/src/contexts/AuthContext.js`
- `frontend/src/components/Logo.js`
- `frontend/src/pages/Landing.js`
- `frontend/src/pages/Auth.js`
- `frontend/src/pages/AdminDashboard.js`
- mehrere Dashboard-/Step-Komponenten mit Brand-Farben

## Aktueller lokaler Stand

Gepruefte Services:

- MongoDB: Container `gerdoctor-mongo`, Port `27017`
- Backend: Container `gerdoctor-backend`, Port `8001`
- Frontend: `npm start`, Port `3000`

Gepruefte URLs:

- `http://localhost:3000`
- `http://localhost:3000/s/pflege`
- `http://localhost:3000/s/pflege/register`
- `http://localhost:3000/admin`
- `http://localhost:8001/api/surveys/public`

Wichtige Login-Hinweise:

- Der kanonische Baseline-Seed enthält `admin@example.com / Admin123!`.
- Reproduzierbare Daten werden ausschließlich mit `backend/seed_baseline.py --force`
  wiederhergestellt; historische Einzel-Seeds wurden entfernt.
- Partner-Smoke-Login: `empfang@chrizz1001.de / Partner123!`.

## Performance-Stand

- User-Dashboard nutzt einen Bootstrap-Request statt sieben Einzelrequests.
- Der Bootstrap-Request berechnet Completion/ETA inzwischen aus den bereits
  geladenen Steps und Progress-Daten; dadurch entfallen doppelte MongoDB-Reads
  auf dem Reload-Hotpath.
- Admin- und Partner-Endpunkte verwenden Bulk-Metriken statt serieller N+1-Abfragen.
- Partner-Insights, Partner-Submissions und Other-Users lesen Stammdaten ueber
  `user_progress.step_order=1` statt ueber eine globale Step-1-ID. Das ist
  schneller und korrekt fuer parallele Surveys.
- AdminDashboard verhindert den doppelten initialen Request-Batch beim Setzen des Surveys.
- PartnerDashboard lädt vier unabhängige Ressourcen parallel.
- Gemessene Hotpaths liegen nach Optimierung zwischen ca. 0,02 und 0,42 Sekunden;
  vorher lagen einzelne Listen bei 5,9 bis 18,5 Sekunden.

## Session-Endstand 2026-06-23

- Letzter sauberer GitHub-/Ruecksetzpunkt vor der aktuellen lokalen
  Performance-/Security-Runde: `b8d55c2c5a9ffec39a6ec0cc72fc71d2aabe0bd0`.
- Der aktuelle Workspace enthaelt danach lokale, noch nicht committete
  Aenderungen in:
  - `backend/server.py`
  - `backend/helpers.py`
  - `backend/tests/test_reload_performance.py`
  - `backend/tests/test_file_access_security.py`
- Backend wurde nach den Aenderungen neu gestartet, damit neue Indizes und Code
  aktiv sind.
- Verifikation am Session-Ende:
  - `PYTHONPYCACHEPREFIX=/tmp/gerdoctor-pycache python3 -m py_compile backend/server.py backend/helpers.py backend/tests/test_file_access_security.py backend/tests/test_reload_performance.py`
  - `git diff --check`
  - `docker exec -e REACT_APP_BACKEND_URL=http://localhost:8001 gerdoctor-backend pytest -q tests/test_reload_performance.py tests/test_file_access_security.py tests/test_admin_user_survey_assignment.py tests/test_partner_insights_alignment.py tests/test_new_features_iter34.py tests/test_partner_completed_users_split.py tests/test_partner_milestone_complete.py`
  - Ergebnis: `24 passed`.
- Wichtiger Security-Hinweis aus den Logs: `JWT_SECRET` ist mit 26 Bytes kuerzer
  als die fuer HS256 empfohlenen 32 Bytes. Nicht automatisch geaendert, weil das
  Deployment-/Token-Konfiguration betrifft.

## Aktueller fachlicher Stand

Bereits umgesetzt:

- Mehrere Surveys koennen vorbereitet und per Slug aufgerufen werden.
- Pflege-Survey `pflege` existiert als eigener Survey-Datensatz.
- FSP-Pflege-Branding ist im Frontend eingezogen.
- Admin-Step-Editor kann Survey-Kontext auswaehlen.
- Step-Listen, Step-Erstellung, Reorder und Template-Anwendung sind survey-spezifisch vorbereitet.
- Bestehender Aerzte-Flow wurde in der Step-Logik linearisiert, damit Meilensteine logisch bis zum Ende fortlaufen.

Noch nicht final umgesetzt:

- Der Pflege-Survey hat 25 aktive Steps. Approbation wurde im gesamten
  Pflege-Kontext durch Anerkennung ersetzt; Gleichwertigkeitsprüfung ist
  entfernt. Zwischen Fachsprachenprüfung und Kenntnisprüfung liegt die neue
  Etappe Vorbereitungskurs Kenntnisprüfung.
- Partner-Tags, Upload-Anforderungen, E-Mail-Texte und Detailbedingungen fuer Pflege muessen fachlich definiert werden.
- Der Registrierungsprozess ist technisch survey-faehig, aber ggf. noch nicht vollstaendig auf mehrere parallele Pflege-/Spezial-Surveys ausgelegt.
