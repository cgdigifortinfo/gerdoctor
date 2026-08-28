import {
    defaultSurveyId,
    dialogIsOpen,
    partnerUserFeeCents,
    partnerUsers,
} from './adminDialogViewModels';

describe('adminDialogViewModels', () => {
    test('normalizes dialog state without leaking object values', () => {
        expect(dialogIsOpen(undefined)).toBe(false);
        expect(dialogIsOpen({ id: 'partner-1' })).toBe(true);
    });

    test('selects only ordinary users for partner linking', () => {
        const users = [{ id: 'u', role: 'user' }, { id: 'p', role: 'partner' }];
        expect(partnerUsers(users)).toStrictEqual([{ id: 'u', role: 'user' }]);
        expect(partnerUsers()).toStrictEqual([]);
    });

    test('preserves configured zero and supplies a missing fee default', () => {
        expect(partnerUserFeeCents({ stripe_partner_user_fee_cents: 250 })).toBe(250);
        expect(partnerUserFeeCents({ stripe_partner_user_fee_cents: 0 })).toBe(0);
        expect(partnerUserFeeCents()).toBe(0);
    });

    test('chooses active, marked default, first and empty survey ids in order', () => {
        const surveys = [{ id: 'first' }, { id: 'default', is_default: true }];
        expect(defaultSurveyId('active', surveys)).toBe('active');
        expect(defaultSurveyId('', surveys)).toBe('default');
        expect(defaultSurveyId('', [{ id: 'first' }])).toBe('first');
        expect(defaultSurveyId()).toBe('');
    });
});
