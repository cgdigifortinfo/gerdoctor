# Document Workflow

Die idempotente Bestandsmigration für historische Dokumenttitel und
Read-only-Conditions gehört nun ebenfalls zu diesem Slice und ist vollständig
Line-/Branch-getestet.

Der Document-Workflow-Slice kapselt Upload, Zuordnung, Sichtbarkeit und Schutz
von Survey-Dokumenten.

Dokumente bleiben dauerhaft Nutzer, Step und Step-Version zugeordnet. Wurde
eine Datei durch Nutzer oder Partner hochgeladen, kann sie im abschließenden
Dokumenten-Step angezeigt und heruntergeladen werden. Historische Dateien sind
vor automatischer Löschung geschützt; vorangehende Eingabe- und Auswahl-Steps
können nach dem Upload read-only werden.

Domainregeln, Models, Mapper, Ports, Mongo-Repository, Service und Webadapter
sind getrennt und typisiert. Positive Fälle, Zugriffsgrenzen und historische
Zuordnungen sind Teil des globalen Coverage-, mypy- und Mutation-Gates.
