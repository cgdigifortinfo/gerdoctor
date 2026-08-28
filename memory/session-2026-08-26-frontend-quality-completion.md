# Sessionabschluss – Frontend-Architektur und vollständige Qualitätsgates

Stand: 2026-08-26

> Der aktuellste Abschlussstand einschließlich User-Progress- und
> Dokumentnavigation steht in
> `memory/session-2026-08-28-user-journey-completion.md`.

## Ergebnis

- Das Frontend wurde in fachliche Admin-Hooks, Command-Hooks, Tabs, Dialoge,
  Step-Editor-Panels und eigenständige Domain-Module zerlegt.
- Wiederverwendbare UI-Bausteine umfassen Page-/Section-Cards,
  Collection-Controls, SearchToolbar, Tabellenprimitive, Pagination,
  PaginatedCollection, Status-/Tag-Badges und einen global nutzbaren
  Bestätigungsdialog.
- Unbenutzte Sammelimporte und kopierte UI-, Icon- und API-Imports wurden
  bereinigt. Temporäre Artifact-Dateien wurden entfernt.
- API-, Normalisierungs-, Journey-, Partner-, Step-, Flow-, Admin- und
  UI-Logik liegt soweit sinnvoll in kleinen, deterministischen Domain-Modulen.
  React- und HTTP-Adapter bleiben deklarativ und delegieren Fachentscheidungen.
- Fehlende Eingabewerte werden an den Grenzen normalisiert; Domain-Logik nutzt
  stabile Defaults und vermeidet unnötige nullable Zwischenzustände.

## Frontend-Gates

- Vollständige Jest-Suite: 58/58 Suites, 427/427 Tests und 55/55 Snapshots.
- Coverage:
  - Statements: 100 Prozent (4.489/4.489)
  - Branches: 100 Prozent (4.145/4.145)
  - Functions: 100 Prozent (1.676/1.676)
  - Lines: 100 Prozent (3.621/3.621)
- Der Browser-Entry-Point `src/index.js` wird regulär getestet und ist nicht
  mehr aus `collectCoverageFrom` ausgenommen.
- Der optimierte Production-Build kompiliert erfolgreich.

## Stryker-Migration

- Der frühere globale Monolith `frontend/stryker.config.json` wurde entfernt.
- Ebenfalls entfernt wurden überlappende bzw. temporäre Konfigurationen für
  Admin-UI, Steps, Step-Integration und Timeout-Sonderläufe.
- `frontend/mutation-shards.json` ist die kanonische Quelle für 19 fokussierte
  Mutation-Shards.
- `frontend/scripts/check-mutation-shards.cjs` erzwingt, dass jede produktive
  Frontend-Quelldatei exakt einem Shard zugeordnet ist. Aktuell sind es 113
  Quelldateien ohne Lücke oder Überschneidung.
- `frontend/scripts/run-mutation-shards.cjs` validiert das Manifest und führt
  alle Shards sequenziell aus. `npm run test:mutation` verwendet ausschließlich
  diesen Runner.
- Der vollständige Lauf aller 19 Shards ist bei einem Break-Gate von 100 grün:
  keine überlebenden, nicht abgedeckten oder in Timeout gelaufenen Mutanten.
- Frisch verifizierte große Bereiche: Step-Core 315/315 und
  StepsFlowBuilder 435/435 Mutanten getötet.

## Backend-Gates zum gemeinsamen Abschluss

- Backend-Gesamt-Unit-Suite: 583/583 Tests, 100,00 Prozent Coverage über 7.007
  Statements und 1.610 Branches.
- Backend-Domain-Suite: 707/707 Tests, 100,00 Prozent Coverage über 5.510
  Statements und 1.430 Branches.
- mypy: 224 Source-Dateien ohne Befund.
- mutmut: 5.549/5.549 Mutanten getötet; das CI-Qualitäts-Gate ist grün.

## Verbindlicher Weiterarbeitsmodus

- Neue produktive Frontend-Dateien müssen im Mutation-Manifest genau einem
  fachlich passenden Shard zugeordnet werden; der Manifest-Check verhindert
  Lücken und Doppelmutation.
- Fachliche Conditions, Reducer, Normalisierung und Zuweisungen bevorzugt als
  kleine pure Funktionen implementieren und regulär mutation-testen.
- Stryker-Ausnahmen nur für deklarative Adapter verwenden, wenn die delegierte
  Fachlogik separat vollständig mutation-getestet ist.
- `npm run test:coverage`, `npm run build` und `npm run test:mutation` bilden
  gemeinsam das Frontend-Abschlussgate.
- Backend-Abschlussgate bleibt: `pytest -c pytest.next.ini`, `mypy`,
  `pytest -c pytest.domain.ini`, `mutmut run`, `mutmut export-cicd-stats` und
  `python scripts/assert_mutation_quality.py`.
