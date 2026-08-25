# Partner Selection

Der Slice besitzt jetzt auch den öffentlichen FastAPI-Router für Partnersuche,
Einzel- und Mehrfachauswahl. Auswahlvalidierung bleibt im Domain-/Service-Layer;
Mongo-Persistenz und Benachrichtigungen werden über explizite Adapter angebunden.

Der Partner-Selection-Slice kapselt die Auswahl eines Partners innerhalb eines
Survey-Steps.

Er behandelt Einzel- und Mehrfachauswahl, prüft die fachliche Verfügbarkeit der
Partner und erzeugt stabile Zuordnungen zum Nutzer und zum konkreten Step. Die
Entscheidung für Partnerunterstützung aktiviert nicht mehr vorzeitig einen
Pending-Schritt: Erst eine tatsächliche Partnerauswahl erzeugt den dazugehörigen
Vorgang.

Domain, Modelle, Mapper, Ports, Repository und Service sind getrennt. Eigene
Web-Serializer und Fehlerabbildungen halten FastAPI aus der Domäne heraus. Die
Auswahlregeln und ihre Fallstricke sind Bestandteil der strikten Coverage-,
mypy-, Mutation- und übergeordneten Survey-Regressionstests.
