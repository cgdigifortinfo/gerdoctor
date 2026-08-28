import { Navigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { dashboardForRole, hasRequiredPermission } from './routeDomain';

// Stryker disable all: declarative router adapter; access decisions live in routeDomain.
export function ProtectedRoute({ children, allowedRoles, requiredPermission }) {
    const { user, loading } = useAuth();

    if (loading) {
        return (
            <div className="min-h-screen bg-[#FAFAFA] flex items-center justify-center">
                <div className="text-[#52525B]">Loading...</div>
            </div>
        );
    }

    if (!user) {
        return <Navigate to="/login" replace />;
    }

    if (allowedRoles && !allowedRoles.includes(user.role)) {
        return <Navigate to={dashboardForRole(user.role)} replace />;
    }

    if (!hasRequiredPermission(user.permissions, requiredPermission)) {
        return <div className="min-h-screen bg-background flex items-center justify-center p-6"><div className="max-w-md rounded-lg border border-border bg-card p-6 text-center"><h1 className="text-xl font-semibold text-foreground">Keine Berechtigung</h1><p className="mt-2 text-sm text-muted-foreground">Für diesen Bereich fehlt die Berechtigung <code>{requiredPermission}</code>.</p></div></div>;
    }

    return children;
}

export function PublicRoute({ children }) {
    const { user, loading } = useAuth();

    if (loading) {
        return (
            <div className="min-h-screen bg-[#FAFAFA] flex items-center justify-center">
                <div className="text-[#52525B]">Loading...</div>
            </div>
        );
    }

    if (user) {
        return <Navigate to={dashboardForRole(user.role)} replace />;
    }

    return children;
}
