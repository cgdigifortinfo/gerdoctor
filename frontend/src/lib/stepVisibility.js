// Shared condition evaluator (mirrors backend helpers._evaluate_condition)
export function evaluateCondition(cond, stepDataByOrder) {
    // Compound conditions
    if (Array.isArray(cond?.all_of)) {
        return cond.all_of.every(c => evaluateCondition(c, stepDataByOrder));
    }
    if (Array.isArray(cond?.any_of)) {
        return cond.any_of.some(c => evaluateCondition(c, stepDataByOrder));
    }
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
            if (!Array.isArray(uploads)) return false;
            // Empty expected → any upload with a file_id qualifies
            if (expected === undefined || expected === null || expected === '') {
                return uploads.some(u => u && u.file_id);
            }
            return uploads.some(u => u.document_type === expected && u.file_id);
        }
        case 'missing_upload': {
            const uploads = data[field] || [];
            if (!Array.isArray(uploads)) return true;
            if (expected === undefined || expected === null || expected === '') {
                return !uploads.some(u => u && u.file_id);
            }
            return !uploads.some(u => u.document_type === expected && u.file_id);
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

// ===== Simulator =====
// Simulate what the flow would look like for a hypothetical profile.
// `profile` is a map of step_order -> {data, status} (status defaults to 'pending').
// Returns sets of step ids per state.
export function simulateJourney(steps, profile = {}) {
    const sorted = [...(steps || [])].sort((a, b) => a.order - b.order);
    // Build synthetic byOrder from profile data; assume steps with data are 'completed'
    const byOrder = {};
    sorted.forEach(s => {
        const entry = profile[s.order] || {};
        byOrder[s.order] = {
            data: entry.data || {},
            status: entry.status || (entry.data ? 'completed' : 'pending'),
        };
    });

    const hidden = new Set();
    const blocked = new Set();
    const autoComplete = new Set();

    sorted.forEach(s => {
        const sid = s.id || s.step_id;
        for (const cond of (s.conditions || [])) {
            if (evaluateCondition(cond, byOrder)) {
                if (cond.action === 'hide') hidden.add(sid);
                else if (cond.action === 'block') blocked.add(sid);
                else if (cond.action === 'auto_complete') autoComplete.add(sid);
            }
        }
    });
    return { hidden, blocked, autoComplete };
}

// Predefined profiles for the simulator
export const SIMULATOR_PROFILES = {
    none: {
        label: 'Keine Simulation',
        profile: null,
    },
    fresh: {
        label: 'Frischer User',
        profile: {
            1: { data: {
                anerkennungsstatus: 'Die Fachsprachenprüfung Medizin ist geplant',
                fachrichtung_gewuenscht: 'Allgemeinmedizin',
                anerkennungsverfahren_bundesland: 'Bayern',
            }, status: 'completed' },
        },
    },
    upload_path: {
        label: 'Upload-Pfad (Dokumente)',
        profile: {
            1: { data: {
                anerkennungsstatus: 'Die Fachsprachenprüfung Medizin ist geplant',
                fachrichtung_gewuenscht: 'Innere Medizin',
                anerkennungsverfahren_bundesland: 'Berlin',
            }, status: 'completed' },
            2: { data: { decision: 'upload' }, status: 'completed' },
            3: { data: { documents: [{ file_id: 'sim-doc', document_type: 'Diplom', filename: 'diplom.pdf' }] }, status: 'completed' },
        },
    },
    partner_path: {
        label: 'Partner-Pfad',
        profile: {
            1: { data: {
                anerkennungsstatus: 'Die Fachsprachenprüfung Medizin ist geplant',
                fachrichtung_gewuenscht: 'Pädiatrie',
                anerkennungsverfahren_bundesland: 'Hamburg',
            }, status: 'completed' },
            2: { data: { decision: 'partner' }, status: 'completed' },
        },
    },
    already_approbated: {
        label: 'Bereits approbiert',
        profile: {
            1: { data: {
                anerkennungsstatus: 'Ich bin in Deutschland approbiert',
                fachrichtung_gewuenscht: 'Kardiologie',
                anerkennungsverfahren_bundesland: 'Berlin',
            }, status: 'completed' },
        },
    },
};
