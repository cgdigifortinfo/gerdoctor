export const dashboardForRole = (role = '') => {
    if (role === 'admin') return '/admin';
    if (role === 'partner') return '/partner-dashboard';
    return '/dashboard';
};

export const hasRequiredPermission = (permissions = [], requiredPermission = '') =>
    !requiredPermission || permissions.includes('*') || permissions.includes(requiredPermission);
