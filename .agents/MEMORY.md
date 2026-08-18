# GerDoctor – Arbeitskontext

Stand: 2026-08-18

## Lokale Umgebung

- Repository: `/Users/christophergunther/apps/gerdoctor`
- Arbeitsbranch: `local-pflege`, basiert auf `origin/pflege`
- Docker Compose startet MongoDB, FastAPI und React.
- Frontend: `http://localhost:3001`
- Backend: `http://localhost:8001`
- MongoDB: `localhost:27017`
- Lokale Testzugänge sind in den E2E-Fixtures dokumentiert; keine Zugangsdaten in Memory-Dateien duplizieren.

## Zuletzt umgesetzt

- Multi-Survey-Verwaltung für Ärzte und Pflege funktioniert über den Survey-Selektor.
- Step-Editor um kontextbezogene, per Portal gerenderte und tastaturbedienbare Tooltips erweitert.
- Der Titel des bearbeiteten Steps steht prominent im Kopf des Edit-Step-Dialogs.
- Neben Listen- und Flow-Ansicht existiert die Ansicht `Abhängigkeiten`:
  - Dagre-Layout ausschließlich anhand realer Conditions
  - keine künstlichen Sequenzkanten
  - rekursive Darstellung von UND-/ODER-Regeln
  - getrennte Positionierung ohne Überschreiben des manuellen Flow-Layouts
- Lokale Dockerfiles und Compose-Konfiguration für Port 3001/8001 ergänzt.
- Backend-Verträge verbessert:
  - rekursive `StepCondition`-Modelle
  - `StepFieldMapping` und `FlowPosition`
  - validiertes `StepResponse` für die Admin-Step-API
  - gemeinsame, lesbare Step-Serialisierung
- Testinfrastruktur verbessert:
  - `pytest.ini` und gemeinsame `base_url`-Fixture
  - `httpx` als deklarierte Testabhängigkeit
  - Modelltests für verschachtelte Conditions, Mappings und Layoutkoordinaten

## Verifikation

- Frontend: 5/5 Tests bestanden.
- Fokussierter Backend-Lauf: 37/37 Tests bestanden.
- Vollständiger Backend-Lauf: 321 bestanden, 15 übersprungen, 6 fehlgeschlagen.
- Frontend-Produktionsbuild war erfolgreich.
- FastAPI OpenAPI und Frontend liefern lokal HTTP 200.

## Bekannte offene Testfehler

1. Zwei Admin-Survey-E2E-Tests: Radix-Auswahl `Alle` liegt laut Playwright außerhalb des Viewports.
2. Zwei Auth-E2E-Tests: erwarten Same-Origin-Proxy über Port 3001, während das lokale Frontend direkt Port 8001 nutzt.
3. Milestone-Flow: Step 7 bleibt in einem Szenario `pending` statt `in_progress`.
4. No-builder-tracking-Test: Landingpages laden noch sechs Bilder von `static.prod-images.emergentagent.com`.

## Architekturhinweise

- `backend/server.py` (~3.000 Zeilen) sollte langfristig in Domain-Router und Services zerlegt werden.
- `frontend/src/pages/AdminDashboard.js` (~3.300 Zeilen) sollte schrittweise in Feature-Komponenten und Hooks aufgeteilt werden.
- Diese großen Refactorings wurden bewusst nicht neben den funktionalen Änderungen durchgeführt.

## Sicherheit beim Weiterarbeiten

- Der Arbeitsbaum enthielt vor den Änderungen bereits lokale Docker- und UI-Arbeit; nicht pauschal zurücksetzen.
- E2E-Tests erzeugen beziehungsweise aktualisieren Screenshots unter `test_results/e2e-screenshots/`.
- Nach einem Backend-Container-Rebuild müssen Playwright und Chromium für E2E-Tests erneut installiert werden, sofern sie nicht ins Image aufgenommen werden.
