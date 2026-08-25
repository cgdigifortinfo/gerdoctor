# Partner Assignments

Der Partner-Assignments-Slice bildet die dauerhafte Zuordnung eines Nutzers zu
einem Partner und einem konkreten Survey-Step ab.

Die Zuordnung wird bewusst pro Nutzer und Step betrachtet. Ein Nutzer kann
daher für unterschiedliche Leistungen mehrfach beim selben Partner erscheinen,
beispielsweise für Sprachprüfung und Kenntnisprüfung. Mapper übersetzen
Persistenzdokumente in typisierte Modelle; Repository und Service kapseln Suche,
Erstellung und Statusabgleich.

Damit bleiben Partnerrelationen nachvollziehbar und werden nicht mehr aus einer
einzigen globalen `partner_id`-Referenz abgeleitet. Die Regeln und Grenzfälle
sind in den globalen 100-%-Line-/Branch-, mypy- und Mutation-Gates enthalten.
