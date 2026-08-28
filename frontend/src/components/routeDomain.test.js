import { dashboardForRole, hasRequiredPermission } from './routeDomain';

describe('routeDomain', () => {
    test('routes every portal role to its dashboard', () => {
        expect(dashboardForRole('admin')).toBe('/admin');
        expect(dashboardForRole('partner')).toBe('/partner-dashboard');
        expect(dashboardForRole('user')).toBe('/dashboard');
        expect(dashboardForRole()).toBe('/dashboard');
    });

    test('accepts omitted, wildcard and explicit permissions only', () => {
        expect(hasRequiredPermission([], '')).toBe(true);
        expect(hasRequiredPermission(['*'], 'users.read')).toBe(true);
        expect(hasRequiredPermission(['users.read'], 'users.read')).toBe(true);
        expect(hasRequiredPermission(['users.write'], 'users.read')).toBe(false);
        expect(hasRequiredPermission(undefined, 'users.read')).toBe(false);
    });
});
