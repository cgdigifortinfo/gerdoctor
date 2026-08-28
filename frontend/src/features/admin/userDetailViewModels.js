export const effectivePermissionLabel = (permissions = []) =>
    permissions.includes('*') ? 'Vollzugriff' : `${permissions.length} wirksame Rechte`;

export const completionPercent = (value = 0) => value ?? 0;

export const stepForProgress = (steps = [], stepId = '') =>
    steps.find(({ id }) => id === stepId);

export const progressData = (data = {}) => data ?? {};

export const hasVisibleProgressData = (data = {}) =>
    Object.keys(progressData(data)).some((key) => key !== 'skipped');

export const fieldPresentation = (step, progress, key) => {
    const current = step?.fields?.find(({ name }) => name === key);
    const historical = progress.step_snapshot?.fields?.find(({ name }) => name === key);
    return {
        label: current?.label ?? historical?.label ?? key.replace(/_/g, ' '),
        type: current?.field_type ?? historical?.field_type ?? '',
        removed: !current && Boolean(historical),
    };
};

export const displayFieldValue = (value) => {
    if (Array.isArray(value)) return value.join(', ');
    if (value && typeof value === 'object') return JSON.stringify(value);
    return String(value ?? '-');
};

export const partnerNameForSubmission = (partners = [], partnerId = '') =>
    partners.find(({ id }) => id === partnerId)?.name ?? 'Unknown Partner';

export const historyAction = (action = '') => ({
    done: action === 'completed',
    inProgress: action === 'in_progress',
    label: action === 'completed' ? 'Abgeschlossen' : action === 'in_progress' ? 'In Bearbeitung' : action,
});
