# Sessionabschluss – User Journey, Navigation und Qualitätsgates

Stand: 2026-08-28

## Behobene User-Progress-Fehler

- Der Abschluss des ersten Formular-Steps schließt nur noch diesen Step ab.
- `anerkennungsstatus` ist gewöhnliches Survey-Formulardatum und löst im
  User-Progress-Endpunkt keine implizite Fertigstellung späterer Blöcke aus.
- Explizite `auto_complete`-Conditions bleiben für fachlich konfigurierte
  Milestones erhalten.
- Nach dem Abschluss eines Steps lädt das Dashboard den aktuellen
  Serverzustand und öffnet den ersten noch nicht abgeschlossenen sichtbaren
  Step.

## Einheitliche Vorwärtsnavigation

- Jeder abgeschlossene User-Step zeigt eine sichtbare Weiter-Aktion, sofern
  ein nächster sichtbarer Step existiert und dieser nicht blockiert ist.
- Das gilt insbesondere für schreibgeschützte Upload-Übersichten nach einem
  Dokument-Upload sowie für Dokument-Workflow-Milestones mit Dateiliste.
- Ist der nächste Step durch Conditions gesperrt oder existiert kein nächster
  Step, wird kein Weiter-Button angezeigt.
- Rückwärtsnavigation verändert keine Progresszustände. Von Upload-Übersicht
  und Milestone kann anschließend wieder deterministisch vorwärts navigiert
  werden.

## End-to-End-Abdeckung

`backend/tests/test_user_first_steps_e2e.py` prüft im echten Browser:

1. Registrierung eines neuen Users über `/s/aerzte/register`.
2. Vollständiges Ausfüllen und Abschließen von Step 1.
3. Nur Step 1 ist abgeschlossen; die nächsten vier Progressdatensätze sind es
   nicht.
4. Auswahl des Selbststart- und Upload-Pfads.
5. Upload der echten Datei `output/pdf/demo-sprachnachweis.pdf`.
6. Navigation zum folgenden Auswahlstep.
7. Rücknavigation zum Dokument-Milestone und zur schreibgeschützten
   Upload-Übersicht; die hochgeladene Datei ist sichtbar.
8. Erneute Vorwärtsnavigation über Milestone zum Auswahlstep.
9. Automatische Bereinigung des angelegten Testusers.

## Zuletzt verifizierte Gates

- Browser-E2E für den vollständigen beschriebenen User-Pfad: 1/1 bestanden.
- UserDashboard: 45/45 Tests bestanden.
- Frontend: 58/58 Suites, 429/429 Tests und 55/55 Snapshots bestanden.
- Frontend-Coverage: Statements 4.492/4.492, Branches 4.154/4.154,
  Functions 1.676/1.676 und Lines 3.627/3.627 – jeweils 100 Prozent.
- Frontend-Production-Build erfolgreich.
- Backend-Unit-Suite: 583/583 Tests und 100 Prozent Coverage.
- Backend-Domain-Suite: 707/707 Tests und 100 Prozent Coverage.
- mypy: 224 Source-Dateien ohne Befund.
- Backend-mutmut: 5.549/5.549 Mutanten getötet.
- Frontend-Stryker: alle 19 kanonischen Shards bei 100 Prozent; der globale
  Stryker-Monolith bleibt entfernt.
- `git diff --check` ohne Befund.

## Weiterarbeiten

- Vorwärtsnavigation gehört in die zentrale Step-Komposition; neue Step-Typen
  dürfen keine eigene abweichende Freischaltungslogik einführen.
- Fachliche Sperren weiterhin aus Step-Conditions ableiten, nicht aus bloßer
  Position oder lokalem UI-Zustand.
- Neue Frontend-Quelldateien genau einem Eintrag in
  `frontend/mutation-shards.json` zuordnen.
