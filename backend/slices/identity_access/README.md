# Identity & Access

Der Identity-&-Access-Slice kapselt Authentifizierung, Tokenverarbeitung,
Passwortprüfung und das Laden der aktuellen Identität.

JWT-Erzeugung und -Dekodierung, Passwort-Hashing, Repositoryzugriff,
Service-Orchestrierung und FastAPI-nahe Tokenextraktion sind getrennt. Fehler
wie abgelaufene oder ungültige Tokens, unbekannte Nutzer und ungültige
Identifiers werden an der Webgrenze stabil übersetzt.

Gruppen und effektive Berechtigungen gehören bewusst nicht mehr zu diesem
Slice, sondern zu `groups_permissions`. Im Identity-Slice verbleiben lediglich
Identität und accountbezogene Zugangsregeln, darunter der Wartestatus eines
noch nicht freigeschalteten Partners. Alle Module sind streng typisiert und in
Coverage-, mypy- und Mutation-Gates eingebunden.
