# GerDoctor – Arbeitskontext

Stand: 2026-08-28

## Repository und Git

- Repository: `/Users/christophergunther/apps/gerdoctor`
- Aktiver Branch: `main`
- Remote: `origin/main`
- Letzter veröffentlichter Commit vor diesem Abschluss: `6077443`; der gesamte
  danach entstandene Slice-/Versionierungsstand wird mit dem aktuellen
  Abschlusscommit veröffentlicht.
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
- Die Grundgebühr läuft ausschließlich als monatliches Abonnement.
- Beim ersten Partner-Dokument je Nutzer und Leistungs-Step wird ein offener
  Invoice Item für die nächste Monatsrechnung erzeugt. Preise werden in dieser
  Reihenfolge aufgelöst: globaler Standard, Step-Override, Partner/Step-Override.
- Partner und Admin sehen offene/abgerechnete Posten sowie Stripe-Rechnungen.
- Ein Stripe-Verbindungs-Audit erkennt fehlende Customer-/Subscription-IDs.
  Nur eindeutige Treffer dürfen einzeln oder gesammelt repariert werden;
  mehrdeutige Treffer bleiben manuell zu prüfen.

## Surveys und Step-Editor

- Ärzte- und Pflege-Surveys sind getrennt und im Adminbereich umschaltbar.
- Neben Listen- und Flow-Ansicht existiert die Abhängigkeitsansicht mit
  Dagre-Layout auf Basis realer Conditions, ohne künstliche Sequenzkanten.
- Rekursive UND-/ODER-Regeln, Feld-Mappings und Flow-Positionen besitzen
  validierte Pydantic-Modelle.
- Der Edit-Step-Dialog zeigt den Step-Titel prominent im Kopf.
- Kontextbezogene Tooltips sind per Portal gerendert sowie mit Maus und
  Tastatur bedienbar.
- Partnerauswahl und `partner_submissions` werden serverseitig gemeinsam
  gespeichert. Submissions tragen eine `step_id`; die eindeutige Relation ist
  Nutzer + Step + Partner. Alte Einzelauswahlen desselben Steps werden entfernt.
- Das idempotente Script `backend/repair_partner_references.py` gleicht
  Antworten, Submissions, Partner- und Survey-Zuordnungen ab.
- `backend/audit_step_relations.py` prüft Requirements und Conditions;
  `backend/recalculate_step_flow_layouts.py` berechnet Flow-Layouts neu.

## Seed- und Datenzustand

- Der Baseline-Seed wurde in einer isolierten temporären Datenbank vollständig
  wiederhergestellt und verifiziert; die temporären Daten wurden gelöscht.
- Die Seed-Migration repariert Legacy-Partnerrelationen deterministisch und
  die Verifikation schlägt bei verbleibenden Inkonsistenzen fehl.
- Der letzte globale Partnerrelations-Dry-Run war leer (`actions: []`).
- Historische Step-Versionierung ist umgesetzt: unveränderliche
  Step-Snapshots, Antwortrevisionen, Soft-Delete, dauerhafte
  Dokument-Bindings, Audit-Vorher-/Nachherstände und Bestandsmigration schützen
  historische Konfigurationen, Antworten und Dateien. Admin und Partner sehen
  Konfigurationsabweichungen und gelöschte historische Felder gekennzeichnet.

## Backend-Slice-Architektur

- `backend/server.py` ist nur noch eine 10-zeilige Kompatibilitätsfassade auf
  `web.application`; direkte FastAPI-Routendeklarationen wurden daraus entfernt.
- Fachliche Routen liegen in den jeweiligen Slice-Routern. Survey-Progress und
  Partner-Workspace besitzen getrennte Read-, Detail-, Command- und
  Action-Services sowie Mongo-Repositories.
- `backend/web/application.py` ist Composition-/Lifecycle-Root und enthält
  keine direkten `@api_router`- oder `@app`-Routen mehr.
- Technische Mongo-Schema- und Indexinitialisierung liegt in
  `backend/infrastructure/mongo_bootstrap.py`.
- Architekturgrenzen und Abhängigkeitsrichtung sind in
  `backend/ARCHITECTURE.md` dokumentiert und werden durch Tests erzwungen.

## Tests

- Bestehende Standardsuite bleibt unter `backend/tests` und wird über
  `backend/pytest.ini` gesammelt.
- Neue Kandidatensuite liegt getrennt unter `backend/unit_tests_next`.
- Ausführung der Kandidatensuite:
  `cd backend && pytest -c pytest.next.ini`
- Das strikte Backend-Domain-Gate umfasst 5.510 Statements und 1.430 Branches
  bei 100,00 Prozent Line-/Branch-Coverage (`707 passed`).
- Sie deckt Modelle, Auth, Berechtigungen, Formularnormalisierung,
  Condition-Auswertung, Metriken und Partnerfreischaltung mit Positiv-,
  Negativ-, Grenzwert- und Fallback-Fällen ab.
- Backend-Gesamt-Unit-Suite: `583 passed`; 7.007 Statements und 1.610 Branches
  bei 100,00 Prozent Coverage, keine fehlenden oder partiellen Branches.
- Striktes mypy ist für 224 Python-Module grün.
- Backend-Mutation: 5.549/5.549 Mutanten getötet; keine Survived-, Timeout-,
  Suspicious- oder Uncovered-Mutanten. Das CI-Gate
  `backend/scripts/assert_mutation_quality.py` ist grün.
- Frontend-Gesamtsuite: 58/58 Suites, 429/429 Tests und 55/55 Snapshots grün.
- Frontend-Coverage: Statements 4.492/4.492, Branches 4.154/4.154,
  Functions 1.676/1.676 und Lines 3.627/3.627, jeweils 100 Prozent.
- Der Frontend-Production-Build ist grün.
- Frontend-Stryker verwendet keinen globalen Monolithen mehr. Das kanonische
  Manifest `frontend/mutation-shards.json` ordnet 113 produktive Quelldateien
  jeweils exakt einem von 19 fokussierten Shards zu. `npm run test:mutation`
  prüft zuerst das Manifest und führt danach alle Shards aus; der vollständige
  Lauf ist bei 100 Prozent Mutation Score ohne Survived-, Timeout- oder
  No-Coverage-Mutanten grün.
- `frontend/stryker.config.json` und die überlappenden Legacy-Konfigurationen
  `stryker.admin-ui.config.json`, `stryker.steps.config.json`,
  `stryker.step-integration.config.json`, `stryker.step-timeouts.config.json`
  und `stryker.flow-timeouts.config.json` wurden entfernt.
- Besonders große, frisch verifizierte Shards: Step-Core 315/315 und
  StepsFlowBuilder 435/435 Mutanten getötet.
- Der User-Progress-Endpunkt behandelt `anerkennungsstatus` als gewöhnliches
  Formulardatum. Er schließt ausschließlich den adressierten Step ab und löst
  keine impliziten Block-Auto-Skips mehr aus; explizite `auto_complete`-
  Conditions für Milestones bleiben aktiv.
- Abgeschlossene User-Steps zeigen zentral eine Vorwärtsaktion, wenn ein
  nächster sichtbarer und nicht blockierter Step existiert. Dies gilt auch für
  schreibgeschützte Upload-Übersichten und Dokument-Workflow-Milestones.
- `backend/tests/test_user_first_steps_e2e.py` registriert einen realen
  Ärzte-User, füllt Step 1 aus, prüft die ersten fünf Progresszustände, nimmt
  den Selbst-Upload-Pfad, lädt eine echte Demo-PDF hoch und verifiziert die
  Rückwärts-/Vorwärtsnavigation zwischen Upload-Übersicht, Dokument-Milestone
  und folgendem Auswahlstep.
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

- Für jede weitere Slice-Extraktion gelten die verbindlichen Regeln aus
  `memory/slice-extraction-standards.md` (Schichtengrenzen, striktes mypy,
  100 % Line-/Branch-Coverage, Mutation Testing und ausschließlich steigende
  globale Gates).
- Vor Änderungen zuerst `git status` prüfen; reguläre Arbeit erfolgt auf
  `main`, solange kein neuer Feature-Branch angelegt wird.
- Stripe-Test-Price-IDs und Live-Price-IDs gehören zu getrennten Stripe-Modi.
- Keine realen Stripe-Zugangsdaten, Webhook-Secrets, Datenbankexporte oder
  personenbezogenen Uploads committen.
- Die Admin-Oberfläche ist inzwischen fachlich zerlegt: Controller-State und
  Commands, Admin-Tabs, Dialoge, Step-Editor-Panels sowie wiederverwendbare
  Layout-, Collection-, Tabellen-, Pagination-, Search-, Badge- und
  Confirm-Dialog-Primitives besitzen getrennte Module und Tests.
- Frontend-Orchestrierungs-/Renderadapter sind dort gezielt von Mutation
  ausgeschlossen, wo die zugrunde liegende Fachlogik in extrahierten, regulär
  mutation-getesteten Domain-Funktionen liegt. Neue Logik gehört bevorzugt in
  diese Domain-Module; Adapter dürfen nicht zur Ablage fachlicher Bedingungen
  werden.
- `backend/server.py` ist bereits auf die stabile Kompatibilitätsfassade reduziert.
- Detaillierter Sessionabschluss:
  `memory/session-2026-08-28-user-journey-completion.md`.
