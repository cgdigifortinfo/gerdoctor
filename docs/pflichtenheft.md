# Pflichtenheft

## Deckblatt

| Feld | Inhalt |
|---|---|
| Projekt | IHCA Multi-Survey-Plattform |
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
- [21. Partnerregistrierung und Billing-Erweiterung](#21-partnerregistrierung-und-billing-erweiterung)
- [22. Nutzerrechte und Nutzergruppen](#22-nutzerrechte-und-nutzergruppen)

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
| Datenbank | MongoDB | Persistenz für Nutzer, Surveys, Steps, Progress, Partner, Dateien, Billing Events |
| Frontend | React / CRACO | Single Page Application mit User-, Partner- und Admin-Dashboard |
| Betrieb | Docker Compose | Lokaler Betrieb von MongoDB und Backend |
| Uploads | Lokaler Object Storage | Persistente Ablage von Upload-Dateien über Docker-Volume |
| Payment Provider | Stripe als Beispiel, provider-neutral abstrahiert | Partner-Abo, Checkout, Webhooks und nutzungsbezogene Abrechnung |
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
| `group_ids` | `array<string>` | Zugeordnete Nutzergruppen für erweiterte Rechte |
| `permission_overrides` | `object` | Explizite nutzerbezogene Rechteabweichungen |
| `survey_id` | `string` / `null` | Zugeordneter Survey für normale Nutzer |
| `survey_slug` | `string` / `null` | Lesbarer Survey-Schlüssel |
| `partner_id` | `string` / `null` | Zugeordnete Partnerorganisation bei Partner-Usern |
| `notification_prefs` | `object` | Benachrichtigungseinstellungen, z. B. E-Mail Opt-out |
| `created_at` | `datetime string` | Erstellzeitpunkt |
| `updated_at` | `datetime string` | Letzte Änderung |

### 4.2.1 User Group

User Groups bündeln Berechtigungen und können Nutzern ergänzend zur Basisrolle
zugewiesen werden.

| Feld | Datentyp | Kurzbeschreibung |
|---|---|---|
| `_id` | `ObjectId` | Eindeutige technische ID |
| `name` | `string` | Anzeigename der Gruppe, z. B. Fachadmin oder Abrechnung |
| `description` | `string` | Kurzbeschreibung des Einsatzzwecks |
| `scope` | `enum` | Geltungsbereich: global, survey-spezifisch oder partner-spezifisch |
| `survey_ids` | `array<string>` | Optionale Survey-Einschränkung |
| `partner_ids` | `array<string>` | Optionale Partner-Einschränkung |
| `permissions` | `array<string>` | Zugeordnete Berechtigungsschlüssel |
| `is_active` | `boolean` | Aktivierungsstatus |
| `created_at` | `datetime string` | Erstellzeitpunkt |
| `updated_at` | `datetime string` | Letzte Änderung |

### 4.2.2 Permission Audit

Permission Audits dokumentieren Änderungen an Gruppen, Mitgliedschaften und
Rechte-Overrides.

| Feld | Datentyp | Kurzbeschreibung |
|---|---|---|
| `_id` | `ObjectId` | Eindeutige technische ID |
| `actor_user_id` | `string` | Auslösender Admin oder Systemnutzer |
| `target_user_id` | `string` / `null` | Betroffener Nutzer bei Mitgliedschafts- oder Override-Änderung |
| `group_id` | `string` / `null` | Betroffene Gruppe |
| `action` | `enum` | `group_created`, `group_updated`, `member_added`, `member_removed`, `override_changed` |
| `before` | `object` / `null` | Vorheriger Zustand |
| `after` | `object` / `null` | Neuer Zustand |
| `created_at` | `datetime string` | Änderungszeitpunkt |

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
| `billing_event_id` | `string` / `null` | Referenz auf erzeugtes Billing Event bei abrechnungsrelevantem Abschluss |

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

### 4.7 Partner Account

Partner Accounts erweitern Partnerorganisationen um Registrierungs-, Prüf- und
Zahlungsstatus. Bestehende Partner-Stammdaten können technisch in derselben
Collection oder in einer ergänzenden Collection gespeichert werden.

| Feld | Datentyp | Kurzbeschreibung |
|---|---|---|
| `_id` | `ObjectId` | Eindeutige technische ID |
| `partner_id` | `string` | Referenz auf Partnerorganisation |
| `company_name` | `string` | Name der Organisation |
| `contact_name` | `string` | Ansprechpartner |
| `contact_email` | `string` | E-Mail für Registrierung, Login und Abrechnung |
| `registration_status` | `enum` | Status: `pending`, `approved`, `rejected`, `suspended` |
| `billing_status` | `enum` | Status: `none`, `checkout_pending`, `active`, `past_due`, `canceled`, `unpaid` |
| `stripe_customer_id` | `string` / `null` | Stripe Customer ID als Beispielanbieterreferenz |
| `stripe_subscription_id` | `string` / `null` | Stripe Subscription ID |
| `billing_email` | `string` | E-Mail für Rechnungs- und Zahlungsinformationen |
| `created_at` | `datetime string` | Registrierungszeitpunkt |
| `updated_at` | `datetime string` | Letzte Änderung |

### 4.8 Partner Subscription

Partner Subscriptions speichern den lokalen Abo-Zustand unabhängig vom konkreten
Zahlungsanbieter.

| Feld | Datentyp | Kurzbeschreibung |
|---|---|---|
| `_id` | `ObjectId` | Eindeutige technische ID |
| `partner_id` | `string` | Referenz auf Partnerorganisation |
| `provider` | `enum` | Zahlungsanbieter, z. B. `stripe` |
| `provider_customer_id` | `string` | Customer-ID beim Zahlungsanbieter |
| `provider_subscription_id` | `string` | Subscription-ID beim Zahlungsanbieter |
| `plan_id` | `string` | Interner Tarif oder Preisplan |
| `status` | `enum` | `incomplete`, `trialing`, `active`, `past_due`, `unpaid`, `canceled` |
| `current_period_start` | `datetime string` | Beginn der aktuellen Abrechnungsperiode |
| `current_period_end` | `datetime string` | Ende der aktuellen Abrechnungsperiode |
| `cancel_at_period_end` | `boolean` | Kündigung zum Periodenende vorgemerkt |
| `created_at` | `datetime string` | Erstellzeitpunkt |
| `updated_at` | `datetime string` | Letzte Synchronisierung |

### 4.9 Billing Event

Billing Events sind die interne, revisionsfähige Grundlage der Abrechnung pro
abgeschlossenem Nutzer-Meilenstein.

| Feld | Datentyp | Kurzbeschreibung |
|---|---|---|
| `_id` | `ObjectId` | Eindeutige technische ID |
| `event_key` | `string` | Idempotenzschlüssel, z. B. `partner_id:user_id:step_id` |
| `partner_id` | `string` | Abzurechnender Partner |
| `user_id` | `string` | Nutzer, dessen Meilenstein abgeschlossen wurde |
| `survey_id` | `string` | Zugehöriger Survey |
| `step_id` | `string` | Abrechnungsrelevanter Meilenstein |
| `step_order` | `integer` | Step-Reihenfolge |
| `milestone_title` | `string` | Anzeigename des Meilensteins |
| `amount_net` | `integer` | Nettobetrag in kleinster Währungseinheit, z. B. Cent |
| `currency` | `string` | Währung, z. B. `EUR` |
| `status` | `enum` | `pending`, `reported`, `invoiced`, `paid`, `void`, `error` |
| `provider` | `string` / `null` | Zahlungsanbieterreferenz, z. B. `stripe` |
| `provider_usage_record_id` | `string` / `null` | Referenz auf Usage-/Metering-Event beim Anbieter |
| `billing_period` | `string` | Abrechnungsperiode, z. B. `2026-07` |
| `completed_at` | `datetime string` | Zeitpunkt des fachlichen Abschlusses |
| `created_at` | `datetime string` | Erzeugungszeitpunkt |

### 4.10 Payment Provider Event

Payment Provider Events speichern eingehende Webhooks, damit Verarbeitung
idempotent und nachvollziehbar bleibt.

| Feld | Datentyp | Kurzbeschreibung |
|---|---|---|
| `_id` | `ObjectId` | Eindeutige technische ID |
| `provider` | `string` | Zahlungsanbieter, z. B. `stripe` |
| `provider_event_id` | `string` | Eindeutige Event-ID des Anbieters |
| `event_type` | `string` | Webhook-Typ, z. B. `checkout.session.completed` |
| `payload` | `object` | Signiert empfangener Webhook-Payload |
| `processing_status` | `enum` | `received`, `processed`, `ignored`, `failed` |
| `error_message` | `string` / `null` | Fehlerdetails bei Verarbeitung |
| `received_at` | `datetime string` | Empfangszeitpunkt |
| `processed_at` | `datetime string` / `null` | Verarbeitungszeitpunkt |

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
| Billing Event | Erzeugt bei abrechnungsrelevantem Partner-Meilenstein genau ein idempotentes Abrechnungsereignis |

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
| Auth | `GET /api/auth/permissions` | Auth-Token | `EffectivePermissions` | Liefert effektive Rechte aus Rolle, Gruppen und Overrides |
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
| Partner Billing | `GET /api/partner/billing/summary` | Partner-Auth; optional Zeitraum | `PartnerBillingSummary` | Zeigt eigene Umsätze, Abschlüsse und offene Beträge |
| Partner Billing | `GET /api/partner/billing/events` | Partner-Auth; Filter: Zeitraum, Status, Survey | `array<BillingEvent>` | Listet eigene abrechnungsrelevante Meilensteine |
| Partner Billing | `GET /api/partner/billing/subscription` | Partner-Auth | `PartnerSubscription` | Liefert lokalen Abo- und Zahlungsstatus |
| Partner Billing | `POST /api/partners/register` | Body: Organisations-, Kontakt- und Rechnungsdaten | `PartnerRegistrationPayload` | Registriert neue Partnerorganisation mit Prüfstatus |
| Partner Billing | `POST /api/partners/billing/checkout-session` | Body: `partner_id`, Tarif/Plan | `CheckoutSessionPayload` | Erstellt Checkout Session beim Zahlungsanbieter |
| Partner Billing | `POST /api/webhooks/stripe` | Signierter Stripe-Payload | `StatusPayload` | Verarbeitet Provider-Events idempotent |
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
| Admin Access | `GET /api/admin/user-groups` | Admin-Auth | `array<UserGroup>` | Listet Nutzergruppen und Berechtigungsprofile |
| Admin Access | `POST /api/admin/user-groups` | Body: Gruppenfelder und Berechtigungen | `UserGroup` | Erstellt neue Nutzergruppe |
| Admin Access | `PUT /api/admin/user-groups/{id}` | Pfad: `id`; Body: Gruppenfelder | `UserGroup` | Aktualisiert Gruppe, Scope und Berechtigungen |
| Admin Access | `POST /api/admin/users/{id}/groups` | Pfad: `id`; Body: `group_ids` | `UserPayload` | Setzt Gruppenmitgliedschaften eines Nutzers |
| Admin Access | `PUT /api/admin/users/{id}/permission-overrides` | Pfad: `id`; Body: Overrides | `UserPayload` | Setzt explizite nutzerbezogene Rechteabweichungen |
| Admin Access | `GET /api/admin/permission-audit` | Filter: Nutzer, Gruppe, Zeitraum | `array<PermissionAudit>` | Zeigt Audit-Historie für Rechteänderungen |
| Admin Partners | `GET, POST, PUT, DELETE /api/admin/partners` | Partner-Daten | `Partner` / `StatusPayload` | Verwaltet Partnerorganisationen |
| Admin Billing | `GET /api/admin/billing/summary` | Admin-Auth; Filter: Zeitraum, Partner, Status | `AdminBillingSummary` | Aggregiert Abrechnungen über alle Partner |
| Admin Billing | `GET /api/admin/billing/events` | Admin-Auth; Filter: Zeitraum, Partner, Status, Survey | `array<BillingEvent>` | Listet alle Billing Events mit Partnerbezug |
| Admin Billing | `GET /api/admin/billing/export` | Admin-Auth; Filter wie Übersicht | `file` | Exportiert Abrechnungsdaten als CSV/XLSX |
| Admin Billing | `POST /api/admin/billing/events/{id}/void` | Pfad: `id`; Body: Begründung | `BillingEvent` | Storniert ein Billing Event revisionsfähig |
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
| `/partner/register` | Keine oder Referral-/Plan-Parameter | PartnerRegister | Öffentliche Partnerregistrierung |
| `/partner/billing/checkout` | Partnerkontext, Plan | Checkout-Redirect/Status | Startet oder prüft Abo-Checkout beim Zahlungsanbieter |
| `/dashboard` | Auth-Session | UserDashboard | Nutzer-Journey für den dem User zugeordneten Survey |
| `/partner-dashboard` | Partner-Auth | PartnerDashboard | Partnerfälle, Completed Users, Insights und Billing-Einstieg |
| `/partner-dashboard/billing` | Partner-Auth | PartnerBillingPage | Eigene Umsätze, Abschlüsse, Abo-Status und Export |
| `/admin` | Admin-Auth | AdminDashboard | Verwaltung von Surveys, Steps, Nutzern, Partnern, Billing, CMS und E-Mails |
| `/admin/access-control` | Admin-Auth mit Rechteverwaltung | AccessControlPage | Verwaltung von Nutzergruppen, Berechtigungen und Overrides |
| `/admin/billing` | Admin-Auth | AdminBillingPage | Globale Abrechnungsübersicht über alle Partner |

### 7.2 Kernseiten

| Seite | Erwartete Parameter | Rückgabetyp / Ansicht | Kurzbeschreibung |
|---|---|---|---|
| `Landing.js` | Optional `surveySlug` | React Page | Rendert Landing-Copy und CTA je Survey |
| `Auth.js` | Optional `surveySlug`, Modus Login/Register | React Page | Login und Registrierung, übergibt Survey-Slug an API |
| `PartnerRegister.js` | Organisations-, Kontakt- und Rechnungsdaten | React Page | Registriert Partner und führt zum Abo-Checkout |
| `UserDashboard.js` | Auth-User mit `survey_id` | React Page | Lädt Bootstrap-Daten und rendert Step-Journey |
| `PartnerDashboard.js` | Partner-User mit `partner_id` | React Page | Rendert Partnerlisten, Details, Uploads und Insights |
| `PartnerBillingPage.js` | Partner-User mit `partner_id` | React Page | Rendert eigene Billing-Kennzahlen, Ereignisse und Abo-Status |
| `AdminDashboard.js` | Admin-User | React Page | Rendert Admin-Module für Survey-, Step-, Billing- und Stammdatenpflege |
| `AccessControlPage.js` | Admin-User mit Rechteverwaltung | React Page | Rendert Gruppen, Berechtigungsprofile, Mitgliedschaften und Audit-Historie |
| `AdminBillingPage.js` | Admin-User | React Page | Rendert globale Partnerabrechnungen, Filter, Storno und Export |

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
| `authAPI.getPermissions` | Keine | `EffectivePermissions` | Lädt effektive Rechte für UI-Gating |
| `adminAccessAPI.getGroups` | Filter optional | `array<UserGroup>` | Lädt Nutzergruppen und Berechtigungsprofile |
| `adminAccessAPI.updateUserGroups` | `userId`, `group_ids` | `UserPayload` | Speichert Gruppenmitgliedschaften |
| `adminAccessAPI.updatePermissionOverrides` | `userId`, Overrides | `UserPayload` | Speichert nutzerbezogene Rechteabweichungen |
| `partnerBillingAPI.getSummary` | Zeitraum/Filter | `PartnerBillingSummary` | Lädt eigene Umsatz- und Abschlussübersicht |
| `partnerBillingAPI.createCheckoutSession` | `partner_id`, Plan | `CheckoutSessionPayload` | Startet Abo-Buchung beim Zahlungsanbieter |
| `adminBillingAPI.getSummary` | Zeitraum, Partner, Status | `AdminBillingSummary` | Lädt globale Abrechnungskennzahlen |
| `adminBillingAPI.export` | Zeitraum, Partner, Status | `file` | Exportiert Abrechnungsdaten |

## 8. Rechte- und Sicherheitskonzept

### 8.1 Rollen

| Rolle | Zugriff |
|---|---|
| User | Eigener Survey, eigener Progress, eigene Dateien |
| Partner | Zugewiesene Nutzer, Partner-Submissions, berechtigte Dateien |
| Admin | Vollständige Verwaltung und Einsicht |
| Sondergruppen | Erweiterte oder eingeschränkte Rechte gemäß Gruppenprofil und Scope |

Effektive Berechtigungen werden aus Basisrolle, aktiven Nutzergruppen,
Scope-Regeln und nutzerbezogenen Overrides berechnet. Die Backend-Prüfung ist
führend; Frontend-Gating dient nur der Bedienbarkeit.

### 8.2 Sicherheitsmaßnahmen

- Tokenbasierte Authentifizierung.
- Rollenprüfung pro geschütztem Endpoint.
- Berechtigungsprüfung pro geschütztem Endpoint auf Basis effektiver Rechte.
- Scope-Prüfung für Survey-, Partner- und Billing-Kontexte.
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
| `users` | `group_ids` | Gruppenbasierte Nutzerfilter |
| `users` | `(role,created_at)` | Sortierte Rollenlisten |
| `user_groups` | `name` eindeutig | Eindeutige Gruppenverwaltung |
| `user_groups` | `(is_active,scope)` | Effektive Rechteberechnung |
| `permission_audits` | `(target_user_id,created_at)` | Audit-Historie je Nutzer |
| `permission_audits` | `(group_id,created_at)` | Audit-Historie je Gruppe |
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
| `billing_events` | `event_key` eindeutig | Verhindert Doppelabrechnung pro Partner/User/Step |
| `billing_events` | `(partner_id,billing_period,status)` | Partner- und Periodenübersichten |
| `billing_events` | `(survey_id,step_id,completed_at)` | Milestone-Auswertungen |
| `partner_subscriptions` | `(partner_id,status)` | Abo-Statusprüfung |
| `payment_provider_events` | `(provider,provider_event_id)` eindeutig | Webhook-Idempotenz |

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
| `backend/tests/test_access_control.py` | Effektive Rechte, Gruppenmitgliedschaften und Overrides |

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
| Rechteverwaltung | Gruppen, Mitgliedschaften, Overrides und Audit Logs funktionieren konsistent |

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
| `PAYMENT_PROVIDER` | `stripe` | Aktivierter Zahlungsanbieter | Nein |
| `STRIPE_SECRET_KEY` | Stripe Secret Key | API-Zugriff auf Stripe | Ja |
| `STRIPE_WEBHOOK_SECRET` | Stripe Signing Secret | Webhook-Signaturprüfung | Ja |
| `STRIPE_PARTNER_PLAN_PRICE_ID` | Stripe Price ID | Abo-Tarif für Partner | Nein |
| `MILESTONE_BILLING_PRICE_ID` | Stripe Price/Meter ID | Abrechnung abgeschlossener Meilensteine | Nein |

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
| Nutzergruppen | Kein Zugriff | Kein Zugriff | Lesen/Schreiben bei Admin-Recht `access.manage` |
| Berechtigungsprofile | Kein Zugriff | Kein Zugriff | Lesen/Schreiben bei Admin-Recht `access.manage` |
| Rechte-Audit | Kein Zugriff | Kein Zugriff | Lesen bei Admin-Recht `audit.read` |
| Partnerregistrierung | Kein Zugriff | Erzeugen vor Login/Freigabe | Lesen/Schreiben |
| Partner-Abo | Kein Zugriff | Eigenen Status lesen, Checkout starten | Lesen/Schreiben |
| Partner-Umsätze | Kein Zugriff | Eigene Umsätze lesen/exportieren | Lesen/Export |
| Billing Events | Kein Zugriff | Eigene Ereignisse lesen | Lesen/Schreiben/Storno |
| Zahlungsanbieter-Daten | Kein Zugriff | Keine Zahlungsinstrumentdaten | Providerstatus lesen, keine Karten speichern |
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
| Zahlungsdaten | Zahlungsinstrumentdaten werden nicht lokal gespeichert; Speicherung erfolgt beim Zahlungsanbieter |

### 16.2 Technische Sicherheitsmaßnahmen

| Maßnahme | Umsetzung / Ziel |
|---|---|
| Transportverschlüsselung | TLS 1.2 oder höher im Produktivbetrieb |
| Passwortschutz | Hashing im Backend; produktiv Rate-Limiting und starke Secrets |
| Token-Sicherheit | Signierte Tokens mit ausreichend starkem `JWT_SECRET` |
| Rollenprüfung | Backend prüft Rollen und Berechtigungen pro Endpoint |
| Effektive Rechte | Backend berechnet Rechte aus Rolle, Gruppen, Scope und Overrides |
| Rechte-Audit | Änderungen an Gruppen, Mitgliedschaften und Overrides werden revisionsfähig protokolliert |
| Dateizugriff | Owner, Admin oder berechtigter Partner; sonst Ablehnung |
| Upload-Filter | Extension-Allowlist, Content-Type-Blocklist, Größenlimit |
| Eingabevalidierung | Pydantic-Modelle und serverseitige Validierung |
| Webhook-Sicherheit | Stripe-Signaturprüfung und eindeutige Provider-Event-ID verhindern Replay-/Doppelverarbeitung |
| Billing-Zugriff | Partner sehen ausschließlich eigene Billing Events; Admin sieht mandantenübergreifend |
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
| Rechteänderungen | Ungewöhnliche Gruppen- oder Berechtigungsänderungen erkennen |
| Payment Webhooks | Fehler, Replay-Versuche und Verzögerungen bei Zahlungsanbieter-Events erkennen |
| Billing Events | Ausstehende, fehlerhafte oder stornierte Abrechnungsereignisse überwachen |

### 17.2 Logging

| Logtyp | Inhalt | Aufbewahrung Standardannahme |
|---|---|---|
| Application Logs | Fehler, Warnungen, technische Ereignisse | 30-90 Tage |
| Audit Logs | Admin- und sicherheitsrelevante Aktionen | 180-365 Tage |
| Access Logs | HTTP-Zugriffe, Statuscodes, Latenzen | 30-90 Tage |
| Security Logs | Auth-Fehler, Zugriffsablehnungen, Upload-Ablehnungen | 180 Tage |
| Billing Logs | Webhook-Verarbeitung, Providerfehler, Billing-Statuswechsel | 180-365 Tage |

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
| Billing-Test | Partnerregistrierung, Checkout, Webhooks, Idempotenz, Partner-/Adminübersicht | Testprotokoll |
| Access-Control-Test | Gruppen, effektive Rechte, Overrides, Scope-Regeln und Audit Logs | Testprotokoll |
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
| Billing-Daten | Partner-Subscriptions, Billing Events und Provider-Event-IDs werden idempotent migriert |

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
| Zahlungsanbieter | Stripe-Test- und Produktivkonto mit Preis-/Meter-Konfiguration wird bereitgestellt | Auftraggeber |
| Abrechnungsmodell | Standardannahme: aktives Partner-Abo plus Abrechnung pro abgeschlossenem Nutzer-Meilenstein | Auftraggeber |
| Datenschutz | Zwecke, Rechtsgrundlagen und Löschfristen werden beigestellt | Auftraggeber |
| Barrierefreiheit | WCAG 2.1 AA / EN 301 549 als Zielstandard | Auftraggeber |
| Mengengerüst | 10.000 Nutzer, 50 Surveys, 100 gleichzeitige Sessions als Startannahme | Auftraggeber |
| Support | Werktags 09:00-17:00 Uhr | Auftraggeber |
| Abnahme | Abnahme anhand Muss-Anforderungen, Tests und Beispielszenarien | Auftraggeber |

## 21. Partnerregistrierung und Billing-Erweiterung

### 21.1 Betroffene Softwarebereiche

| Bereich | Erweiterung |
|---|---|
| Public Frontend | Neue Partnerregistrierungsseite und Einstieg in den Abo-Checkout |
| Auth/Rollen | Anlage oder Freigabe von Partner-Usern mit Zahlungs-/Registrierungsstatus |
| Partner-Modul | Abo-Status, Umsätze, abrechnungsrelevante Abschlüsse und Exportansicht |
| Admin-Modul | Globale Abrechnungsübersicht, Filter, Storno, Export und Providerstatus |
| Step Engine | Markierung abrechnungsrelevanter Partner-Meilensteine |
| Partner Milestones | Erzeugung idempotenter Billing Events bei Abschluss |
| Payment Provider | Stripe Checkout, Subscriptions, Webhooks und optional usage-based Billing als Beispiel |
| Datenmodell | Partner Account, Partner Subscription, Billing Event, Payment Provider Event |
| E-Mail | Benachrichtigungen zu Registrierung, Abo-Status, Zahlungsproblemen und Abrechnung |
| Tests | Webhook-Idempotenz, Doppelabrechnungsschutz, Rollenrechte und Reporting |

### 21.2 Stripe-Beispielintegration

Stripe wird als Beispielanbieter verwendet. Die technische Umsetzung soll über
eine Provider-Abstraktion erfolgen, damit ein alternativer Zahlungsanbieter
später angebunden werden kann.

| Stripe-Baustein | Einsatz im System |
|---|---|
| Checkout Session | Partner startet Abo-Buchung über gehostete Zahlungsseite |
| Customer | Partnerorganisation wird als Customer beim Zahlungsanbieter geführt |
| Subscription | Aktiver oder inaktiver Abo-Status des Partners |
| Invoice | Zahlungs- und Rechnungsstatus für Abo und nutzungsabhängige Abrechnung |
| Webhook Event | Synchronisiert Checkout-, Subscription-, Invoice- und Payment-Status |
| Usage-based Billing / Metering | Beispielhafte Abbildung abgeschlossener Meilensteine als abrechenbare Nutzung |

### 21.3 Fachlicher Billing-Ablauf

| Schritt | Systemverhalten |
|---|---|
| 1. Partnerregistrierung | Partner gibt Organisations-, Kontakt- und Rechnungsdaten ein |
| 2. Prüfung/Freigabe | Partner erhält Status `pending` oder wird automatisch/administrativ freigegeben |
| 3. Abo-Checkout | System erstellt Checkout Session beim Zahlungsanbieter |
| 4. Webhook-Synchronisierung | Erfolgreicher Checkout setzt Subscription auf `active` |
| 5. Partnerarbeit | Partner bearbeitet zugeordnete Nutzer und schließt Meilensteine ab |
| 6. Billing Event | Abrechnungsrelevanter Abschluss erzeugt ein eindeutiges Billing Event |
| 7. Provider-Meldung | Billing Event wird an Stripe/Provider als Nutzung oder Rechnungsposition übertragen |
| 8. Reporting | Partner und Admin sehen Umsätze, Status, Perioden und Einzelereignisse |

### 21.4 Idempotenz- und Konsistenzregeln

| Regel | Beschreibung |
|---|---|
| Eindeutiger Event-Key | Pro `partner_id`, `user_id`, `step_id` darf nur ein aktives Billing Event entstehen |
| Webhook-Idempotenz | `provider_event_id` wird eindeutig gespeichert; wiederholte Webhooks werden ignoriert |
| Statusübergänge | Billing Events wechseln kontrolliert zwischen `pending`, `reported`, `invoiced`, `paid`, `void`, `error` |
| Storno | Admin kann Billing Events mit Begründung auf `void` setzen |
| Nachvollziehbarkeit | Partner- und Adminübersicht zeigen dieselbe Datengrundlage mit rollenabhängigem Scope |
| Kein lokaler Kartenbestand | Zahlungsinstrumentdaten verbleiben beim Zahlungsanbieter |

### 21.5 Abnahmekriterien Billing

| Kriterium | Erwartung |
|---|---|
| Partnerregistrierung | Neuer Partner kann sich registrieren und erhält einen prüfbaren Status |
| Aboabschluss | Stripe-Test-Checkout führt zu aktivem lokalen Subscription-Status |
| Abo-Sperre | Inaktives oder überfälliges Abo kann Partnerfunktionen einschränken |
| Milestone-Abrechnung | Abgeschlossener Partner-Meilenstein erzeugt genau ein Billing Event |
| Doppelabrechnungsschutz | Wiederholtes Abschließen oder Webhook-Replay erzeugt kein zweites aktives Billing Event |
| Partnerübersicht | Partner sieht nur eigene Umsätze, Perioden und Einzelereignisse |
| Adminübersicht | Admin sieht alle Partnerabrechnungen mit Filter und Export |
| Datenschutz | Zahlungsinstrumentdaten werden nicht lokal gespeichert |

## 22. Nutzerrechte und Nutzergruppen

### 22.1 Zielbild

Das bestehende Rollenmodell `user`, `partner` und `admin` bleibt als
Basisschutz erhalten. Darauf aufbauend ergänzt das System Nutzergruppen und
granulare Berechtigungsschlüssel, damit fachliche Sonderrollen ohne neue
Hardcode-Rollen abgebildet werden können.

Typische Gruppen sind:

| Gruppe | Beispielhafte Rechte |
|---|---|
| Fachadmin | Surveys und Steps lesen/schreiben, Nutzerfortschritt bearbeiten |
| Support | Nutzer lesen, Dateien nach Berechtigung lesen, keine Löschrechte |
| Abrechnung | Billing lesen/exportieren, Billing Events stornieren |
| Partner-Manager | Partner verwalten, Partnerregistrierungen freigeben |
| Auditor | Audit Logs und Rechte-Audit lesen, keine Schreibrechte |

### 22.2 Berechtigungsschlüssel

| Bereich | Beispielrechte |
|---|---|
| Surveys | `surveys.read`, `surveys.write`, `surveys.publish` |
| Steps | `steps.read`, `steps.write`, `steps.reorder`, `steps.templates.manage` |
| Nutzer | `users.read`, `users.write`, `users.impersonate` |
| Partner | `partners.read`, `partners.write`, `partners.approve` |
| Billing | `billing.read`, `billing.export`, `billing.void` |
| Dateien | `files.read`, `files.upload`, `files.delete` |
| CMS/E-Mail | `cms.write`, `email_templates.write` |
| Zugriffskontrolle | `access.read`, `access.manage` |
| Audit | `audit.read` |

### 22.3 Effektive Rechteberechnung

| Schritt | Beschreibung |
|---|---|
| 1. Basisrolle | Startrechte aus `user`, `partner` oder `admin` werden geladen |
| 2. Gruppen | Aktive Gruppen des Nutzers werden additiv berücksichtigt |
| 3. Scope | Survey-, Partner- oder globale Einschränkungen werden angewendet |
| 4. Overrides | Explizite Nutzer-Overrides ergänzen oder beschränken Rechte |
| 5. Endpoint-Prüfung | Backend prüft die erforderlichen Rechte und den Ressourcenscope |
| 6. Audit | Änderungen an Gruppen, Mitgliedschaften und Overrides werden protokolliert |

### 22.4 Sicherheitsregeln

| Regel | Umsetzung |
|---|---|
| Backend führend | Frontend blendet Funktionen aus, Backend entscheidet verbindlich |
| Least Privilege | Neue Gruppen starten ohne kritische Schreib- oder Exportrechte |
| Kritische Rechte | `users.impersonate`, `billing.void`, `access.manage` und `audit.read` sind separat zu vergeben |
| Mandantenscope | Survey- und Partnerrechte gelten nur im zugewiesenen Scope |
| Auditierbarkeit | Jede Änderung an Rechten erzeugt einen Permission-Audit-Eintrag |

### 22.5 Abnahmekriterien Access Control

| Kriterium | Erwartung |
|---|---|
| Gruppenverwaltung | Admin kann Gruppen anlegen, ändern, deaktivieren und Nutzer zuordnen |
| Effektive Rechte | Kombinierte Gruppen ergeben reproduzierbar die erwarteten Rechte |
| Scope-Prüfung | Survey-/Partner-spezifische Gruppen greifen nur im erlaubten Kontext |
| Overrides | Nutzerbezogene Abweichungen wirken nachvollziehbar und auditierbar |
| Endpoint-Schutz | API lehnt fehlende Berechtigungen mit eindeutigem Fehler ab |
| UI-Gating | Frontend zeigt nicht verfügbare Funktionen nicht als aktive Aktionen an |
| Audit | Rechteänderungen enthalten Akteur, Ziel, Änderung und Zeitpunkt |
