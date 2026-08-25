# Stripe Subscription

Der Slice „Stripe Subscription“ ist vollständig extrahiert.

Enthalten sind typisierte Subscription-, Checkout- und Connection-Modelle sowie
reine Regeln für Checkout-Abschluss, Zugriffsfreigabe, Subscription-Status,
Kunden- und Abo-Kandidaten, Connection-Audit, Reparierbarkeit und
Subscription-Webhooks. Repository-Port, MongoDB-Adapter, Service und
HTTP-Fehlerabbildung vervollständigen den Slice.

Der konkrete Stripe-Gateway liegt in
`infrastructure/stripe_subscription_gateway.py`. Usage-Charges und Invoice-Items
bleiben im Partner-Billing-Slice. Der gemeinsame Stripe-Client bleibt als
Kompositionsmodul bestehen, da er aktuell Datenbanksettings liest und
FastAPI-Fehler erzeugt. Checkout-, Portal-, Status- und Connection-Repair-
Endpunkte delegieren an den neuen Service; subscriptionbezogene
Webhook-Zustandswechsel wurden aus `server.py` entfernt.

Validierung zum Abschluss der Extraktion:

- Domain-/Architektur-Gate: 459 Tests
- Coverage: 100 % bei 2.622 Statements und 690 Branches
- Stripe-, Webhook-, Billing- und Routenregression: 60 Tests erfolgreich
- striktes mypy: 115 Dateien ohne Fehler
- 4.222 Mutanten geprüft; auch die letzten beiden Stripe-Grenzfälle wurden getötet
- `git diff --check`: fehlerfrei
