# Survey Administration

Dieser Slice kapselt den Survey-Lebenszyklus und die dazugehörigen
administrativen Regeln: Auflisten, Erstellen, Bearbeiten, Slug-Eindeutigkeit,
Default-Survey-Umschaltung und Auflösung des Surveys für öffentliche sowie
nutzerspezifische Zugriffe.

Die Domäne normalisiert Slugs, erzeugt stabile Survey-Dokumente und serialisiert
die administrative/public API-Darstellung. Das Repository enthält sämtliche
MongoDB-Zugriffe; der Service koordiniert Default- und Eindeutigkeitsregeln.
FastAPI-Modelle und sichere Fehlerabbildung liegen in `web.py`.

Step-Aufbau, Step-Konfiguration, Vorlagen und historische Versionen bleiben in
ihren jeweiligen Slices. Survey Administration verwaltet ausschließlich den
übergeordneten Survey-Datensatz.

Der Slice ist Bestandteil des strikten mypy-, 100-%-Line-/Branch-Coverage- und
Mutation-Testing-Gates.
