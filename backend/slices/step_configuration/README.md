# Step Configuration

Der Step-Configuration-Slice bündelt die administrative Konfiguration von
Survey-Steps.

Er enthält Normalisierung und Migration von Formularfeldern, Anforderungen,
Conditions und Step-Dokumenten sowie Repository-, Service- und Webgrenzen. Die
Konfiguration unterstützt gruppierte Regeln, bearbeitbare UND-Bestandteile und
die vorhandene ODER-Semantik, ohne leere Regeln versehentlich als dauerhafte
Sperre zu interpretieren.

Der Form Builder liegt als stabile Fassade im Slice. Fachliche Regeln sind frei
von FastAPI und MongoDB; Migration und Persistenz sind separat gekapselt. Der
gesamte ausführbare Slice-Code ist Bestandteil des 100-%-Line-/Branch-, mypy-
und Mutation-Gates.
