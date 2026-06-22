# Betrieb, Baseline-Seed und Performance

Stand: 2026-06-22

Diese Datei hält den konsolidierten Stand der Session vom 22.06.2026 fest.

## Persistenter lokaler Betrieb

Die maßgebliche Definition ist `compose.yaml` im Projektroot.

- MongoDB: Container `gerdoctor-mongo`, Port `27017`
- Backend: Container `gerdoctor-backend`, Port `8001`
- Frontend: CRACO-Dev-Server auf Port `3000`
- Backend-Datenbank: `test_database`
- Backend verbindet intern über `mongodb://mongo:27017`

Persistente Docker-Volumes:

- `gerdoctor-mongo-data` -> `/data/db`
- `gerdoctor-mongo-config` -> `/data/configdb`
- `gerdoctor-uploads` -> `/var/lib/gerdoctor/uploads`
- `gerdoctor-backend-tmp` -> `/tmp`

Damit bleiben Datenbank, Uploads und Backend-Temp-Dateien über Container-Neustarts
erhalten. Beide Container verwenden `restart: unless-stopped`.

Standardstart:

```bash
cd /home/chrizz1001/apps/gerdoctor
docker compose up -d mongo backend
cd frontend
BROWSER=none HOST=0.0.0.0 PORT=3000 npm start
```

Status und Logs:

```bash
docker ps
docker logs --tail 100 gerdoctor-backend
```

## Kanonischer Seed

Es gibt nur noch eine Seed-Datei:

- `backend/seed_baseline.py`

Die historischen, voneinander abhängigen Seed-Dateien wurden nach Sicherung
gelöscht. Das Backup liegt unter:

- `backups/seed-files-20260622-0808.zip`

Der Baseline-Seed enthält einen komprimierten Extended-JSON-Snapshot mit
erhaltenen ObjectIds sowie deduplizierte Upload-Binärdaten. Er ersetzt die
gesamte Datenbank und den Upload-Ordner atomar aus Sicht des lokalen Setups.

Wiederherstellen (destruktiv für den aktuellen lokalen DB-/Upload-Stand):

```bash
docker exec gerdoctor-backend python /app/backend/seed_baseline.py --force
docker restart gerdoctor-backend
```

Nur prüfen:

```bash
docker exec gerdoctor-backend python /app/backend/seed_baseline.py --verify-only
```

Kanonische Counts:

- Surveys: 2
- Steps: 50 (25 Ärzte, 25 Pflege)
- Users: 511
- Partners: 36
- User Progress: 12025
- Partner Submissions: 624
- Files/Uploads: 544
- CMS Sections: 4
- Site Settings: 1
- E-Mail-Templates: 10

Die Verifikation prüft Counts, User-/Step-/Partner-Referenzen, doppelte E-Mails,
Upload-Metadaten und SHA-256-Checksummen der Upload-Objekte.

`backend/email_template_defaults.py` enthält die wiederverwendbaren Default-
Templates. Der Server importiert keine entfernten historischen Seeds mehr.

## Reload-Performance: Ursachen

Die Hauptursachen der langsamen Reloads waren:

- kaum passende MongoDB-Indizes;
- serielle N+1-Abfragen für Benutzer-Metriken und Partner-Arbeitsstatus;
- sieben getrennte Requests beim User-Dashboard-Reload;
- ein doppelter kompletter Admin-Request-Batch, weil `activeSurveyId` während
  `loadData` gesetzt wurde und die Callback-Abhängigkeit erneut auslöste;
- ein zusätzlicher doppelter Steps-Request im Admin-Dashboard;
- teilweise sequenzielle, unabhängige Partner-Dashboard-Requests.

## Backend-Optimierungen

In `backend/helpers.py`:

- `calculate_users_metrics(user_ids)` berechnet Metriken für viele Nutzer mit
  drei gebündelten DB-Abfragen.
- `_metrics_from_loaded_context(...)` berechnet das Ergebnis aus bereits
  geladenen Steps und Progress-Datensätzen.

In `backend/server.py`:

- Bulk-Partner-Arbeitsstatus über `_partner_work_status_for_users(...)`.
- `/api/admin/users`, `/api/admin/partners`, `/api/partner/submissions` und
  `/api/partner/other-users` laden Progress, Submissions, Profile und Beziehungen
  gesammelt statt pro Tabellenzeile.
- `/api/partner/insights` lädt Stammdaten gesammelt.
- `GET /api/steps` verwendet nur eine Steps-Abfrage.
- `GET /api/steps/bootstrap` liefert den kompletten User-Dashboard-Startzustand.
- CMS-Payloads mit historisch rekursiv verschachteltem `content` werden beim
  Lesen, Schreiben und Startup normalisiert.

Startup-Indizes:

- `users(email)` unique, `users(role,survey_id)`, `users(partner_id)`
- `surveys(slug)` unique
- `steps(survey_id,is_active,order)`, `steps(is_active,order)`
- `user_progress(user_id,step_id)` unique
- `user_progress(user_id,survey_id)`
- `user_progress(step_id,status)`
- `user_progress(user_id,status,step_order)`
- `partner_submissions(partner_id,user_id)`
- `partner_submissions(user_id,partner_id)`
- `partner_submissions(partner_id,created_at desc)`
- `files(id)` unique, `partners(name)`
- `progress_history(user_id,timestamp desc)`
- `audit_logs(timestamp desc)`

## Frontend-Optimierungen

- `UserDashboard.js` lädt initial nur `stepsAPI.getBootstrap(...)` statt sieben
  einzelner Ressourcen.
- `PartnerDashboard.js` lädt Submissions, Other Users, Profil und Insights in
  einem `Promise.all`.
- `AdminDashboard.js` entkoppelt den initialen Batch von `activeSurveyId`, nutzt
  funktionales Setzen des Survey-States und verhindert mit
  `loadedStepsSurveyRef` doppelte initiale Step-Abfragen.
- Request-IDs verhindern, dass eine ältere Admin-Antwort einen neueren Zustand
  überschreibt.

## Gemessene Resultate

Authentifizierte lokale API-Messungen vor und nach der Optimierung:

| Endpoint | Vorher | Nachher |
|---|---:|---:|
| Admin Users | 18,53 s | 0,42 s |
| Admin Partners | 5,88 s | 0,21 s |
| Admin Analytics | 0,90 s | 0,16 s |
| Partner Submissions | 8,99 s | 0,12 s |
| Partner Other Users | 11,76 s | 0,10 s |
| Partner Insights | 0,92 s | 0,02 s |
| User Bootstrap | vorher 7 Requests | 0,025 s / 1 Request |

`backend/tests/test_reload_performance.py` schützt Bootstrap-Vollständigkeit,
Hotpath-Laufzeiten und erforderliche Indizes gegen Regressionen ab.

## Teststand

Abschlusslauf der Session:

- Backend Unit/Integration ohne Browser-Suiten: `176 passed`, eine externe
  Starlette-PendingDeprecationWarning.
- Reload-Performance: `3 passed` in 1,92 s.
- Aktive Playwright-E2E-Suiten: `6 passed`.
- `15 skipped`: ausschließlich der bewusst deaktivierte Legacy-12-Step-
  Walkthrough; ersetzt durch Survey-v2- und kombinatorische Tests.
- Frontend Jest: keine Testdateien vorhanden, mit `--passWithNoTests` erfolgreich.
- Frontend Production Build: erfolgreich, Hauptbundle ca. 346 kB gzip.
- `git diff --check`: ohne Whitespace-Fehler.
- Baseline-Verifikation nach Wiederherstellung: erfolgreich.

Spätere Pflege-Anpassung derselben Session:

- Pflege-Approbation vollständig in Pflege-Anerkennung umbenannt.
- Gleichwertigkeitsprüfung ist im Pflege-Flow nicht enthalten.
- Sprachprüfung heißt jetzt Fachsprachenprüfung.
- Vorbereitungskurs Kenntnisprüfung (Orders 15–18) und Kenntnisprüfung
  (Orders 19–22) als vollständige Etappen ergänzt.
- Jobangebote auf Orders 23–25 verschoben und linear an Milestone 22 angebunden.
- Partner-Tags angepasst; jede Pflege-Service-Etappe hat zwei passende Partner.
- Baseline auf 50 Steps neu erzeugt; Upload-Restore leert bei Docker-Volumes nur
  den Inhalt und löscht nicht mehr den Mountpoint (`EBUSY`-Fix).
- Vollständige Backend-Suite danach: `177 passed`.

E2E-Testabhängigkeiten stehen in `backend/requirements-test.txt`. Im aktuellen
Backend-Container wurden Playwright 1.60.0 und Chromium installiert. Bei einem
neu erstellten Container ist zusätzlich erforderlich:

```bash
python -m pip install -r /app/backend/requirements-test.txt
python -m playwright install --with-deps chromium
```

Browser-Tests im Container verwenden `localhost:3000` als Origin und mappen
`localhost` per Chromium-Argument auf `host.docker.internal`, damit CORS und
Container-zu-Host-Zugriff zusammenpassen.

## Wichtige Testanpassungen

- Admin-Step-Abfragen in Tests müssen im Multi-Survey-Betrieb explizit
  `?survey_slug=aerzte` oder eine `survey_id` verwenden. Globale Step-Listen sind
  wegen gleicher Orders in mehreren Surveys nicht eindeutig.
- Python 3.12: Teardowns verwenden `asyncio.run(...)`; eine mehrfach verwendete
  Motor-Fixture nutzt einen persistenten `asyncio.Runner`, damit der Client nicht
  an einen bereits geschlossenen Eventloop gebunden bleibt.
- Tests, die Steps/Templates temporär anlegen, räumen diese in `finally` wieder
  auf, um keine Orphans zu hinterlassen.

## Abschlusszustand

- MongoDB und Backend laufen persistent.
- Frontend läuft auf Port 3000.
- Der kanonische Basisstand wurde nach den mutierenden Tests wiederhergestellt.
- Relationen und Upload-Checksummen sind plausibel und verifiziert.
- Die Performance-Regressionsuite ist grün.
