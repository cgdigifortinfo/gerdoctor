# Sessionabschluss: Partner-Onboarding, Stripe und Freischaltung

Stand: 2026-08-24

## Ergebnis

Der bisherige Pflege-Entwicklungsstand wurde vollständig nach `main`
übernommen und auf GitHub veröffentlicht. Die temporären Branches `pflege`,
`Pflege` und `local-pflege` wurden anschließend gelöscht.

## Öffentliche Anwendung

- Root `/`: Partner-Landingpage mit Registrierung
- `/aerzte`: Ärzte-Survey
- `/pflege`: Pflege-Survey
- Registrierung führt bezahlpflichtige Self-Service-Partner direkt in die
  isolierte Route Group `/partner-payment`.

## Zahlungsprozess

- Stripe Checkout übernimmt die initiale Zahlung beziehungsweise das Abo.
- Stripe Customer Portal übernimmt die spätere Zahlungsverwaltung.
- Rechnungen werden über Stripe geladen und im Partnerbereich angeboten.
- Sandbox und Livebetrieb besitzen getrennte Schlüsselkonfigurationen im
  Adminbereich.
- Öffentliche API-Antworten geben keine Secret Keys oder Webhook-Secrets aus.
- Der aktive lokale Stand wurde zuletzt als Sandbox mit Test-Key-Präfix
  bestätigt; konkrete Schlüssel wurden nicht dokumentiert.

## Zweistufige Partnerfreischaltung

Zahlung und fachliche Zuweisung sind getrennte Zustände:

1. Der Partner registriert sich und bezahlt über Stripe.
2. Der Partner kann eigene Profil- und Abrechnungsdaten verwalten.
3. Ein Admin weist mindestens einen Survey zu und aktiviert den Partner.
4. Erst danach werden operative Nutzerlisten, Details, Insights und
   Bearbeitungsaktionen freigegeben.

Vor Schritt 3 zeigt die Dashboard-Übersicht den Freischaltungshinweis. Der Tab
`Other users` bleibt sichtbar, ist aber schreibgeschützt. Seine Detailbuttons
sind deaktiviert. Die API blockiert trotzdem sämtliche direkten Detail- und
Mutationsaufrufe mit HTTP 403. Eigene Partner-, Profil-, Billing- und
Stripe-Einstellungen bleiben erlaubt.

## Relevante Implementierung

- `backend/permissions.py`
  - `partner_is_awaiting_assignment()` als zentrale Zustandsregel
- `backend/server.py`
  - Middleware erzwingt Zahlungs- und Zuweisungsstatus
  - Partnerprofil liefert Aktivierungs- und Survey-Informationen
  - Payment-Router unter `/api/partner-payment`
- `backend/stripe_service.py`
  - zentrale Auswahl der Sandbox-/Live-Konfiguration
  - Customer, Checkout, Portal und Invoice-Zugriff
- `frontend/src/pages/PartnerDashboard.js`
  - Freischaltungsseite
  - read-only `Other users`
  - Profil- und Billing-Zugriff während der Wartezeit
- `frontend/src/pages/PartnerLanding.js`
  - Partnerregistrierung
- `frontend/src/pages/PartnerPayment.js`
  - isolierter Checkout-Zwischenprozess

## Teststrategie

Die bestehenden Tests wurden als Standardsuite beibehalten. Parallel existiert
unter `backend/unit_tests_next` eine neue, bewusst noch nicht standardmäßig
gesammelte Kandidatensuite. `backend/pytest.next.ini` aktiviert ausschließlich
diesen Pfad.

Letzte Ergebnisse:

- Kandidatensuite: 98 bestanden
- relevante bestehende Regressionstests: 128 bestanden
- Frontend-Produktionsbuild: erfolgreich
- Python-Kompilierungsprüfung: erfolgreich
- `git diff --check`: erfolgreich

Stripe selbst ist in der Kandidatensuite bewusst ausgeschlossen, bis die
externe Integration separat weiterbearbeitet wird.

## Git-Endstand vor diesem Memory-Commit

- Branch: `main`
- Remote: `origin/main`
- Commit: `cdec7ec feat: add partner onboarding and billing flow`
- Divergenz: 0 voraus, 0 zurück
- Working Tree: sauber

Der Memory-Abschluss erzeugt anschließend einen zusätzlichen Dokumentations-
Commit auf `main`.
