# Partner User Workspace

Der Partner-Workspace-Slice bündelt die nutzer- und stepbezogene Arbeitsansicht
des Partnerportals.

Er liefert nur die Vorgänge, die dem angemeldeten Partner tatsächlich
zugeordnet sind, und hält unterschiedliche Leistungen desselben Nutzers als
separate Workspace-Einträge. Status, Dokumente und mögliche Partneraktionen
werden über typisierte Modelle und Mapper aufgebaut. Repository und Service
trennen Datenzugriff von den fachlichen Workspace-Regeln.

Damit hängen „My Users“, Detailansicht, Dokument-Upload und Abschluss nicht mehr
von uneindeutigen globalen Nutzer-Partner-Referenzen ab. Der Slice wird durch
die gemeinsamen Coverage-, mypy- und Mutation-Gates abgesichert.
