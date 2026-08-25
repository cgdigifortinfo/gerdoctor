# Partner Billing

Der Partner-Billing-Slice kapselt die nutzungsabhängige Abrechnung von
Partnerleistungen.

Enthalten sind typisierte Abrechnungsmodelle, Preisermittlung, Usage-Charge-
Erfassung, Statistiken, Persistenz und die Übergabe offener Positionen an
Stripe. Die Preispriorität lautet globaler Standard, Step-Preis und zuletzt
partnerspezifischer Step-Preis. Fehlende Stripe-Verknüpfungen vernichten keine
Gebühren; offene Positionen bleiben sichtbar und können später synchronisiert
werden.

Die Domäne ist von MongoDB, FastAPI und Stripe getrennt. Stripe Invoice Items
werden über einen Port erzeugt, während HTTP-Darstellungen ausschließlich
freigegebene Abrechnungsfelder ausgeben. Domain-, Repository-, Service- und
Web-Grenzen sind Bestandteil des strikten Coverage-, mypy- und Mutation-Gates.
