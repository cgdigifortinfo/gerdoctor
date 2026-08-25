# Step Versioning / Answer History

Der Step-Versioning-Slice bewahrt historische Survey-Konfigurationen und
Antworten dauerhaft nachvollziehbar auf.

Er erzeugt unveränderliche Step-Snapshots und Antwortrevisionen, bindet
Dokumente an Nutzer, Step und Step-Version und unterstützt die Migration
bestehender Daten. Historische Antworten und Dateien bleiben auch nach einer
Änderung oder einem Soft-Delete des aktuellen Steps einsehbar. Revisionen
enthalten Vorher-/Nachher-Bezüge für Audit und Adminanzeige.

Domain, Modelle, Ports, Repository und Service sind getrennt. Die Fassade stellt
stabile Aufrufe für bestehende Serverpfade und Migrationen bereit. Historische
Kennzeichnung, Dateischutz und Revisionsfälle laufen im globalen Coverage-,
mypy- und Mutation-Gate.
