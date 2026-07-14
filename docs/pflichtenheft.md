# Pflichtenheft

## Deckblatt

| Feld | Inhalt |
|---|---|
| Projekt | GERdoctor / IHCA Multi-Survey-Plattform |
| Dokument | Pflichtenheft |
| Stand | 2026-07-14 |
| Status | Technischer Entwurf auf Basis des aktuellen lokalen Projektstands |
| Zweck | Beschreibung der technischen Umsetzung einer generischen Survey-/Step-Plattform |
| Beispielszenarien | Ärzte-Survey und Pflege-Survey als Referenzkonfigurationen |

## Inhaltsverzeichnis

- [1. Zweck des Dokuments](#1-zweck-des-dokuments)
- [2. Systemarchitektur](#2-systemarchitektur)
- [3. Technologiestack](#3-technologiestack)
- [4. Datenmodell](#4-datenmodell)
- [5. Step Engine](#5-step-engine)
- [6. Backend-Schnittstellen](#6-backend-schnittstellen)
- [7. Frontend](#7-frontend)
- [8. Rechte- und Sicherheitskonzept](#8-rechte--und-sicherheitskonzept)
- [9. Performance-Konzept](#9-performance-konzept)
- [10. Betrieb](#10-betrieb)
- [11. Tests](#11-tests)
- [12. Abgrenzungen und offene Punkte](#12-abgrenzungen-und-offene-punkte)
- [13. Technische Abnahmekriterien](#13-technische-abnahmekriterien)
- [14. Produktionsbetrieb und Deployment](#14-produktionsbetrieb-und-deployment)
- [15. Rollen- und Rechtematrix](#15-rollen--und-rechtematrix)
- [16. Datenschutz- und Sicherheitskonzept](#16-datenschutz--und-sicherheitskonzept)
- [17. Monitoring, Logging und Backup](#17-monitoring-logging-und-backup)
- [18. Test- und Abnahmekonzept](#18-test--und-abnahmekonzept)
- [19. Migration, Wartung und Support](#19-migration-wartung-und-support)
- [20. Ausschreibungsannahmen](#20-ausschreibungsannahmen)

## 1. Zweck des Dokuments

Dieses Pflichtenheft beschreibt, wie die im Lastenheft genannten Anforderungen
technisch umgesetzt werden. Es dokumentiert Architektur, Module, Datenmodell,
Schnittstellen, Rechtekonzept, Sicherheitsmaßnahmen, Tests und Betriebsabläufe.

Die vorhandenen Surveys `aerzte` und `pflege` werden als Beispielkonfigurationen
verstanden. Ziel ist die generische Darstellbarkeit unterschiedlicher fachlicher
Szenarien über dieselbe Survey-/Step-Engine. Anwendernahe Beispiele verwenden
überwiegend den Ärzte-Kontext.

## 2. Systemarchitektur

![Systemarchitektur](docs/charts/pflichtenheft-systemarchitektur.png)

### 2.1 Komponenten

| Komponente | Pfad | Aufgabe |
|---|---|---|
| Backend | `backend/server.py` | API, Auth, Uploads, Admin-/Partner-/User-Endpunkte |
| Helper | `backend/helpers.py` | Step-Logik, Metriken, E-Mails, Auto-Completes |
| Modelle | `backend/models.py` | Pydantic-Modelle und Payload-Strukturen |
| Datenbank | `backend/database.py` | MongoDB-Verbindung |
| Seed | `backend/seed_baseline.py` | Kanonischer Daten- und Upload-Snapshot |
| Frontend | `frontend/src` | React-App mit Dashboards, Landing, Auth und Admin UI |
| API Client | `frontend/src/lib/api.js` | Zentraler Frontend-API-Zugriff |
| Visibility | `frontend/src/lib/stepVisibility.js` | Clientseitige Step-Sichtbarkeitslogik |

## 3. Technologiestack

| Bereich | Technologie | Kurzbeschreibung |
|---|---|---|
| Backend | Python / FastAPI | HTTP-API, Authentifizierung, Rollen, Survey-/Step-Logik |
| Datenbank | MongoDB | Persistenz für Nutzer, Surveys, Steps, Progress, Partner, Dateien |
| Frontend | React / CRACO | Single Page Application mit User-, Partner- und Admin-Dashboard |
| Betrieb | Docker Compose | Lokaler Betrieb von MongoDB und Backend |
| Uploads | Lokaler Object Storage | Persistente Ablage von Upload-Dateien über Docker-Volume |
| Tests | Pytest / Playwright | Backend-, Performance-, Security- und Browser-Regressionen |
| Dokumentation | Markdown, PNG-/SVG-Diagramme, Pandoc | Versionierbare Quelldokumente und DOCX-Export |

## 4. Datenmodell

Die Datenmodelle sind in MongoDB dokumentorientiert gespeichert. Tabellen in
diesem Abschnitt beschreiben die fachlich relevanten Felder, Datentypen und
ihre Funktion. Technische Zusatzfelder können je Collection vorhanden sein.

### 4.1 Survey

Ein Survey ist eine eigenständige Prozesskonfiguration mit eigenem Slug, eigener
Landingpage, eigenem Step-Set, eigenem Progress-Kontext und optional eigenem
Branding.

| Feld | Datentyp | Kurzbeschreibung |
|---|---|---|
| `id` / `_id` | `ObjectId` / `string` | Eindeutige technische ID des Surveys |
| `name` | `string` | Anzeigename, z. B. Ärzte oder Pflege |
| `slug` | `string` | URL- und API-Schlüssel, z. B. `aerzte` oder `pflege` |
| `description` | `string` | Kurzbeschreibung des fachlichen Szenarios |
| `is_active` | `boolean` | Steuert, ob der Survey öffentlich nutzbar ist |
| `is_default` | `boolean` | Kennzeichnet den Standard-Survey für Legacy- oder Fallback-Fälle |
| `theme` | `object` | Optionale Branding-Informationen wie Farben, Logo und Icon |
| `created_at` | `datetime string` | Erstellzeitpunkt |
| `updated_at` | `datetime string` | Letzte Änderung |

### 4.2 User

User repräsentieren normale Nutzer, Partnerkonten und Admins.

| Feld | Datentyp | Kurzbeschreibung |
|---|---|---|
| `_id` | `ObjectId` | Eindeutige technische ID des Nutzers |
| `email` | `string` | Login-E-Mail, eindeutig |
| `password_hash` | `string` | Gehashter Passwortwert |
| `name` | `string` | Anzeigename |
| `role` | `enum` | Rolle: `user`, `partner` oder `admin` |
| `survey_id` | `string` / `null` | Zugeordneter Survey für normale Nutzer |
| `survey_slug` | `string` / `null` | Lesbarer Survey-Schlüssel |
| `partner_id` | `string` / `null` | Zugeordnete Partnerorganisation bei Partner-Usern |
| `notification_prefs` | `object` | Benachrichtigungseinstellungen, z. B. E-Mail Opt-out |
| `created_at` | `datetime string` | Erstellzeitpunkt |
| `updated_at` | `datetime string` | Letzte Änderung |

### 4.3 Step

Steps sind survey-spezifische Prozessbausteine. Sie modellieren Aufgaben,
Entscheidungen, Uploads, Partnerauswahl, Meilensteine oder reine Anzeigen.

| Feld | Datentyp | Kurzbeschreibung |
|---|---|---|
| `_id` | `ObjectId` | Eindeutige technische ID des Steps |
| `survey_id` | `string` | Zugehöriger Survey |
| `title` | `string` | Anzeigename des Steps |
| `description` | `string` | Fachliche Beschreibung oder Hilfetext |
| `order` | `integer` | Reihenfolge innerhalb des Surveys |
| `step_type` | `enum` | Typ: `form`, `decision`, `partner_selection`, `partner_multiselection`, `milestone`, `display` |
| `fields` | `array<object>` | Formular-, Decision- oder Uploadfelder |
| `conditions` | `array<object>` | Sichtbarkeits-, Blockierungs- oder Auto-Complete-Regeln |
| `required_fields` | `array<string>` | Pflichtfelder, die zur Fertigstellung nötig sind |
| `required_uploads` | `array<string>` | Erforderliche Upload-Schlüssel |
| `filter_tag` | `string` / `null` | Fachliches Tag für Partner-Matching |
| `duration_value` | `integer` / `null` | Dauerwert für ETA-Berechnung |
| `duration_unit` | `enum` / `null` | Einheit, z. B. Tage, Wochen oder Monate |
| `translations` | `object` | Übersetzungen für mehrsprachige Darstellung |
| `is_active` | `boolean` | Aktivierungsstatus |

### 4.4 User Progress

Progress verbindet Nutzer, Survey und Step. Er ist die zentrale Statusquelle der
Journey.

| Feld | Datentyp | Kurzbeschreibung |
|---|---|---|
| `_id` | `ObjectId` | Eindeutige technische ID des Progress-Eintrags |
| `user_id` | `string` | Zugehöriger Nutzer |
| `step_id` | `string` | Zugehöriger Step |
| `survey_id` | `string` | Zugehöriger Survey |
| `step_order` | `integer` | Step-Reihenfolge als schnelle Filter- und Anzeigehilfe |
| `status` | `enum` | Status, z. B. `pending`, `in_progress`, `completed` |
| `data` | `object` | Erfasste Formular-, Decision- oder Partnerdaten |
| `files` | `array<object>` | Zugeordnete Upload-Metadaten |
| `completed_at` | `datetime string` / `null` | Abschlusszeitpunkt |
| `created_at` | `datetime string` | Erstellzeitpunkt |
| `updated_at` | `datetime string` | Letzte Änderung |

### 4.5 Partner Submission

Partner Submissions verbinden Nutzer mit Partnerorganisationen und steuern
Partnerzugriff sowie Partnerbearbeitung.

| Feld | Datentyp | Kurzbeschreibung |
|---|---|---|
| `_id` | `ObjectId` | Eindeutige technische ID |
| `partner_id` | `string` | Zugeordnete Partnerorganisation |
| `user_id` | `string` | Betroffener Nutzer |
| `step_id` | `string` | Auslösender Partner-Step |
| `step_order` | `integer` | Step-Reihenfolge für Anzeige und Auswertung |
| `status` | `enum` | Submission-Status, z. B. `submitted` |
| `created_at` | `datetime string` | Zeitpunkt der Einreichung |
| `partner_work_completed` | `boolean` | Kennzeichnet abgeschlossene Partnerarbeit |

### 4.6 File

Files speichern Metadaten zu Uploads. Binärdaten liegen im lokalen Storage.

| Feld | Datentyp | Kurzbeschreibung |
|---|---|---|
| `_id` | `ObjectId` | Eindeutige technische ID des Metadatensatzes |
| `id` | `uuid string` | Öffentliche File-ID für Download-Endpunkte |
| `user_id` | `string` | Datei-Owner |
| `storage_path` | `string` | Pfad im lokalen Object Storage |
| `original_filename` | `string` | Normalisierter Originaldateiname |
| `content_type` | `string` | MIME-Type der Datei |
| `size` | `integer` | Dateigröße in Bytes |
| `is_deleted` | `boolean` | Soft-Delete-Status |
| `created_at` | `datetime string` | Upload-Zeitpunkt |

## 5. Step Engine

### 5.1 Grundlogik

Steps werden nach `survey_id`, `is_active` und `order` geladen. Conditions
steuern Sichtbarkeit und Statusverhalten.

| Element | Werte / Typen | Kurzbeschreibung |
|---|---|---|
| Actions | `hide`, `block`, `auto_complete`, `redirect` | Steuern, ob Steps versteckt, gesperrt, automatisch abgeschlossen oder weitergeleitet werden |
| Operatoren | `equals`, `not_equals`, `contains`, `not_empty`, `empty`, `status_is`, `status_not`, `has_upload`, `missing_upload` | Vergleichen Feldwerte, Status oder Upload-Zustände |
| Compound Conditions | `all_of`, `any_of` | Kombinieren mehrere Bedingungen |
| Visibility | Hidden / visible | Hidden Steps werden aus Fortschritt und ETA herausgerechnet |
| Blocking | Blocked / editable | Blocked Steps bleiben sichtbar, sind aber noch nicht bearbeitbar |
| Auto-Complete | Meilenstein- oder Statusautomatik | Schließt Steps serverseitig ab, wenn Bedingungen erfüllt sind |

### 5.2 Typisches Muster

![Step Engine: typisches Muster](docs/charts/pflichtenheft-step-engine.png)

Das Muster zeigt eine generische Etappe, die in unterschiedlichen Surveys
wiederverwendet werden kann. Ein Decision-Step entscheidet, ob der Nutzer einen
Upload-Pfad oder einen Partner-Pfad nutzt. Der Upload-Pfad zeigt einen
Dokumenten-Step, der Partner-Pfad eine Partnerauswahl. Beide Pfade münden in
einen Meilenstein. Erst wenn der Meilenstein erfüllt ist, wird der nächste Block
freigeschaltet.

Anwendernahes Ärzte-Beispiel: In der Etappe "Antragstellung Approbation" kann
der Nutzer entscheiden, ob er die Unterlagen selbst hochlädt oder einen Partner
für die Antragstellung auswählt. Bei Selbstbearbeitung werden Dokumente wie
Urkunden, Nachweise oder Formulare abgefragt. Bei Partnernutzung wird ein
passender Dienstleister ausgewählt. Der Meilenstein "Übersicht Antragstellung
Approbation" wird abgeschlossen, wenn die erforderlichen Uploads oder die
Partnerfreigabe vorliegen.

### 5.3 Generische Survey-Ketten

Ein Survey besteht aus einer geordneten Kette von Steps. Die Kette kann linear
sein oder über Conditions alternative Pfade enthalten.

| Regel | Kurzbeschreibung |
|---|---|
| Survey-Scoping | Step-Orders und Conditions gelten innerhalb eines Surveys |
| Progress-Scoping | Progress wird immer mit `survey_id` gespeichert |
| Hidden Steps | Werden aus sichtbarem Fortschritt und ETA entfernt |
| Blocked Steps | Bleiben sichtbar, können aber noch nicht bearbeitet werden |
| Auto-Complete | Schließt Meilensteine ab, wenn Uploads, Partnerdaten oder Statusbedingungen erfüllt sind |
| Partnerauswahl | Erzeugt Partner Submissions und ermöglicht Partnerzugriff |

### 5.4 Beispielszenarien

| Szenario | Beispielhafte Etappen | Zweck |
|---|---|---|
| Ärzte | Persönliche Daten, Antragstellung Approbation, Fachsprachenprüfung, Gleichwertigkeitsprüfung, Kenntnisprüfung, Jobangebote, Weiterbildung | Anwendernahes Beispiel für Anerkennungs- und Vermittlungsprozesse |
| Pflegepersonal | Anerkennung Pflege, Sprachschule, Fachsprachenprüfung, Vorbereitungskurs Kenntnisprüfung, Kenntnisprüfung, Jobangebote | Zweites Beispiel zur Validierung der generischen Darstellbarkeit |

Beide Szenarien nutzen dieselben technischen Bausteine: Step-Typen, Conditions,
Uploads, Partnerauswahl, Meilensteine, Progress-Berechnung und rollenbasierte
Zugriffe.

## 6. Backend-Schnittstellen

Die folgende Tabelle beschreibt die wesentlichen API-Oberflächen. Rückgabetypen
sind fachlich zusammengefasst und nicht als vollständiges OpenAPI-Schema zu
verstehen.

| Bereich | Methode / Endpoint | Erwartete Parameter | Rückgabetyp | Kurzbeschreibung |
|---|---|---|---|---|
| Public | `GET /api/surveys/public` | Keine | `array<SurveySummary>` | Listet öffentlich aktive Surveys |
| Public | `GET /api/surveys/slug/{slug}` | Pfad: `slug` | `SurveyDetail` | Liefert Survey-Metadaten für Landing/Auth |
| Public | `GET /api/cms/home` | Optional Survey-/CMS-Kontext | `CMSContent` | Liefert CMS-Inhalte der Landingpage |
| Auth | `POST /api/auth/register` | Body: `email`, `password`, `name`, optional `survey_slug` | `AuthPayload` | Registriert Nutzer und initialisiert Progress für den Survey |
| Auth | `POST /api/auth/login` | Body: `email`, `password` | `AuthPayload` | Meldet Nutzer an und liefert Tokens/User-Payload |
| Auth | `GET /api/auth/me` | Auth-Token | `UserPayload` | Liefert aktuellen eingeloggten Nutzer |
| Auth | Passwort-Reset-Endpunkte | E-Mail, Reset-Token, neues Passwort | `StatusPayload` | Unterstützt Passwort-Vergessen- und Reset-Flows |
| User Steps | `GET /api/steps/bootstrap` | Query: optional `survey_slug`; Auth-Token | `StepsBootstrapPayload` | Initialer Sammelrequest für User-Dashboard |
| User Steps | `GET /api/steps` | Query: optional `survey_slug`; Auth-Token | `array<Step>` | Liefert aktive Steps des relevanten Surveys |
| User Steps | `GET /api/steps/progress` | Query: optional `survey_slug`; Auth-Token | `array<UserProgress>` | Liefert Progress des aktuellen Nutzers |
| User Steps | `GET /api/steps/visibility` | Auth-Token | `VisibilityPayload` | Liefert hidden/blocked Steps |
| User Steps | `PUT /api/steps/progress` | Body: `step_id`, `status`, `data`, optional `files` | `UserProgress` | Aktualisiert Step-Progress und triggert Auto-Completes |
| Partner | `GET /api/partner/submissions` | Partner-Auth | `array<PartnerSubmissionView>` | Listet aktive und abgeschlossene Partnerfälle |
| Partner | `GET /api/partner/other-users` | Partner-Auth | `array<UserSummary>` | Listet für Partner sichtbare weitere Nutzer |
| Partner | `GET /api/partner/insights` | Partner-Auth | `PartnerInsights` | Liefert Funnel-, Timeline- und Profilstatistiken |
| Partner | `GET /api/partner/users/{id}` | Pfad: `id`; Partner-Auth | `PartnerUserDetail` | Detailansicht eines berechtigten Nutzers |
| Partner | `PUT /api/partner/users/{id}/progress` | Pfad: `id`; Body: Progressdaten | `UserProgress` | Aktualisiert berechtigten Nutzerfortschritt |
| Partner-Auswahl | `POST /api/partners/submit` | Body: `partner_id`, `step_id`, optionale Profildaten | `PartnerSubmission` | Reicht Nutzer bei einem Partner ein |
| Partner-Auswahl | `POST /api/partners/submit-multi` | Body: mehrere `partner_ids`, `step_id` | `array<PartnerSubmission>` | Reicht Nutzer bei mehreren Partnern ein |
| Admin Surveys | `GET /api/admin/surveys` | Admin-Auth | `array<Survey>` | Listet Surveys für Admin-Verwaltung |
| Admin Surveys | `POST /api/admin/surveys` | Body: Survey-Felder | `Survey` | Erstellt neuen Survey |
| Admin Surveys | `PUT /api/admin/surveys/{survey_id}` | Pfad: `survey_id`; Body: Survey-Felder | `Survey` | Aktualisiert Survey |
| Admin Steps | `GET /api/admin/steps` | Query: `survey_id` oder `survey_slug`; Admin-Auth | `array<Step>` | Listet Steps survey-spezifisch |
| Admin Steps | `POST /api/admin/steps` | Body: Step-Felder inkl. `survey_id` | `Step` | Erstellt neuen Step |
| Admin Steps | `PUT /api/admin/steps/{step_id}` | Pfad: `step_id`; Body: Step-Felder | `Step` | Aktualisiert Step |
| Admin Steps | `POST /api/admin/steps/reorder` | Body: `step_ids`, optional `survey_id` | `StatusPayload` | Speichert Reihenfolge innerhalb eines Surveys |
| Admin Templates | `GET, POST, PUT, DELETE /api/admin/step-templates` | Template-Daten | `StepTemplate` / `StatusPayload` | Verwaltet Step-Templates |
| Admin Users | `GET, POST, PUT, DELETE /api/admin/users` | User-Daten, optional `survey_id` | `UserPayload` / `StatusPayload` | Verwaltet Nutzer und Survey-Zuweisung |
| Admin Partners | `GET, POST, PUT, DELETE /api/admin/partners` | Partner-Daten | `Partner` / `StatusPayload` | Verwaltet Partnerorganisationen |
| Admin E-Mail | `GET, PUT, POST /api/admin/email-templates` | Template-Key, HTML, Variablen | `EmailTemplate` / `PreviewPayload` | Verwaltet und rendert E-Mail-Vorlagen |
| Dateien | `POST /api/files/upload` | Multipart: `file`; Auth-Token | `FileMetadata` | Speichert Upload nach Sicherheitsprüfung |
| Dateien | `GET /api/files/{file_id}` | Pfad: `file_id`; Auth oder Download-Token | `binary` | Liefert Datei nur bei Berechtigung |

## 7. Frontend

### 7.1 Routen

| Route | Erwartete Parameter | Rückgabetyp / Ansicht | Kurzbeschreibung |
|---|---|---|---|
| `/` | Keine | Landing-Ansicht | Default-Landingpage oder Einstieg |
| `/login` | Keine | Auth-Ansicht | Login ohne expliziten Survey-Slug |
| `/register` | Keine | Auth-Ansicht | Registrierung mit Default- oder Fallback-Survey |
| `/s/:surveySlug` | URL: `surveySlug` | Survey-Landing | Survey-spezifische Landingpage, z. B. Pflege oder Ärzte |
| `/s/:surveySlug/login` | URL: `surveySlug` | Auth-Ansicht | Login im Kontext eines Surveys |
| `/s/:surveySlug/register` | URL: `surveySlug` | Auth-Ansicht | Registrierung mit Survey-Zuweisung |
| `/dashboard` | Auth-Session | UserDashboard | Nutzer-Journey für den dem User zugeordneten Survey |
| `/partner-dashboard` | Partner-Auth | PartnerDashboard | Partnerfälle, Completed Users und Insights |
| `/admin` | Admin-Auth | AdminDashboard | Verwaltung von Surveys, Steps, Nutzern, Partnern, CMS und E-Mails |

### 7.2 Kernseiten

| Seite | Erwartete Parameter | Rückgabetyp / Ansicht | Kurzbeschreibung |
|---|---|---|---|
| `Landing.js` | Optional `surveySlug` | React Page | Rendert Landing-Copy und CTA je Survey |
| `Auth.js` | Optional `surveySlug`, Modus Login/Register | React Page | Login und Registrierung, übergibt Survey-Slug an API |
| `UserDashboard.js` | Auth-User mit `survey_id` | React Page | Lädt Bootstrap-Daten und rendert Step-Journey |
| `PartnerDashboard.js` | Partner-User mit `partner_id` | React Page | Rendert Partnerlisten, Details, Uploads und Insights |
| `AdminDashboard.js` | Admin-User | React Page | Rendert Admin-Module für Survey-, Step- und Stammdatenpflege |

### 7.3 Frontend API Client

| Funktion | Erwartete Parameter | Rückgabetyp | Kurzbeschreibung |
|---|---|---|---|
| `authAPI.register` | `email`, `password`, `name`, optional `survey_slug` | `AuthPayload` | Registriert Nutzer im Survey-Kontext |
| `stepsAPI.getBootstrap` | Optional `surveySlug` | `StepsBootstrapPayload` | Lädt initiale User-Dashboard-Daten |
| `adminAPI.getSurveys` | Keine | `array<Survey>` | Lädt Survey-Liste für Admin |
| `adminAPI.getSteps` | `surveyId` | `array<Step>` | Lädt Steps eines Surveys |
| `adminAPI.reorderSteps` | `step_ids`, `survey_id` | `StatusPayload` | Speichert Step-Reihenfolge |
| `surveysAPI.listPublic` | Keine | `array<SurveySummary>` | Lädt öffentliche Surveys |
| `surveysAPI.getBySlug` | `slug` | `SurveyDetail` | Lädt Survey-Metadaten anhand Slug |

## 8. Rechte- und Sicherheitskonzept

### 8.1 Rollen

| Rolle | Zugriff |
|---|---|
| User | Eigener Survey, eigener Progress, eigene Dateien |
| Partner | Zugewiesene Nutzer, Partner-Submissions, berechtigte Dateien |
| Admin | Vollständige Verwaltung und Einsicht |

### 8.2 Sicherheitsmaßnahmen

- Tokenbasierte Authentifizierung.
- Rollenprüfung pro geschütztem Endpoint.
- Survey-Scoping für Steps und Progress.
- Upload-Extension- und Content-Type-Prüfung.
- Download-Autorisierung pro Datei.
- Audit-Logs für administrative Aktionen.
- Deployment-Anforderung: `JWT_SECRET` mindestens 32 Bytes.

## 9. Performance-Konzept

### 9.1 Umgesetzte Maßnahmen

| Maßnahme | Kurzbeschreibung |
|---|---|
| User Bootstrap | User-Dashboard lädt initial über `GET /api/steps/bootstrap` |
| Kontextbasierte Metriken | Completion und ETA werden aus bereits geladenem Step-/Progress-Kontext berechnet |
| Bulk-Metriken | Admin- und Partnerlisten vermeiden serielle N+1-Abfragen |
| Bulk-Partnerstatus | Partner-Arbeitsstatus wird für Nutzerlisten gebündelt berechnet |
| Step-Order-Profilzugriff | Partner-Insights und Listen lesen Stammdaten über `step_order=1` |
| Parallele Frontend-Loads | PartnerDashboard lädt unabhängige Ressourcen parallel |
| Admin Request Guard | AdminDashboard verhindert doppelte initiale Request-Batches |

### 9.2 MongoDB-Indizes

| Collection | Index | Zweck |
|---|---|---|
| `users` | `email` eindeutig | Login und Eindeutigkeit |
| `users` | `(role,survey_id)` | Admin-Listen und Survey-Filter |
| `users` | `partner_id` | Partner-User-Zuordnung |
| `users` | `(role,created_at)` | Sortierte Rollenlisten |
| `surveys` | `slug` eindeutig | Slug-Auflösung |
| `surveys` | `(is_active,is_default)` | Public- und Fallback-Auswahl |
| `steps` | `(survey_id,is_active,order)` | Survey-spezifische Step-Listen |
| `steps` | `(is_active,order)` | Legacy- und Fallback-Listen |
| `user_progress` | `(user_id,step_id)` eindeutig | Eindeutiger Progress pro Step |
| `user_progress` | `(user_id,survey_id)` | User-Dashboard und Survey-Scoping |
| `user_progress` | `(user_id,step_order)` | Profilzugriff über Order |
| `user_progress` | `(step_id,status)` | Statusauswertungen |
| `user_progress` | `(user_id,status,step_order)` | Fortschritt und ETA |
| `partner_submissions` | `(partner_id,user_id)` | Partnerlisten |
| `partner_submissions` | `(user_id,partner_id)` | Berechtigungsprüfung |
| `partner_submissions` | `(partner_id,created_at)` | Timeline und neue Anfragen |
| `files` | `id` eindeutig | Download-Endpunkt |
| `files` | `(user_id,created_at)` | Datei-Listen pro Nutzer |
| `partners` | `name` | Suche und Anzeige |
| `partners` | `(is_active,tags)` | Partner-Matching |
| `progress_history` | `(user_id,timestamp)` | Historie |
| `audit_logs` | `timestamp` | Audit-Anzeige |

## 10. Betrieb

### 10.1 Lokaler Start

```bash
docker compose up -d mongo backend
cd frontend
BROWSER=none HOST=0.0.0.0 PORT=3000 npm start
```

### 10.2 Kanonischen Datenstand herstellen

```bash
docker exec gerdoctor-backend python /app/backend/seed_baseline.py --force
docker restart gerdoctor-backend
```

Nur verifizieren:

```bash
docker exec gerdoctor-backend python /app/backend/seed_baseline.py --verify-only
```

### 10.3 Standard-Logins

| Rolle | Zugangsdaten |
|---|---|
| Admin | `admin@example.com / Admin123!` |
| Partner | `empfang@chrizz1001.de / Partner123!` |
| Alternativer Partner | `partner-example@chrizz1001.de / Partner123!` |

## 11. Tests

### 11.1 Backend ohne Browser-Suiten

```bash
docker exec -e REACT_APP_BACKEND_URL=http://localhost:8001 \
  gerdoctor-backend pytest -q tests \
  --ignore=tests/e2e_email_template_editor.py \
  --ignore=tests/e2e_flowbuilder.py \
  --ignore=tests/test_admin_survey_steps_e2e.py \
  --ignore=tests/test_landing_pages_e2e.py \
  --ignore=tests/test_e2e_step_walkthrough.py
```

### 11.2 Gezielte Performance- und Security-Suite

```bash
docker exec -e REACT_APP_BACKEND_URL=http://localhost:8001 \
  gerdoctor-backend pytest -q \
  tests/test_reload_performance.py \
  tests/test_file_access_security.py \
  tests/test_admin_user_survey_assignment.py \
  tests/test_partner_insights_alignment.py \
  tests/test_new_features_iter34.py \
  tests/test_partner_completed_users_split.py \
  tests/test_partner_milestone_complete.py
```

Letzter dokumentierter Stand: `24 passed`.

### 11.3 Relevante Testdateien

| Testdatei | Zweck |
|---|---|
| `backend/tests/test_multi_survey_auth.py` | Multi-Survey-Registrierung und Auth |
| `backend/tests/test_pflege_survey_steps.py` | Pflege-Beispielszenario |
| `backend/tests/test_reload_performance.py` | Reload-Hotpaths und Indizes |
| `backend/tests/test_file_access_security.py` | Upload- und Download-Sicherheit |
| `backend/tests/test_partner_insights_alignment.py` | Partner-Insights-Konsistenz |
| `backend/tests/test_partner_milestone_complete.py` | Partner-Meilenstein-Abschluss |
| `backend/tests/test_admin_user_survey_assignment.py` | Admin-Survey-Zuweisung |

## 12. Abgrenzungen und offene Punkte

- Survey-spezifische Spezialfelder für Registrierungen sind noch nicht final
  ausmodelliert.
- Survey-spezifische E-Mail-Texte müssen fachlich finalisiert werden.
- Partner-Tags und Upload-Anforderungen sollten je Survey fachlich geprüft und
  gegebenenfalls erweitert werden.
- Export/Import von Step-Konfigurationen ist Backlog.
- Webhooks und wöchentliche Insights-E-Mails sind Backlog.

## 13. Technische Abnahmekriterien

| Kriterium | Erwartung |
|---|---|
| Backend-Start | Backend startet ohne Fehler und legt erforderliche Indizes an |
| Seed | Baseline-Seed kann mit `--verify-only` validiert werden |
| Registrierung | Survey-spezifische URLs erzeugen Nutzer mit passendem Survey |
| User-Dashboard | Initialer Reload erfolgt über Bootstrap-Endpoint |
| Dateizugriff | Partner können nur berechtigte Dateien herunterladen |
| Upload-Sicherheit | Upload aktiver Inhalte wird abgelehnt |
| Admin-Step-Listen | Step-Listen werden survey-spezifisch geladen |
| Tests | Gezielte Performance-/Security-Suite besteht |

## 14. Produktionsbetrieb und Deployment

### 14.1 Zielarchitektur Produktion

| Komponente | Empfehlung | Kurzbeschreibung |
|---|---|---|
| Reverse Proxy | Nginx, Traefik oder vergleichbar | TLS-Terminierung, Routing, Request-Limits |
| Frontend | Statisches React-Build oder Node-basierter Webserver | Auslieferung der Weboberfläche |
| Backend | FastAPI/Uvicorn in Containerumgebung | API, Auth, Step Engine, Uploadlogik |
| Datenbank | MongoDB mit persistentem Volume oder Managed Service | Primäre Persistenz |
| Upload Storage | Persistenter Storage, optional S3-kompatibel erweiterbar | Ablage hochgeladener Dateien |
| Mail | SMTP-Provider oder Transaktionsmaildienst | Passwort-Reset und Benachrichtigungen |
| Monitoring | Prometheus/Grafana oder vergleichbar | Metriken, Health Checks, Alerts |
| Logging | Zentralisierte Logsammlung | Fehleranalyse und Audit-Unterstützung |

### 14.2 Umgebungsvariablen und Secrets

| Variable | Beispiel / Typ | Zweck | Sensitiv |
|---|---|---|---|
| `MONGO_URL` | `mongodb://mongo:27017` | Datenbankverbindung | Nein, sofern ohne Credentials |
| `DB_NAME` | `test_database` / Produktivname | Datenbankname | Nein |
| `JWT_SECRET` | Mindestens 32 zufällige Bytes | Signatur von Tokens | Ja |
| `FRONTEND_URL` | `https://example.org` | Linkgenerierung und CORS | Nein |
| `LOCAL_STORAGE_ROOT` | `/var/lib/app/uploads` | Upload-Speicherort | Nein |
| `MAX_UPLOAD_BYTES` | `20971520` | Upload-Limit, Standard 20 MB | Nein |
| SMTP-Host/User/Pass | Providerabhängig | E-Mail-Versand | Ja |

Secrets sind produktiv über Secret-Management der Zielplattform zu verwalten und
dürfen nicht im Git-Repository gespeichert werden.

### 14.3 Betriebs-SLAs als Standardannahme

| Kennzahl | Standardannahme |
|---|---|
| Verfügbarkeit | 99,5 % monatlich ohne angekündigte Wartung |
| Supportzeit | Werktags 09:00-17:00 Uhr |
| Kritischer Incident | Reaktion innerhalb von 4 Stunden |
| Hoher Incident | Reaktion innerhalb von 1 Arbeitstag |
| Normaler Incident | Reaktion innerhalb von 3 Arbeitstagen |
| RPO | 24 Stunden |
| RTO | 8 Stunden |
| Wartungsfenster | Nach Ankündigung außerhalb fachlicher Kernzeiten |

## 15. Rollen- und Rechtematrix

| Funktion / Ressource | User | Partner | Admin |
|---|---|---|---|
| Eigene Registrierung/Login | Lesen/Schreiben | Lesen/Schreiben | Lesen/Schreiben |
| Eigener Survey-Progress | Lesen/Schreiben | Kein Zugriff | Lesen/Schreiben |
| Eigene Dateien | Lesen/Schreiben | Kein Zugriff | Lesen |
| Zugeordnete Nutzer | Kein Zugriff | Lesen, teilweise Schreiben | Lesen/Schreiben |
| Dateien zugeordneter Nutzer | Kein Zugriff | Lesen bei Partnerbeziehung | Lesen |
| Partner-Submissions | Erzeugen über Partnerauswahl | Lesen/Bearbeiten eigener Partnerfälle | Lesen/Schreiben |
| Surveys | Kein Zugriff | Kein Zugriff | Lesen/Schreiben |
| Steps und Conditions | Kein Zugriff | Kein Zugriff | Lesen/Schreiben |
| Nutzerverwaltung | Kein Zugriff | Kein Zugriff | Lesen/Schreiben |
| Partnerverwaltung | Kein Zugriff | Eigene Profildaten eingeschränkt | Lesen/Schreiben |
| E-Mail-Vorlagen | Kein Zugriff | Kein Zugriff | Lesen/Schreiben |
| CMS / Landing-Inhalte | Kein Zugriff | Kein Zugriff | Lesen/Schreiben |
| Audit Logs | Kein Zugriff | Kein Zugriff | Lesen |

## 16. Datenschutz- und Sicherheitskonzept

### 16.1 Datenschutztechnik

| Thema | Umsetzung / Anforderung |
|---|---|
| Privacy by Design | Survey-Felder sind fachlich konfigurierbar und sollen nur erforderliche Daten erfassen |
| Privacy by Default | Neue Nutzer erhalten nur Zugriff auf den eigenen Survey-Kontext |
| Datenminimierung | Pflichtfelder werden je Survey fachlich begründet |
| Zweckbindung | Survey und Step-Kontext dokumentieren den fachlichen Zweck der Verarbeitung |
| Auskunft | Export personenbezogener Nutzerdaten ist als Betriebs-/Admin-Prozess vorzusehen |
| Löschung | Nutzer, Progress, Submissions und Uploads müssen nachvollziehbar löschbar sein |
| Protokollierung | Admin- und sicherheitsrelevante Aktionen werden auditierbar gespeichert |
| Aufbewahrung | Konkrete Fristen werden durch Auftraggeber vorgegeben |

### 16.2 Technische Sicherheitsmaßnahmen

| Maßnahme | Umsetzung / Ziel |
|---|---|
| Transportverschlüsselung | TLS 1.2 oder höher im Produktivbetrieb |
| Passwortschutz | Hashing im Backend; produktiv Rate-Limiting und starke Secrets |
| Token-Sicherheit | Signierte Tokens mit ausreichend starkem `JWT_SECRET` |
| Rollenprüfung | Backend prüft Rollen und Berechtigungen pro Endpoint |
| Dateizugriff | Owner, Admin oder berechtigter Partner; sonst Ablehnung |
| Upload-Filter | Extension-Allowlist, Content-Type-Blocklist, Größenlimit |
| Eingabevalidierung | Pydantic-Modelle und serverseitige Validierung |
| Audit | Admin-Aktionen und sicherheitsrelevante Vorgänge werden protokolliert |
| Dependency Management | Regelmäßige Prüfung und Aktualisierung von Abhängigkeiten |
| Backup-Schutz | Backups sind vor unberechtigtem Zugriff zu schützen |

### 16.3 Barrierefreiheit

| Anforderung | Umsetzung / Nachweis |
|---|---|
| Zielstandard | WCAG 2.1 AA / EN 301 549 als Standardannahme |
| Tastaturbedienung | Interaktive Elemente müssen per Tastatur erreichbar sein |
| Kontraste | Farbkontraste nach WCAG AA |
| Semantik | Formularlabels, Überschriftenstruktur und ARIA nur bei Bedarf |
| Fehlermeldungen | Verständliche, lokalisierbare Validierungs- und Fehlermeldungen |
| Nachweis | Accessibility-Audit oder Stichprobentest mit dokumentierten Ergebnissen |

## 17. Monitoring, Logging und Backup

### 17.1 Monitoring

| Signal | Ziel |
|---|---|
| API Health Check | Verfügbarkeit des Backends prüfen |
| Datenbankverbindung | MongoDB-Erreichbarkeit überwachen |
| Antwortzeiten | Performance-Hotpaths überwachen |
| Fehlerraten | 4xx/5xx-Raten erkennen |
| Speicherverbrauch | Upload-Storage und Datenbankvolumen überwachen |
| Login-/Auth-Fehler | Auffällige Authentifizierungsversuche erkennen |

### 17.2 Logging

| Logtyp | Inhalt | Aufbewahrung Standardannahme |
|---|---|---|
| Application Logs | Fehler, Warnungen, technische Ereignisse | 30-90 Tage |
| Audit Logs | Admin- und sicherheitsrelevante Aktionen | 180-365 Tage |
| Access Logs | HTTP-Zugriffe, Statuscodes, Latenzen | 30-90 Tage |
| Security Logs | Auth-Fehler, Zugriffsablehnungen, Upload-Ablehnungen | 180 Tage |

Konkrete Aufbewahrungsfristen sind durch den Auftraggeber datenschutzrechtlich
festzulegen.

### 17.3 Backup und Restore

| Objekt | Intervall | Aufbewahrung | Restore-Ziel |
|---|---|---|---|
| MongoDB | Täglich | 14-30 Tage | RPO 24 h |
| Upload Storage | Täglich inkrementell | 14-30 Tage | RPO 24 h |
| Konfiguration/Secrets | Nach Änderung | Versioniert im Secret-/Config-System | Wiederherstellung der Umgebung |
| Restore-Test | Quartalsweise oder vor Go-live | Protokolliert | RTO 8 h |

## 18. Test- und Abnahmekonzept

| Testart | Umfang | Nachweis |
|---|---|---|
| Unit-/Integrationstests | Backend-Logik, Step Engine, Partner- und Adminfunktionen | Pytest-Protokoll |
| Security-Regression | Upload-Filter, Dateizugriff, Rollenprüfung | Testprotokoll |
| Performance-Test | Dashboard-Hotpaths, Admin-/Partnerlisten | Laufzeitmessung |
| E2E-Test | Login, Survey-Flow, Admin-Step-Verwaltung, Landingpages | Playwright-Protokoll |
| Accessibility-Test | Tastatur, Kontrast, Labels, Semantik | Audit-Checkliste |
| Abnahmetest | Muss-Anforderungen und Beispielszenarien Ärzte/Pflege | Abnahmeprotokoll |

## 19. Migration, Wartung und Support

### 19.1 Migration

| Thema | Vorgehen |
|---|---|
| Bestandsdaten | Vor Migration sichern und mit Skripten idempotent migrieren |
| Survey-Zuordnung | Nutzer, Steps und Progress erhalten `survey_id` / `survey_slug` |
| Uploads | Metadaten und Binärdaten gemeinsam sichern und wiederherstellen |
| Rollback | Backup-Restore und Rückkehr auf vorherigen Containerstand |
| Baseline | Lokaler Referenzstand über `backend/seed_baseline.py` reproduzierbar |

### 19.2 Wartung und Support

| Leistung | Standardannahme |
|---|---|
| Fehlerbehebung kritisch | Reaktion innerhalb 4 Stunden während Supportzeit |
| Fehlerbehebung hoch | Reaktion innerhalb 1 Arbeitstag |
| Fehlerbehebung normal | Reaktion innerhalb 3 Arbeitstagen |
| Sicherheitsupdates | Zeitnah nach Bewertung, kritisch innerhalb 7 Tagen |
| Feature-Updates | Nach Change Request und Freigabe |
| Dokumentationspflege | Bei relevanten Änderungen |

## 20. Ausschreibungsannahmen

| Thema | Annahme | Zu bestätigen |
|---|---|---|
| Hosting | Containerfähige Linux-Umgebung mit persistentem Storage | Auftraggeber |
| Datenbank | MongoDB lokal oder Managed MongoDB-kompatibel | Auftraggeber |
| Mailversand | SMTP-/Transaktionsmaildienst wird bereitgestellt | Auftraggeber |
| Datenschutz | Zwecke, Rechtsgrundlagen und Löschfristen werden beigestellt | Auftraggeber |
| Barrierefreiheit | WCAG 2.1 AA / EN 301 549 als Zielstandard | Auftraggeber |
| Mengengerüst | 10.000 Nutzer, 50 Surveys, 100 gleichzeitige Sessions als Startannahme | Auftraggeber |
| Support | Werktags 09:00-17:00 Uhr | Auftraggeber |
| Abnahme | Abnahme anhand Muss-Anforderungen, Tests und Beispielszenarien | Auftraggeber |
