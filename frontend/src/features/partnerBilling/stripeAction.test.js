import { getPartnerStripeAction } from './stripeAction';

describe('getPartnerStripeAction', () => {
    it('does not offer a Stripe action when Stripe is not configured', () => {
        expect(getPartnerStripeAction({ configured: false })).toBeNull();
        expect(getPartnerStripeAction()).toBeNull();
    });

    it('starts Checkout before a Stripe customer exists', () => {
        expect(getPartnerStripeAction({ configured: true, customer_created: false })).toEqual({
            kind: 'checkout',
            label: 'Stripe Checkout starten',
        });
    });

    it('opens account management after Checkout created the customer', () => {
        expect(getPartnerStripeAction({ configured: true, customer_created: true })).toEqual({
            kind: 'portal',
            label: 'Stripe-Konto verwalten',
        });
    });
});
