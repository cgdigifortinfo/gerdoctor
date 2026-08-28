export function formatApiError(error = {}) {
    const detail = error.response?.data?.detail;
    if (detail == null) return error.request
        ? 'Der Server ist nicht erreichbar. Bitte versuchen Sie es erneut.'
        : 'Etwas ist schiefgelaufen. Bitte versuchen Sie es erneut.';
    if (detail === 'Invalid email or password') return 'E-Mail-Adresse oder Passwort ist falsch.';
    if (detail === 'Too many failed attempts. Try again later.') return 'Zu viele fehlgeschlagene Versuche. Bitte versuchen Sie es später erneut.';
    if (['Invalid or expired token', 'Token expired'].includes(detail)) return 'Der Link ist ungültig oder abgelaufen.';
    if (Array.isArray(detail)) return detail
        .map((entry) => entry && typeof entry.msg === 'string' ? entry.msg : JSON.stringify(entry))
        .filter(Boolean)
        .join(' ');
    if (detail && typeof detail.msg === 'string') return detail.msg;
    return String(detail);
}

export const userSearchQuery = (query = '', role = '') =>
    `q=${encodeURIComponent(query)}&role=${encodeURIComponent(role)}`;

export const auditLogQuery = (limit = 100, skip = 0, action = '', dateFrom = '', dateTo = '') => {
    const params = new URLSearchParams({ limit: String(limit), skip: String(skip) });
    if (action) params.set('action', action);
    if (dateFrom) params.set('date_from', dateFrom);
    if (dateTo) params.set('date_to', dateTo);
    return params.toString();
};

export const eventsQuery = (limit = 0, eventType = '', status = '') => {
    const params = new URLSearchParams({ limit: String(limit) });
    if (eventType) params.set('event_type', eventType);
    if (status) params.set('status', status);
    return params.toString();
};
