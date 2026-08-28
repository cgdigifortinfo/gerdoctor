import { asArray } from '../../lib/valueNormalization';

export const STEP_STATUS_OPTIONS = [
    { value: 'pending', label: 'Ausstehend' },
    { value: 'in_progress', label: 'In Bearbeitung' },
    { value: 'completed', label: 'Abgeschlossen' },
    { value: 'rejected', label: 'Abgelehnt' },
    { value: 'skipped', label: 'Übersprungen' },
];

export const CONDITION_OPERATOR_OPTIONS = [
    { value: 'status_is', label: 'Status ist' },
    { value: 'status_not', label: 'Status ist nicht' },
    { value: 'equals', label: 'Ist gleich' },
    { value: 'not_equals', label: 'Ist ungleich' },
    { value: 'one_of', label: 'Ist einer von' },
    { value: 'not_one_of', label: 'Ist keiner von' },
    { value: 'contains', label: 'Enthält Text' },
    { value: 'not_empty', label: 'Ist ausgefüllt' },
    { value: 'empty', label: 'Ist leer' },
    { value: 'has_upload', label: 'Dokument vorhanden' },
    { value: 'missing_upload', label: 'Dokument fehlt' },
];

export const CONDITION_ACTION_OPTIONS = [
    { value: 'block', label: 'Schritt blockieren' },
    { value: 'hide', label: 'Schritt ausblenden' },
    { value: 'read_only', label: 'Schritt schreibschützen' },
    { value: 'auto_complete', label: 'Automatisch abschließen' },
    { value: 'allow_next', label: 'Zugriff erlauben' },
    { value: 'redirect', label: 'Zu anderem Schritt weiterleiten' },
];

export function optionValue(option) {
    if (typeof option === 'string') return option;
    return option?.value ?? option?.label ?? '';
}

export function optionLabel(option) {
    if (typeof option === 'string') return option;
    return option?.label ?? option?.value ?? '';
}

export function stepFieldOptions(selectedStep, includeStatus = true) {
    const options = asArray(selectedStep?.fields).map((field) => ({
        value: field.name,
        label: field.label || field.name,
        description: `${field.name} · ${field.field_type || 'Feld'}`,
        keywords: `${field.name} ${field.field_type || ''}`,
    }));
    if (includeStatus) {
        options.unshift({
            value: 'status',
            label: 'Schrittstatus',
            description: 'Systemfeld · pending, in_progress, completed …',
            keywords: 'status abgeschlossen ausstehend system',
        });
    }
    if (selectedStep?.step_type === 'milestone' && !options.some((option) => option.value === 'partner_uploads')) {
        options.push({
            value: 'partner_uploads',
            label: 'Partner-Dokumente',
            description: 'Systemfeld · vom Partner hochgeladene Dokumente',
            keywords: 'partner uploads dokumente system',
        });
    }
    return options;
}

export function withFallbackOption(options, value, labelPrefix = 'Bestehender Wert') {
    if (value == null || value === '' || options.some((option) => String(option.value) === String(value))) return options;
    return [...options, { value: String(value), label: `${labelPrefix}: ${value}` }];
}

export function conditionGroupKey(condition) {
    if (Array.isArray(condition.all_of)) return 'all_of';
    if (Array.isArray(condition.any_of)) return 'any_of';
    return null;
}

export function conditionActionUpdate(action, targetStepOrder) {
    return { action, target_step_order: action === 'redirect' ? targetStepOrder : null };
}

export function conditionSourceUpdate(sourceValue) {
    return { source_step_order: sourceValue ? Number(sourceValue) : null, field: 'status', operator: 'status_is', value: 'completed' };
}

export function conditionFieldUpdate(fieldName, selectedField) {
    if (fieldName === 'status') return { field: fieldName, operator: 'status_is', value: 'completed' };
    if (selectedField?.field_type === 'multiupload' || fieldName === 'partner_uploads') return { field: fieldName, operator: 'has_upload', value: '' };
    return { field: fieldName, operator: 'equals', value: optionValue(selectedField?.options?.[0]) || '' };
}

export function conditionOperatorUpdate(operator, currentValue) {
    if (['empty', 'not_empty', 'has_upload', 'missing_upload'].includes(operator)) return { operator, value: '' };
    if (['one_of', 'not_one_of'].includes(operator)) return { operator, value: Array.isArray(currentValue) ? currentValue : (currentValue ? [currentValue] : []) };
    return { operator, value: Array.isArray(currentValue) ? (currentValue[0] || '') : currentValue };
}

export function conditionDisplayValue(operator, value) {
    if (['has_upload', 'missing_upload'].includes(operator) && (value == null || value === '')) return 'beliebiges Dokument';
    if (Array.isArray(value)) return value.join(', ');
    return String(value ?? '–');
}

export function conditionMultiValue(value) {
    if (Array.isArray(value)) return value;
    return value ? [value] : [];
}

export function conditionScalarValue(value) {
    if (Array.isArray(value)) return value[0] || '';
    return value || '';
}

export function conditionValueMode(operator, hasOptions) {
    if (operator === 'empty' || operator === 'not_empty') return 'none';
    if (operator === 'one_of' || operator === 'not_one_of') return 'multi';
    return hasOptions ? 'select' : 'input';
}
