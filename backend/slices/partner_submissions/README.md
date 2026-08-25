# Partner Submissions

Der Partner-Submissions-Slice kapselt die Arbeitsvorgänge, die ein Partner für
einen zugewiesenen Nutzer und Step bearbeitet.

Er enthält typisierte Submission- und Step-Modelle, Statusregeln, Mapper,
Persistenzzugriff und Service-Orchestrierung. Ein Step gilt fachlich als
abgeschlossen, wenn der Partner genau diesen Vorgang abschließt; mehrere
Partnerleistungen desselben Nutzers werden unabhängig gezählt und bearbeitet.

Die Slice-Grenze verhindert, dass Submission-Status, Nutzerzuordnung und
allgemeiner Survey-Fortschritt vermischt werden. Domain-, Mapper-, Repository-
und Servicecode laufen in den gemeinsamen Coverage-, mypy- und Mutation-Gates.
