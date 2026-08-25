# Survey Runtime / Step Progress

Neben Sichtbarkeit und Laufzeitmetriken enthält der Slice nun das typisierte
Dashboard-Read-Model sowie die reine Validierung abgeschlossener Antworten,
Pflichtfelder und Upload-Anforderungen.

Der Survey-Runtime-Slice enthält die laufzeitbezogene Step- und
Fortschrittslogik eines Surveys.

Er bewertet Sichtbarkeit, Voraussetzungen, Conditions, nächsten sichtbaren
Step, Abschlussstatus und Read-only-Zustände. Nach einem Partnerabschluss wird
die Bedingungslogik neu ausgewertet und ausschließlich der tatsächlich nächste
sichtbare Step aktiviert. Bereits abgeschlossene oder durch Conditions bzw.
Milestones gesperrte Antworten bleiben unveränderlich.

Reine Regeln, typisierte Modelle, Mapper, Ports, Repository und Service sind
voneinander getrennt. Dadurch lässt sich die Step-Progression unabhängig von
FastAPI und MongoDB vollständig testen. Der Slice läuft im 100-%-Line-/Branch-,
mypy- und Mutation-Gate.
