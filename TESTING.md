# Teststrategie

Die Tests sind bewusst in vier Stufen getrennt. Ein erfolgreicher Lauf einer
Stufe ersetzt keine andere Stufe.

1. **Unit-Tests** prüfen reine Geschäftslogik schnell und deterministisch.
2. **Mutation Tests** prüfen, ob Assertions fachliche Fehler tatsächlich erkennen.
3. **Integrations-/API-Tests** prüfen MongoDB, Berechtigungen und HTTP-Verträge.
4. **E2E-Tests** prüfen wenige geschäftskritische Abläufe im Browser.

## Befehle

```bash
# Backend Unit Coverage einschließlich Branch Coverage
docker exec gerdoctor-backend pytest -c pytest.next.ini

# Extrahierte Domain-/Repository-/Service-Module: hartes 100-%-Gate
docker exec gerdoctor-backend pytest -c pytest.domain.ini

# Strikte statische Typprüfung der extrahierten Backend-Slices
docker exec gerdoctor-backend mypy

# Backend-Mutationen (mutmut >= 3.7) und CI-taugliche Ergebnisprüfung
docker exec gerdoctor-backend mutmut run
docker exec gerdoctor-backend mutmut export-cicd-stats
docker exec gerdoctor-backend python scripts/assert_mutation_quality.py

# Bestehende Backend-Regressionssuite
docker exec -e REACT_APP_BACKEND_URL=http://localhost:8001 gerdoctor-backend pytest -q

# Frontend Unit Coverage und Mutationen
docker exec gerdoctor-frontend npm run test:coverage
docker exec gerdoctor-frontend npm run test:mutation
```

## Coverage-Regeln

- Line- und Branch-Coverage werden gemeinsam gemessen.
- Definitionen werden nicht künstlich aus der Messung entfernt. Reine Konstanten
  oder deklarative Daten benötigen aber keine eigenen Tests.
- Das Gate wird nur angehoben, wenn die Suite den neuen Wert stabil erreicht.
- `# pragma: no cover` ist nur für technisch nicht ausführbare Schutzpfade erlaubt.
- Das Ziel ist 100 % für extrahierte reine Geschäftslogik. Router, Datenbank- und
  Browserintegration werden zusätzlich über Integration und E2E geprüft.
- Neue Python-Slices müssen das strikte `mypy`-Gate erfüllen. Framework- oder
  Datenbankgrenzen werden explizit typisiert; untypisierte Definitionen sind in
  den geprüften Slices nicht erlaubt.
- Ein grüner Coverage-Bericht reicht nicht: Kritische Module müssen auch den
  Mutation-Schwellenwert erfüllen.

Die initial gemessenen Baselines sind Backend 47,55 % kombinierte Line-/Branch-
Coverage und Frontend 0,98 % Statements, 0,88 % Branches, 0,27 % Funktionen und
1,09 % Lines. Die niedrigen Frontend-Grenzen sind absichtlich sichtbar im
`package.json` hinterlegt und dürfen nicht abgesenkt werden.

## Ausbauplan

Der historische `server.py` enthält Routing, Datenzugriff und Geschäftslogik in
einer Datei. Neue Logik kommt nicht mehr direkt in diesen Monolithen. Bestehende
Regeln werden bei Änderungen in kleine Module extrahiert und zuerst durch
Unit- und Mutation-Tests abgesichert. Die vorhandenen Regressionstests bleiben
als Sicherheitsnetz bestehen.

Weitere fachliche Slices bleiben ausdrücklich vorgemerkt: Die Bearbeitung und
Vorschau von E-Mail-Templates bildet eine eigene Fähigkeit. Ebenso bleibt das
Domain-Event-System mit Event-Erzeugung, Handlern, Retry und Audit ein eigener
Slice; es wird nicht in Notifications, Survey Runtime oder Billing versteckt.

## Aktueller Messstand (24.08.2026)

- Die extrahierten Partner-Slices für Abrechnung, Zuordnung, servicebezogene
  Submissions, Insights, den Partner User Workspace und Partner Selection umfassen
  Domain, Mapper, Repository, Service und typisierte Ports. Zusammen mit den
  technischen Basisgrenzen und ausführbaren Architekturregeln sichern 200 Tests
  alle 45 Dateien
  mit 100 % Line-/Branch-Coverage.
- Backend-Unit-Gesamtabdeckung: 68,38 %; das globale Gate wurde ausschließlich
  nach oben von 40 über 41, 51, 54, 58, 61, 63 und 66 auf 68 % angehoben.
- Backend Mutation Testing für Billing-, Partner-Zuordnungs-, Submission-,
  Insights-, Workspace- und Selection-Regeln samt Domain-Modellen und Mappern:
  1.642 von 1.642 Mutanten
  erkannt; kein überlebender
  oder ungetesteter Mutant.
- Striktes mypy-Gate: 31 Dateien der extrahierten Billing-, Partner-Zuordnungs-,
  Submission-, Insights-, Workspace- und Selection-Slices ohne Befund. Jeder weitere
  Python-Slice wird der Dateiliste in `backend/mypy.ini` hinzugefügt, bevor er
  als extrahiert gilt. Aktuell umfasst das Gate 45 Dateien.
- Der erste isolierte Frontend-Slice `features/steps/domain` verlangt 100 %
  Line-/Branch-/Function-/Statement-Coverage. Sein Mutation-Gate wurde von 70
  auf 85 % angehoben; der aktuelle Score beträgt 86,87 % (225/259).
- Reine `domain.versioning_rules`: 100 % Line- und Branch-Coverage.
- Frontend-Komponententests prüfen die Zugriffsverträge für Auth-, Admin-, Partner-
  und User-Dashboard.
- Frontend Unit-Suite: mindestens 25 Tests; `stepVisibility.js` 98,83 % Statements,
  90,26 % Branches und 98,52 % Lines.
- Frontend Mutation Testing: 79,10 % und damit über dem Gate von 70 %.
- Gesamter Frontend-Code: 2,97 % Statements, 3,45 % Branches, 1,51 % Funktionen
  und 2,96 % Lines. Die globalen Gates wurden ausschließlich nach oben auf
  2,9/3,4/1,5/2,9 % angehoben. Das ist weiterhin eine wesentliche Lücke.
- Backend-Gesamtsuite: 382 bestanden, 15 erwartungsgemäß übersprungen. Ein erst
  nach mehr als vier Minuten aufgetretener UI-Wartezeit-Ausreißer wurde isoliert
  reproduziert (1/1 grün) und mit einer belastbareren E2E-Wartegrenze stabilisiert.

`mutmut` 3.7 wird aus `backend/setup.cfg` konfiguriert. Es mutiert ausschließlich
importstabile Domain-Pakete; `pytest.mutmut.ini` begrenzt den Testlauf auf die
zugehörigen Tests. `scripts/assert_mutation_quality.py` macht den Lauf auch dann
rot, wenn keine Mutanten erzeugt wurden oder ein Mutant überlebt, ungetestet
bleibt, verdächtig ist, abstürzt oder in einen Timeout läuft.
