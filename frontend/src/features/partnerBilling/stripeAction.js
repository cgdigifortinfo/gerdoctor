export function getPartnerStripeAction(stripeStatus = {}) {
    if (!stripeStatus.configured) return null;
    if (stripeStatus.customer_created) {
        return { kind: 'portal', label: 'Stripe-Konto verwalten' };
    }
    return { kind: 'checkout', label: 'Stripe Checkout starten' };
}
