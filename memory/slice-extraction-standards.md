# Standards für Slice-Extraktionen

Stand: 2026-08-25

Diese Vorgaben gelten für jeden weiteren fachlichen Slice, der aus den großen
Backend- oder Frontend-Dateien extrahiert wird.

## Ziel und Zuschnitt

- Ein Slice bildet einen fachlich zusammengehörigen Use Case ab. Zusammengehörige
  Regeln werden nicht nur zur Verkleinerung von Dateien künstlich getrennt.
- Der Slice erhält eine klare öffentliche Schnittstelle. Bestehende Importpfade
  dürfen vorübergehend als kleine Kompatibilitätsfassaden bestehen bleiben.
- Abhängigkeiten zeigen nach innen: technische und Framework-spezifische Details
  dürfen nicht in die Fachdomäne gelangen.
- Bereits extrahierte Slices werden bei jeder weiteren Extraktion auf gemeinsam
  nutzbare technische oder universelle Bestandteile geprüft.

## Backend-Schichten

Jeder fachliche Slice liegt geschlossen unter `backend/slices/<slice-name>/`.
Seine Schichten werden darin über klar benannte Module (`domain.py`,
`models.py`, `mappers.py`, `repository.py`, `service.py`, `ports.py` und
gegebenenfalls Webadapter) gruppiert. Globale Schichtordner werden nicht als
Ablage für slice-spezifische Dateien verwendet.

- `domain`: reine, deterministische Geschäftsregeln und unveränderliche,
  typisierte Value Objects. Keine FastAPI-, MongoDB-, HTTP- oder Infrastruktur-
  Imports.
- `services`: Anwendungsfälle und Orchestrierung. Abhängigkeiten werden über
  typisierte Ports/Protocols eingebracht.
- `repositories`: konkrete Persistenzadapter. MongoDB-Abfragen und technische
  Datenabbildung bleiben hier.
- `infrastructure`: technische Adapter wie Uhr, ID-Konvertierung und
  Serialisierung. Keine Geschäftsregeln.
- `web`: FastAPI-/HTTP-spezifische Fehlerabbildung, Request-/Response-Adapter und
  Serializer. Kein direkter Datenbankzugriff.
- `shared`: ausschließlich sehr kleine, wirklich universelle Typen ohne
  fachliche Bedeutung und ohne Abhängigkeiten.

Es wird kein allgemeiner `core`-Sammelordner angelegt. Code wird nur dann in
einen Basisordner verschoben, wenn seine Verantwortung eindeutig zu
`infrastructure`, `web` oder `shared` gehört. Fachliche Hilfsfunktionen bleiben
im jeweiligen Slice.

## Modellierung und Typisierung

- Framework- und Sprachmittel werden genutzt, wenn sie den Code klarer machen:
  insbesondere `dataclass(frozen=True, slots=True)`, Pydantic an API-Grenzen,
  `Protocol` für Ports sowie `Mapping`/`Sequence` für lesende Eingaben.
- Öffentliche Slice-Schnittstellen und alle neu extrahierten Dateien werden
  vollständig typisiert.
- `Any` bleibt auf echte Framework-/Datenbankgrenzen begrenzt und darf nicht
  unkontrolliert durch Domain und Services fließen.
- Jeder neue Slice wird in das strikte `mypy`-Gate aufgenommen. Neue Warnungen
  werden nicht durch globale Ausnahmen oder eine Lockerung der Konfiguration
  verborgen.
- Namen bilden fachliche Begriffe und Verantwortlichkeiten ab. Kleine,
  gut lesbare Funktionen werden langen Mischfunktionen vorgezogen.

## Tests und Qualitäts-Gates

- Für jedes extrahierte Geschäftsmodul gelten 100 Prozent Line- und
  Branch-Coverage. Positive Fälle, negative Fälle, Grenzwerte und Fallbacks
  werden explizit getestet.
- Domain-Tests sind schnell, deterministisch und frei von MongoDB, Netzwerk und
  FastAPI. Repository-, Service- und Web-Grenzen erhalten eigene Tests.
- Bestehende Tests bleiben während der Umstrukturierung als Regression-Fallback
  erhalten. Sie werden erst ersetzt oder entfernt, wenn gleichwertiger oder
  stärkerer Schutz nachgewiesen ist.
- Backend-Mutation-Testing mit `mutmut >= 3.7` wird für die importstabilen,
  deterministischen Domain-Pakete aktiviert. Überlebende Mutanten werden durch
  bessere Tests oder eine klarere Implementierung beseitigt; pauschale
  Ausschlüsse sind nicht die Lösung.
- Einmalige, zustandsbehaftete Datenmigrationen und Service-Orchestrierung
  gehören nicht in den Domain-Mutationsumfang. Sie bleiben über vollständige
  Line-/Branch-Coverage und gezielte Integrationsfälle abgesichert.
- Nach jeder Extraktion werden mindestens ausgeführt:
  1. gezielte neue Unit-Tests,
  2. 100-%-Line-/Branch-Coverage-Gate,
  3. striktes `mypy`,
  4. Mutation-Test des neuen Domain-Slices,
  5. betroffene bestehende Backend-/Frontend-/E2E-Regressionen,
  6. `git diff --check`.
- Globale Qualitäts-Gates werden bei jedem Ausbau ausschließlich erhöht und
  niemals abgesenkt, um einen neuen Slice aufzunehmen.

## Frontend-Slices

- Größere fachliche Bereiche wie Steps werden als eigener Feature-Slice
  isoliert und innerhalb des Features nach UI, Hooks/State, reiner Logik und
  API-Adaptern gegliedert, wenn diese Trennung einen echten Nutzen bringt.
- Reine Frontend-Regeln werden unabhängig von React-Komponenten getestet.
  Komponenten-Tests decken Auth-, Admin-, Partner- und User-Dashboard-Verhalten
  ab; wichtige rollenübergreifende Abläufe erhalten End-to-End-Tests.
- Fachlogik wird nicht zwischen Backend und UI dupliziert, sofern eine klare
  kanonische Quelle oder ein bewusst getestetes Mapping möglich ist.

## Vorgehen je Extraktionsschritt

1. Verantwortlichkeiten, Importstellen und bestehende Tests erfassen.
2. Fachliche Regeln und unveränderliche Modelle zuerst isolieren.
3. Ports, Service-Orchestrierung und technische Adapter darum legen.
4. Bestehende Aufrufer über die neue Schnittstelle oder eine kleine Fassade
   anbinden, ohne gleichzeitig sachfremde Änderungen vorzunehmen.
5. Tests und Gates ergänzen und vollständig grün ausführen.
6. Erst danach den nächsten fachlichen Slice beginnen.
