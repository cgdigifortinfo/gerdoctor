# Groups & Permissions

Der Slice „Groups & Permissions“ ist vollständig extrahiert.

Enthalten sind reine Domain-Regeln für Rechteauswertung und Gruppenänderungen,
immutable Models, typisierte Repository-Ports, ein MongoDB-Repository, der
Service für Gruppen-CRUD und Gruppenzuordnungen sowie HTTP-Serialisierung und
Fehlerabbildung. Berechtigungskatalog, Defaultgruppen und Migrationslogik liegen
ebenfalls in diesem Slice.

„Identity & Access“ enthält dadurch nur noch Identitäts- und
Account-Zugriffslogik. Die Admin-Endpunkte delegieren an den neuen Service;
direkter Datenbankzugriff wurde aus den Gruppen-Endpunkten entfernt. Gruppenname,
Portalrolle, Rechte, Rollenwechsel, Systemgruppen und bestehende Zuweisungen
werden in Domain und Service validiert.

Validierung zum Abschluss der Extraktion:

- Domain-Gate: 444 Tests
- Line-/Branch-Coverage: 100 %
- betroffene API-, Rollen- und Architekturtests: 195 erfolgreich
- fokussierte Slice-Tests: 164 erfolgreich
- striktes mypy: 108 Dateien ohne Fehler
- alle zunächst überlebenden neuen Mutationen wurden getötet
- `git diff --check`: fehlerfrei
