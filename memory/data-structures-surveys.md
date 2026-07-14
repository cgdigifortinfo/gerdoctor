# Datenstrukturen und API fuer Surveys

Stand: 2026-06-23

Diese Notiz beschreibt den aktuell vorbereiteten Multi-Survey-Stand.

## Survey-Konzept

Neu eingefuehrt wurde eine Survey-Ebene oberhalb der Steps. Ziel ist, spaeter mehrere fachliche Surveys ueber unterschiedliche URLs betreiben zu koennen, inklusive eigener Registrierung.

Aktuelle Slugs:

- `aerzte`: bestehender Default-Flow fuer Aerzte-Anerkennung.
- `pflege`: vorbereiteter FSP-Pflege-Flow.

Der Pflege-Survey besitzt aktuell 25 aktive Steps. Der Ärzte-Survey besitzt
ebenfalls 25 aktive Steps. Die Pflege-Kette ist technisch lauffähig.

## Survey-Felder

Survey-Datensaetze enthalten sinngemaess:

- `id`
- `name`
- `slug`
- `description`
- `is_active`
- `is_default`
- `theme`
- `created_at`
- `updated_at`

Das `theme`-Objekt kann enthalten:

- `primary_color`
- `secondary_color`
- `accent_color`
- `logo_url`
- `icon_url`

## User-Felder

Registrierte Nutzer koennen Survey-Kontext tragen:

- `survey_id`
- `survey_slug`

Bei Registrierung ueber `/s/pflege/register` wird `survey_slug=pflege` an das Backend uebergeben. Das Backend loest daraus den Survey auf und legt Progress nur fuer Steps dieses Surveys an.

## Step-Felder

Steps koennen einem Survey zugeordnet werden:

- `survey_id`

Bestehende Steps ohne Survey werden beim Backend-Startup auf den Default-Survey `aerzte` zurueckgefuehrt.

Wichtige bestehende Step-Felder bleiben:

- `title`
- `description`
- `order`
- `step_type`
- `fields`
- `filter_tag`
- `conditions`
- `required_fields`
- `required_uploads`
- `field_mappings`
- `duration_value`
- `duration_unit`
- `email_on_enter`
- `email_on_edit`
- `email_on_leave`

## Progress-Felder

Progress wird survey-spezifisch vorbereitet:

- `user_id`
- `step_id`
- `survey_id`
- `status`
- `data`
- `files`
- `completed_at`
- `updated_at`

`backend/helpers.py` scoped Step-Kontext inzwischen ueber den Survey des Users. Dadurch werden Conditions und Auto-Completes nicht versehentlich ueber Steps anderer Surveys ausgewertet.

## Backend-Endpunkte

Public:

- `GET /api/surveys/public`
- `GET /api/surveys/slug/{slug}`

User-Dashboard:

- `GET /api/steps/bootstrap?survey_slug=...` liefert in einem Request Steps,
  Progress, alle Step-Daten, Notification Preferences, History, ETA und Settings.
  Dieser Endpoint ersetzt beim initialen Reload sieben getrennte Requests.

Auth:

- `POST /api/auth/register` akzeptiert optional `survey_slug`.
- `POST /api/auth/login` gibt Survey-Informationen im User-Payload zurueck.
- `GET /api/auth/me` gibt Survey-Informationen im User-Payload zurueck.

Admin Users:

- `POST /api/admin/users` akzeptiert für `role=user` optional `survey_id`.
- Der Admin-Dialog zeigt für normale Nutzer eine verpflichtende Auswahl aller
  aktiven Surveys.
- Das Backend validiert den Survey, speichert `survey_id` und `survey_slug` und
  erzeugt ausschließlich für dessen aktive Steps Pending-Progress-Einträge.
- Fehlt `survey_id` bei älteren API-Aufrufern, wird der Default-Survey verwendet.
- Partnerkonten erhalten keine Survey-Zuordnung über diesen Dialog.

Admin Surveys:

- `GET /api/admin/surveys`
- `POST /api/admin/surveys`
- `PUT /api/admin/surveys/{survey_id}`

Admin Steps:

- `GET /api/admin/steps?survey_id=...`
- `GET /api/admin/steps?survey_slug=...`
- `POST /api/admin/steps` akzeptiert `survey_id`.
- `PUT /api/admin/steps/{step_id}` akzeptiert `survey_id`.
- `POST /api/admin/steps/reorder` akzeptiert optional `survey_id`.
- Template-Anwendung akzeptiert optional `survey_id`.

## Frontend API

Wichtige Anpassungen in `frontend/src/lib/api.js`:

- `authAPI.register(email, password, name, survey_slug)`
- `stepsAPI.getAll(surveySlug)`
- `stepsAPI.getProgress(surveySlug)`
- `stepsAPI.getAllData(surveySlug)`
- `stepsAPI.getBootstrap(surveySlug)`
- `adminAPI.getSurveys()`
- `adminAPI.createSurvey(payload)`
- `adminAPI.updateSurvey(surveyId, payload)`
- `adminAPI.getSteps(surveyId)`
- `adminAPI.reorderSteps(step_ids, survey_id)`
- `adminAPI.applyStepTemplate(templateId, order, surveyId)`
- `surveysAPI.listPublic()`
- `surveysAPI.getBySlug(slug)`

## Frontend-Routen

Neue oder relevante Routen:

- `/`
- `/login`
- `/register`
- `/s/:surveySlug`
- `/s/:surveySlug/login`
- `/s/:surveySlug/register`
- `/dashboard`
- `/partner-dashboard`
- `/admin`

Die Survey-Routen werden aktuell vor allem fuer Landing/Auth genutzt. Dashboard und Step-Darstellung leiten sich aus dem eingeloggten User und dessen Survey ab.

## Admin-Step-Editor

Der Admin-Step-Editor wurde erweitert:

- Survey-Auswahl im Step-Tab.
- Button zum Oeffnen der Survey-URL.
- Button zum Anlegen eines Surveys.
- Step-Dialog besitzt Survey-Auswahl.
- Step-Speichern sendet `survey_id`.
- Reorder laeuft fuer den aktiven Survey.
- Flow-Builder/Add/Edit beruecksichtigt `survey_id`.

Test-ID fuer Survey-Auswahl:

- `data-testid="admin-survey-select"`
- `data-testid="step-survey-select"`

## Startup-/Backfill-Verhalten

Beim Backend-Startup werden Survey-Datensaetze sichergestellt:

- Default-Survey `aerzte`
- Pflege-Survey `pflege`

Backfill:

- Existing Steps ohne `survey_id` werden dem Default-Survey zugeordnet.
- Existing Users ohne Survey-Kontext werden dem Default-Survey zugeordnet.
- Existing Progress ohne `survey_id` wird entsprechend ergaenzt.

Beim Startup werden außerdem die für Reload-Hotpaths benötigten MongoDB-Indizes
idempotent angelegt. Dazu gehören insbesondere `users(role,survey_id)`,
`steps(survey_id,is_active,order)`, der eindeutige Index
`user_progress(user_id,step_id)` sowie Indizes für Partner-Submissions,
Progress-History, Files und Audit-Logs.

Erweiterter Index-Stand nach der Performance-/Security-Runde vom 2026-06-23:

- `users.email` eindeutig
- `users(role,survey_id)`
- `users.partner_id`
- `users(role,created_at)`
- `surveys.slug` eindeutig
- `surveys(is_active,is_default)`
- `steps(survey_id,is_active,order)`
- `steps(is_active,order)`
- `user_progress(user_id,step_id)` eindeutig
- `user_progress(user_id,survey_id)`
- `user_progress(user_id,step_order)`
- `user_progress(step_id,status)`
- `user_progress(user_id,status,step_order)`
- `partner_submissions(partner_id,user_id)`
- `partner_submissions(user_id,partner_id)`
- `partner_submissions(partner_id,created_at)`
- `files.id` eindeutig
- `files(user_id,created_at)`
- `partners.name`
- `partners(is_active,tags)`
- `progress_history(user_id,timestamp)`
- `audit_logs(timestamp)`

## Upload-/Dateizugriff-Security

Dateiuploads wurden am 2026-06-23 gehaertet:

- `MAX_UPLOAD_BYTES` begrenzt Uploads, Default: 20 MB.
- Erlaubte Erweiterungen: `pdf`, `png`, `jpg`, `jpeg`, `webp`, `gif`, `doc`,
  `docx`, `xls`, `xlsx`, `csv`, `txt`, `zip`.
- Aktive Inhalte mit Content Types `text/html`, `application/xhtml+xml`,
  `image/svg+xml`, `application/javascript`, `text/javascript` werden blockiert.
- Dateinamen werden mit `PurePath(...).name` auf Basename reduziert.
- Download von `/api/files/{file_id}` ist nur erlaubt fuer Datei-Owner, Admin
  oder Partner, wenn der Datei-Owner ueber `linked_user_ids` oder
  `partner_submissions` diesem Partner zugeordnet ist.

Regressionstest: `backend/tests/test_file_access_security.py`.

## Aktueller lokaler Stand am Session-Ende 2026-06-23

- GitHub-/Ruecksetzpunkt vor aktueller lokaler Optimierungsrunde:
  `b8d55c2c5a9ffec39a6ec0cc72fc71d2aabe0bd0`.
- Danach lokale, noch nicht committete Aenderungen:
  - `backend/server.py`
  - `backend/helpers.py`
  - `backend/tests/test_reload_performance.py`
  - `backend/tests/test_file_access_security.py`
- Gezielte Tests am Ende: `24 passed`.

## Bekannte Grenzen

- Die Pflege-Etappen laufen aktuell linear über Anerkennung, Sprachschule,
  Fachsprachenprüfung, Vorbereitungskurs Kenntnisprüfung, Kenntnisprüfung und
  Jobangebote. Eine Gleichwertigkeitsprüfung ist nicht enthalten.
- Multi-Survey-Registrierung funktioniert fuer Slug-basierte Registrierung, aber spezielle Registrierungsfelder pro Survey sind noch nicht ausmodelliert.
- Survey-spezifische E-Mail-Texte und Partner-Tags muessen noch ergaenzt werden.
