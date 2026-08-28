import { activeSurveys, createUserPayload, emptyCreateUser, groupsForRole, linkedUserCandidates, sortedPartners, systemGroupIdsForRole } from './adminUserDialogDomain';

describe('adminUserDialogDomain', () => {
    test('creates normalized initial state and system groups', () => {
        expect(emptyCreateUser()).toStrictEqual({ email: '', password: '', name: '', role: 'user', partner_id: 'none', survey_id: '', group_ids: [] });
        expect(emptyCreateUser('survey', ['g'])).toStrictEqual(expect.objectContaining({ survey_id: 'survey', group_ids: ['g'] }));
        const groups = [{ id: 'a', role: 'user', is_system: true }, { id: 'b', role: 'user', is_system: false }, { id: 'c', role: 'partner', is_system: true }];
        expect(systemGroupIdsForRole(groups, 'user')).toStrictEqual(['a']);
        expect(systemGroupIdsForRole()).toStrictEqual([]);
    });

    test('removes fields that are inapplicable to a created user', () => {
        const base = { role: 'user', partner_id: 'none', survey_id: 's', group_ids: ['g'] };
        expect(createUserPayload(base, true)).toStrictEqual({ role: 'user', survey_id: 's', group_ids: ['g'] });
        expect(createUserPayload({ ...base, role: 'partner', partner_id: 'p' }, true)).toStrictEqual({ role: 'partner', partner_id: 'p', group_ids: ['g'] });
        expect(createUserPayload(base, false)).toStrictEqual({ role: 'user', survey_id: 's' });
        expect(createUserPayload(base)).toStrictEqual({ role: 'user', survey_id: 's' });
    });

    test('builds role group options including wildcard and missing permission labels', () => {
        const groups = [{ id: 'all', role: 'user', name: 'All', permissions: ['*'] }, { id: 'none', role: 'user', name: 'None' }, { id: 'other', role: 'partner', name: 'Other' }];
        expect(groupsForRole(groups, 'user')).toStrictEqual([
            { value: 'all', label: 'All', description: 'Alle Rechte' },
            { value: 'none', label: 'None', description: '0 Rechte' },
        ]);
        expect(groupsForRole()).toStrictEqual([]);
    });

    test('filters active surveys and sorts partners without mutating input', () => {
        expect(activeSurveys([{ id: 'on', is_active: true }, { id: 'off', is_active: false }])).toStrictEqual([{ id: 'on', is_active: true }]);
        expect(activeSurveys()).toStrictEqual([]);
        const partners = [{ name: 'Zulu' }, { name: 'Alpha' }];
        expect(sortedPartners(partners).map(({ name }) => name)).toStrictEqual(['Alpha', 'Zulu']);
        expect(partners[0].name).toBe('Zulu');
        expect(sortedPartners()).toStrictEqual([]);
    });

    test('searches linked users by name or email and uses email as tie breaker', () => {
        const users = [{ id: 'b', name: 'Same', email: 'b@x' }, { id: 'a', name: 'Same', email: 'a@x' }, { id: 'z', name: 'Zulu', email: 'z@x' }];
        expect(linkedUserCandidates(users, ' SAME ').map(({ id }) => id)).toStrictEqual(['a', 'b']);
        expect(linkedUserCandidates(users, 'z@x').map(({ id }) => id)).toStrictEqual(['z']);
        expect(linkedUserCandidates(users).map(({ id }) => id)).toStrictEqual(['a', 'b', 'z']);
        expect(linkedUserCandidates()).toStrictEqual([]);
    });
});
