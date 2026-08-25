# Partner Administration

Der Partner-Administration-Slice kapselt das administrative Anlegen, Ändern,
Löschen und Verknüpfen von Partnerorganisationen.

Er validiert Survey-Zuweisungen und partnerfähige Steps, verwaltet den primären
Partnernutzer und sorgt bei Verknüpfung oder Trennung für konsistente Rollen und
Gruppen. Beim Löschen werden abhängige Partnerbeziehungen kontrolliert
bereinigt. Die Admin-Darstellung zeigt außerdem die vom Partner angebotenen
Service-Steps und partnerspezifischen Step-Preise.

Domain, Models, Ports, Mongo-Repository, Service und HTTP-Fehlerabbildung sind
klar getrennt und vollständig typisiert. Der Slice ist Teil der strikten
Coverage-, mypy-, Mutation- und Admin-Regressionsgates.
