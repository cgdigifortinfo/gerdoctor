// Shared condition evaluator (mirrors backend helpers._evaluate_condition)
export function evaluateCondition(cond, stepDataByOrder) {
    const source = stepDataByOrder[cond.source_step_order];
    if (!source) return false;
    const data = source.data || {};
    const field = cond.field;
    const fieldValue = (field && field in data) ? data[field] : source.status;
    const expected = cond.value;
    switch (cond.operator) {
        case 'equals': return String(fieldValue) === String(expected);
        case 'not_equals': return String(fieldValue) !== String(expected);
        case 'contains': return String(fieldValue || '').includes(String(expected));
        case 'not_empty': return !!fieldValue && fieldValue !== '';
        case 'empty': return !fieldValue || fieldValue === '';
        case 'status_is': return source.status === expected;
        case 'status_not': return source.status !== expected;
        case 'has_upload': {
            const uploads = data[field] || [];
            return Array.isArray(uploads) && uploads.some(u => u.document_type === expected && u.file_id);
        }
        case 'missing_upload': {
            const uploads = data[field] || [];
            return !Array.isArray(uploads) || !uploads.some(u => u.document_type === expected && u.file_id);
        }
        default: return false;
    }
}

// Build a {order -> {data, status}} map from (steps, progress)
export function buildStepDataByOrder(steps, progress) {
    const progMap = {};
    (progress || []).forEach(p => { progMap[p.step_id] = p; });
    const byOrder = {};
    (steps || []).forEach(s => {
        const p = progMap[s.id || s.step_id] || {};
        byOrder[s.order] = { data: p.data || {}, status: p.status || 'pending' };
    });
    return byOrder;
}

// Compute hidden step IDs given steps + progress
export function getHiddenStepIds(steps, progress) {
    const byOrder = buildStepDataByOrder(steps, progress);
    const hidden = new Set();
    (steps || []).forEach(s => {
        for (const cond of (s.conditions || [])) {
            if (cond.action !== 'hide') continue;
            if (evaluateCondition(cond, byOrder)) { hidden.add(s.id || s.step_id); break; }
        }
    });
    return hidden;
}

// Filter a steps array, dropping any hidden for this user
export function filterVisibleSteps(steps, progress) {
    const hidden = getHiddenStepIds(steps, progress);
    return (steps || []).filter(s => !hidden.has(s.id || s.step_id));
}
