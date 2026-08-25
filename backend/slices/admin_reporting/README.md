# Admin Reporting

Dieser Slice kapselt ausschließlich aggregierte, lesende Administratorberichte:
globale Portalstatistiken, Step-Abschlussquoten sowie die partnerübergreifende
Abrechnungsübersicht. Technische Mongo-Abfragen, Report-Orchestrierung und
FastAPI-Routen sind getrennt; Rechnungs- und Usage-Daten werden über injizierte
Adapter aus den zuständigen Billing-Slices bezogen.
