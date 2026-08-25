// Shared condition evaluator; kept aligned with backend helpers._evaluate_condition.
export function evaluateCondition(condition, stepDataByOrder) {
    if (Array.isArray(condition?.all_of)) return condition.all_of.every(child => evaluateCondition(child, stepDataByOrder));
    if (Array.isArray(condition?.any_of)) return condition.any_of.some(child => evaluateCondition(child, stepDataByOrder));
    const source = stepDataByOrder[condition.source_step_order];
    if (!source) return false;
    const data = source.data || {};
    const fieldValue = condition.field ? data[condition.field] : source.status;
    const expected = condition.value;
    switch (condition.operator) {
        case 'equals': return String(fieldValue) === String(expected);
        case 'not_equals': return String(fieldValue) !== String(expected);
        case 'one_of': {
            const values = (Array.isArray(expected) ? expected : [expected]).map(String);
            return Array.isArray(fieldValue) ? fieldValue.some(value => values.includes(String(value))) : values.includes(String(fieldValue));
        }
        case 'not_one_of': {
            const values = (Array.isArray(expected) ? expected : [expected]).map(String);
            return Array.isArray(fieldValue) ? !fieldValue.some(value => values.includes(String(value))) : !values.includes(String(fieldValue));
        }
        case 'contains': return String(fieldValue || '').includes(String(expected));
        case 'not_empty': return !!fieldValue && fieldValue !== '';
        case 'empty': return !fieldValue || fieldValue === '';
        case 'status_is': return source.status === expected;
        case 'status_not': return source.status !== expected;
        case 'has_upload': {
            const uploads = data[condition.field] || [];
            if (!Array.isArray(uploads)) return false;
            if (expected === undefined || expected === null || expected === '') return uploads.some(upload => upload && upload.file_id);
            return uploads.some(upload => upload && upload.document_type === expected && upload.file_id);
        }
        case 'missing_upload': {
            const uploads = data[condition.field] || [];
            if (!Array.isArray(uploads)) return true;
            if (expected === undefined || expected === null || expected === '') return !uploads.some(upload => upload && upload.file_id);
            return !uploads.some(upload => upload && upload.document_type === expected && upload.file_id);
        }
        default: return false;
    }
}
