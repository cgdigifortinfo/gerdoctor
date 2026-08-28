import { addUniqueTag, allPartnerTags, emptyPartnerForm, inheritedStepFee, matchingTags, partnerForm, partnerUserCandidates, removeTag, toggleId, updateStepFee } from './partnerDialogDomain';

describe('partnerDialogDomain', () => {
    test('creates complete defaults and normalizes sparse partner data', () => {
        expect(emptyPartnerForm()).toStrictEqual({ name: '', description: '', logo_url: '', website: '', contact_email: '', category: '', tags: [], is_active: true, linked_user_ids: [], survey_ids: [], step_user_fee_cents: {}, stripe_customer_id: '', stripe_subscription_id: '', billing_status: '' });
        expect(partnerForm(null)).toStrictEqual(emptyPartnerForm());
        expect(partnerForm({ name: 'School', is_active: false, tags: null })).toStrictEqual(expect.objectContaining({ name: 'School', is_active: false, tags: [], description: '' }));
        expect(partnerForm({ is_active: true, linked_user_ids: ['u'], survey_ids: ['s'], step_user_fee_cents: { a: 1 } })).toStrictEqual(expect.objectContaining({ is_active: true, linked_user_ids: ['u'], survey_ids: ['s'], step_user_fee_cents: { a: 1 } }));
        const populated = { name: 'School', description: 'Desc', logo_url: '/logo', website: 'https://school.test', contact_email: 'office@school.test', category: 'Language', stripe_customer_id: 'cus_1', stripe_subscription_id: 'sub_1', billing_status: 'active' };
        expect(partnerForm(populated)).toStrictEqual(expect.objectContaining(populated));
    });

    test('collects unique sorted tags and matches unselected input', () => {
        expect(allPartnerTags([{ tags: ['Zulu', 'Alpha'] }, { tags: ['Alpha'] }, {}])).toStrictEqual(['Alpha', 'Zulu']);
        expect(allPartnerTags()).toStrictEqual([]);
        expect(matchingTags(['Alpha', 'Alpine', 'Beta'], ['Alpha'], ' AL ')).toStrictEqual(['Alpine']);
        expect(matchingTags(['Alpha'], [], ' ')).toStrictEqual([]);
        expect(matchingTags()).toStrictEqual([]);
    });

    test('adds, removes and toggles values without duplicates', () => {
        const tags = ['Existing'];
        expect(addUniqueTag(tags, ' New ')).toStrictEqual(['Existing', 'New']);
        expect(addUniqueTag(tags, 'Existing')).toBe(tags);
        expect(addUniqueTag(tags, ' ')).toBe(tags);
        expect(addUniqueTag()).toStrictEqual([]);
        expect(removeTag(['a', 'b'], 'a')).toStrictEqual(['b']);
        expect(removeTag()).toStrictEqual([]);
        expect(toggleId(['a', 'b'], 'a')).toStrictEqual(['b']);
        expect(toggleId(['a'], 'b')).toStrictEqual(['a', 'b']);
        expect(toggleId()).toStrictEqual([]);
    });

    test('filters admins, searches users and prioritizes selected ids', () => {
        const users = [{ id: 'admin', role: 'admin', name: 'Admin', email: 'a@x' }, { id: 'z', role: 'user', name: 'Zulu', email: 'z@x' }, { id: 'b', role: 'user', name: 'Same', email: 'b@x' }, { id: 'a', role: 'user', name: 'Same', email: 'a@x' }];
        expect(partnerUserCandidates(users, '', ['z']).map(({ id }) => id)).toStrictEqual(['z', 'a', 'b']);
        expect(partnerUserCandidates(users, 'B@X', []).map(({ id }) => id)).toStrictEqual(['b']);
        expect(partnerUserCandidates(users, ' B@X ', []).map(({ id }) => id)).toStrictEqual(['b']);
        expect(partnerUserCandidates(users, 'same', []).map(({ id }) => id)).toStrictEqual(['a', 'b']);
        expect(partnerUserCandidates()).toStrictEqual([]);
    });

    test('resolves inherited fees and updates explicit prices', () => {
        expect(inheritedStepFee({ step_user_fee_cents: 0 }, 100)).toBe(0);
        expect(inheritedStepFee({}, 100)).toBe(100);
        expect(inheritedStepFee()).toBe(0);
        expect(updateStepFee({ a: 10 }, 'b', '25')).toStrictEqual({ a: 10, b: 25 });
        expect(updateStepFee({ a: 10, b: 25 }, 'b', '')).toStrictEqual({ a: 10 });
        expect(updateStepFee()).toStrictEqual({});
    });
});
