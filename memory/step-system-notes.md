# GERdoctor Memory Index

Stand: 2026-06-22

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

## Detaildateien

- [Design-System FSP Pflege](design-system-fsp-pflege.md): Farben, Fonts, Logos, Icons, Referenzseite, UI-Regeln.
- [Datenstrukturen und API](data-structures-surveys.md): Survey-/Step-/User-/Progress-Felder, neue Endpunkte, Scoping.
- [Programmierung und Betrieb](programming-notes.md): Architektur, Startanleitung, Login-Daten, Verifikation.
- [Step Chain Logic](step-chain-logic.md): Abhaengigkeiten, lineare Kette, Migration, bekannte Risiken.
- [Betrieb, Seed und Performance vom 22.06.2026](session-2026-06-22-operations-performance.md): persistente Services, kanonischer Baseline-Seed, Reload-Optimierung, Messwerte und Teststand.

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
- Admin- und Partner-Endpunkte verwenden Bulk-Metriken statt serieller N+1-Abfragen.
- AdminDashboard verhindert den doppelten initialen Request-Batch beim Setzen des Surveys.
- PartnerDashboard lädt vier unabhängige Ressourcen parallel.
- Gemessene Hotpaths liegen nach Optimierung zwischen ca. 0,02 und 0,42 Sekunden;
  vorher lagen einzelne Listen bei 5,9 bis 18,5 Sekunden.

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
