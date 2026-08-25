import { render, screen } from '@testing-library/react';

import { ProtectedRoute } from './ProtectedRoute';
import { useAuth } from '../contexts/AuthContext';

jest.mock('../contexts/AuthContext', () => ({ useAuth: jest.fn() }));
jest.mock('react-router-dom', () => ({
    Navigate: ({ to }) => <div>{`Navigation:${to}`}</div>,
}), { virtual: true });

function renderAccess({ user, allowedRoles, requiredPermission, path = '/protected' }) {
    useAuth.mockReturnValue({ user, loading: false });
    render(
        <ProtectedRoute allowedRoles={allowedRoles} requiredPermission={requiredPermission}>
            <div>Geschützter Inhalt</div>
        </ProtectedRoute>,
    );
}

afterEach(() => jest.clearAllMocks());

test('Auth: nicht angemeldete Personen werden zum Login geleitet', () => {
    renderAccess({ user: null, allowedRoles: ['admin'] });
    expect(screen.getByText('Navigation:/login')).toBeInTheDocument();
});

test('Admin-Dashboard: passende Rolle und Berechtigung erhalten Zugriff', () => {
    renderAccess({
        user: { role: 'admin', permissions: ['analytics.view'] },
        allowedRoles: ['admin'], requiredPermission: 'analytics.view',
    });
    expect(screen.getByText('Geschützter Inhalt')).toBeInTheDocument();
});

test('Partner-Dashboard: Partner werden bei falschem Portal zum eigenen Dashboard geleitet', () => {
    renderAccess({ user: { role: 'partner', permissions: ['portal.partner.access'] }, allowedRoles: ['admin'] });
    expect(screen.getByText('Navigation:/partner-dashboard')).toBeInTheDocument();
});

test('User-Dashboard: fehlende Fachberechtigung zeigt die konkrete Sperre', () => {
    renderAccess({
        user: { role: 'user', permissions: ['portal.user.access'] },
        allowedRoles: ['user'], requiredPermission: 'survey.own.view',
    });
    expect(screen.getByRole('heading', { name: 'Keine Berechtigung' })).toBeInTheDocument();
    expect(screen.getByText(/survey\.own\.view/)).toBeInTheDocument();
});
