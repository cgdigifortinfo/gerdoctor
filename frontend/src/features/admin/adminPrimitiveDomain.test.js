import { auditActionPresentation } from './adminPrimitiveDomain';

describe('adminPrimitiveDomain', () => {
    test.each([
        ['role_change', 'bg-purple-100'],
        ['step_create', 'bg-green-100'],
        ['step_update', 'bg-blue-100'],
        ['step_delete', 'bg-red-100'],
        ['partner_create', 'bg-green-100'],
        ['partner_update', 'bg-blue-100'],
        ['partner_delete', 'bg-red-100'],
        ['cms_update', 'bg-yellow-100'],
        ['bulk_role_change', 'bg-purple-100'],
    ])('maps %s to its semantic color', (action, color) => {
        const result = auditActionPresentation(action);
        expect(result.label).toBe(action.replace(/_/g, ' '));
        expect(result.colors).toContain(color);
    });

    test('uses explicit fallbacks for missing and unknown actions', () => {
        expect(auditActionPresentation()).toStrictEqual({ label: 'unknown', colors: 'bg-gray-100 text-gray-700' });
        expect(auditActionPresentation('custom_action')).toStrictEqual({ label: 'custom action', colors: 'bg-gray-100 text-gray-700' });
    });
});
