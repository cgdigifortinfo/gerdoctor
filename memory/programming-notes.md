# Programmierung und lokaler Betrieb

Stand: 2026-06-22

## Arbeitsverzeichnis

```bash
cd /home/chrizz1001/apps/gerdoctor
```

## Services und Persistenz

Die verbindliche Definition steht in `compose.yaml`.

- MongoDB: `gerdoctor-mongo`, Port `27017`
- Backend: `gerdoctor-backend`, Port `8001`
- Frontend: CRACO auf Port `3000`
- Datenbank: `test_database`

Persistente Named Volumes:

- `gerdoctor-mongo-data`
- `gerdoctor-mongo-config`
- `gerdoctor-uploads`
- `gerdoctor-backend-tmp`

Die Volumes erhalten Datenbank, Uploads und Backend-Temp-Dateien bei Neustarts.

## Server starten

```bash
docker compose up -d mongo backend
cd frontend
BROWSER=none HOST=0.0.0.0 PORT=3000 npm start
```

Wenn die Container bereits existieren:

```bash
docker start gerdoctor-mongo
docker restart gerdoctor-backend
```

Status und Logs:

```bash
docker ps
docker logs --tail 100 gerdoctor-backend
```

Erwartete Backend-Umgebung laut Compose:

```text
MONGO_URL=mongodb://mongo:27017
DB_NAME=test_database
JWT_SECRET=gerdoctor-local-dev-secret
FRONTEND_URL=http://localhost:3000
LOCAL_STORAGE_ROOT=/var/lib/gerdoctor/uploads
TMPDIR=/tmp
```

## Kanonischen Datenstand herstellen

Historische Einzel-Seeds wurden entfernt. Ausschließlich verwenden:

```bash
docker exec gerdoctor-backend python /app/backend/seed_baseline.py --force
docker restart gerdoctor-backend
```

Der Force-Modus löscht und ersetzt die lokale Datenbank sowie den persistenten
Upload-Ordner. Nur verifizieren:

```bash
docker exec gerdoctor-backend python /app/backend/seed_baseline.py --verify-only
```

Backup der alten Seed-Dateien:

```text
backups/seed-files-20260622-0808.zip
```

## Logins

- Admin: `admin@example.com / Admin123!`
- Partner: `empfang@chrizz1001.de / Partner123!`
- Alternativer Partner: `partner-example@chrizz1001.de / Partner123!`

Admin-Login prüfen:

```bash
curl -s -o /tmp/login-admin.json -w "%{http_code}" \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"Admin123!"}' \
  http://localhost:8001/api/auth/login
```

## Health und URLs

```bash
curl -I http://localhost:3000
curl -s -o /tmp/gerdoctor-api-root.txt -w "%{http_code}" \
  http://localhost:8001/api/
```

Wichtige URLs:

- `http://localhost:3000/`
- `http://localhost:3000/s/pflege`
- `http://localhost:3000/s/pflege/register`
- `http://localhost:3000/admin`
- `http://localhost:8001/api/surveys/public`
- `http://localhost:8001/api/surveys/slug/pflege`

## Tests

Backend Unit/Integration ohne Browser-Suiten:

```bash
docker exec -e REACT_APP_BACKEND_URL=http://localhost:8001 \
  gerdoctor-backend pytest -q tests \
  --ignore=tests/e2e_email_template_editor.py \
  --ignore=tests/e2e_flowbuilder.py \
  --ignore=tests/test_admin_survey_steps_e2e.py \
  --ignore=tests/test_landing_pages_e2e.py \
  --ignore=tests/test_e2e_step_walkthrough.py
```

Performance-Regressions:

```bash
docker exec -e REACT_APP_BACKEND_URL=http://localhost:8001 \
  gerdoctor-backend pytest -q tests/test_reload_performance.py
```

Frontend:

```bash
cd frontend
npm test -- --watchAll=false --passWithNoTests
npm run build
```

Playwright-Abhängigkeiten bei einem neu erstellten Container:

```bash
docker exec gerdoctor-backend \
  python -m pip install -r /app/backend/requirements-test.txt
docker exec gerdoctor-backend \
  python -m playwright install --with-deps chromium
```

Aktive Browser-E2E-Suiten:

```bash
docker exec \
  -e REACT_APP_BACKEND_URL=http://localhost:8001 \
  -e FRONTEND_URL=http://localhost:3000 \
  gerdoctor-backend pytest -q -rs \
  tests/e2e_email_template_editor.py \
  tests/e2e_flowbuilder.py \
  tests/test_admin_survey_steps_e2e.py \
  tests/test_landing_pages_e2e.py \
  tests/test_e2e_step_walkthrough.py
```

Der Legacy-Walkthrough ist absichtlich übersprungen. Aktueller Abschlussstand
nach der Pflege-Flow-Anpassung: 177 Backend-Tests bestanden; die vorhandenen
3 Performance-Tests und 6 aktiven E2E-Tests bleiben grün.

## Headless-Browser im Backend-Container

Für CORS muss der Browser-Origin `http://localhost:3000` bleiben. Container-
Chromium mappt localhost auf den Host:

```python
p.chromium.launch(
    headless=True,
    args=[
        "--no-sandbox",
        "--host-resolver-rules=MAP localhost host.docker.internal",
    ],
)
```

## Multi-Survey-Testregel

Admin-Step-Listen nie ohne Survey-Filter als Order-Map verwenden. Korrekt:

```text
/api/admin/steps?survey_slug=aerzte
```

oder mit expliziter `survey_id`. Orders sind nur innerhalb eines Surveys
eindeutig.

## Reload-Architektur

- UserDashboard: `GET /api/steps/bootstrap` als initialer Einzelrequest.
- PartnerDashboard: vier unabhängige Ressourcen parallel per `Promise.all`.
- AdminDashboard: ein initialer paralleler Batch; Survey-State löst keinen
  zweiten vollständigen Batch aus.
- Backend: Bulk-Metriken und Bulk-Partnerstatus, keine seriellen N+1-Queries.
- MongoDB-Indizes werden bei jedem Backend-Startup idempotent sichergestellt.

Details und Messwerte stehen in
[`session-2026-06-22-operations-performance.md`](session-2026-06-22-operations-performance.md).
