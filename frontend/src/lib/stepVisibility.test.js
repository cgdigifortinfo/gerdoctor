import {
    buildStepDataByOrder,
    evaluateCondition,
    filterVisibleSteps,
    getHiddenStepIds,
    simulateJourney,
} from '../features/steps';


describe('multi-value step conditions', () => {
    const byOrder = {
        4: {
            status: 'completed',
            data: {
                decision: 'partner',
                regions: ['Berlin', 'Hamburg'],
            },
        },
    };

    test('one_of matches a scalar field against selected values', () => {
        expect(evaluateCondition({
            source_step_order: 4,
            field: 'decision',
            operator: 'one_of',
            value: ['upload', 'partner'],
        }, byOrder)).toBe(true);
    });

    test('not_one_of excludes selected scalar values', () => {
        expect(evaluateCondition({
            source_step_order: 4,
            field: 'decision',
            operator: 'not_one_of',
            value: ['upload', 'selbst'],
        }, byOrder)).toBe(true);
    });

    test('one_of supports array-valued source fields', () => {
        expect(evaluateCondition({
            source_step_order: 4,
            field: 'regions',
            operator: 'one_of',
            value: ['Bayern', 'Hamburg'],
        }, byOrder)).toBe(true);
    });

    test.each([
        ['equals', 'partner', true],
        ['equals', 'upload', false],
        ['not_equals', 'upload', true],
        ['contains', 'art', true],
        ['not_empty', null, true],
        ['empty', null, false],
        ['status_is', 'completed', true],
        ['status_not', 'pending', true],
        ['unknown', null, false],
    ])('%s evaluates its positive and negative cases', (operator, value, expected) => {
        expect(evaluateCondition({ source_step_order: 4, field: operator.startsWith('status_') ? undefined : 'decision', operator, value }, byOrder)).toBe(expected);
    });

    test('compound all_of and any_of recurse into their child conditions', () => {
        const equalsPartner = { source_step_order: 4, field: 'decision', operator: 'equals', value: 'partner' };
        const equalsUpload = { ...equalsPartner, value: 'upload' };
        expect(evaluateCondition({ all_of: [equalsPartner, { ...equalsPartner, operator: 'not_empty' }] }, byOrder)).toBe(true);
        expect(evaluateCondition({ all_of: [equalsPartner, equalsUpload] }, byOrder)).toBe(false);
        expect(evaluateCondition({ any_of: [equalsUpload, equalsPartner] }, byOrder)).toBe(true);
        expect(evaluateCondition({ any_of: [equalsUpload] }, byOrder)).toBe(false);
        expect(evaluateCondition({ source_step_order: 99, operator: 'empty' }, byOrder)).toBe(false);
    });

    test('upload operators distinguish type, any upload, invalid values and missing uploads', () => {
        const context = { 1: { status: 'completed', data: { documents: [null, { file_id: 'a', document_type: 'Diplom' }] } } };
        const condition = (operator, value, field = 'documents') => ({ source_step_order: 1, field, operator, value });
        expect(evaluateCondition(condition('has_upload', 'Diplom'), context)).toBe(true);
        expect(evaluateCondition(condition('has_upload', 'Other'), context)).toBe(false);
        expect(evaluateCondition(condition('has_upload', ''), context)).toBe(true);
        expect(evaluateCondition(condition('has_upload', null), context)).toBe(true);
        expect(evaluateCondition(condition('has_upload', undefined, 'invalid'), { 1: { data: { invalid: 'no-array' } } })).toBe(false);
        expect(evaluateCondition(condition('missing_upload', 'Diplom'), context)).toBe(false);
        expect(evaluateCondition(condition('missing_upload', 'Other'), context)).toBe(true);
        expect(evaluateCondition(condition('missing_upload', ''), context)).toBe(false);
        expect(evaluateCondition(condition('missing_upload', undefined, 'invalid'), { 1: { data: { invalid: 'no-array' } } })).toBe(true);
        expect(evaluateCondition(condition('has_upload', undefined, 'absent'), context)).toBe(false);
        expect(evaluateCondition(condition('missing_upload', undefined, 'absent'), context)).toBe(true);
    });

    test('normalizes scalar choices, empty data and all boolean branches', () => {
        expect(evaluateCondition({ source_step_order: 4, field: 'decision', operator: 'one_of', value: 'partner' }, byOrder)).toBe(true);
        expect(evaluateCondition({ source_step_order: 4, field: 'regions', operator: 'not_one_of', value: 'Bayern' }, byOrder)).toBe(true);
        expect(evaluateCondition({ source_step_order: 4, field: 'regions', operator: 'not_one_of', value: 'Berlin' }, byOrder)).toBe(false);
        const emptyData = { 1: { status: 'pending', data: null } };
        expect(evaluateCondition({ source_step_order: 1, field: 'missing', operator: 'contains', value: 'x' }, emptyData)).toBe(false);
        expect(evaluateCondition({ source_step_order: 1, field: 'missing', operator: 'not_empty' }, emptyData)).toBe(false);
        expect(evaluateCondition({ source_step_order: 1, field: 'missing', operator: 'empty' }, emptyData)).toBe(true);
        expect(evaluateCondition({ source_step_order: 4, field: 'decision', operator: 'not_equals', value: 'partner' }, byOrder)).toBe(false);
        expect(evaluateCondition({ source_step_order: 4, field: 'decision', operator: 'contains', value: 'zzz' }, byOrder)).toBe(false);
        expect(evaluateCondition({ source_step_order: 4, field: 'decision', operator: 'not_empty' }, byOrder)).toBe(true);
        expect(evaluateCondition({ source_step_order: 4, field: 'decision', operator: 'empty' }, byOrder)).toBe(false);
        expect(evaluateCondition({ source_step_order: 4, operator: 'status_is', value: 'pending' }, byOrder)).toBe(false);
        expect(evaluateCondition({ source_step_order: 4, operator: 'status_not', value: 'completed' }, byOrder)).toBe(false);
        expect(evaluateCondition({ source_step_order: 1, field: 'missing', operator: 'empty' }, { 1: { data: { missing: 0 } } })).toBe(true);
        expect(evaluateCondition({ source_step_order: 1, field: 'missing', operator: 'not_empty' }, { 1: { data: { missing: 0 } } })).toBe(false);
    });
});

describe('step visibility composition', () => {
    const steps = [
        { id: 'decision', order: 1 },
        { id: 'hidden', order: 2, conditions: [{ action: 'hide', source_step_order: 1, field: 'decision', operator: 'equals', value: 'partner' }] },
        { step_id: 'visible', order: 3, conditions: [{ action: 'block', source_step_order: 1, field: 'decision', operator: 'equals', value: 'partner' }] },
    ];
    const progress = [{ step_id: 'decision', status: 'completed', data: { decision: 'partner' } }];

    test('builds defaults and maps progress by id and order', () => {
        expect(buildStepDataByOrder(steps, progress)).toEqual({
            1: { data: { decision: 'partner' }, status: 'completed' },
            2: { data: {}, status: 'pending' },
            3: { data: {}, status: 'pending' },
        });
        expect(buildStepDataByOrder(null, null)).toEqual({});
    });

    test('hides only matching hide conditions and filters the same ids', () => {
        expect([...getHiddenStepIds(steps, progress)]).toEqual(['hidden']);
        expect(filterVisibleSteps(steps, progress).map(step => step.id || step.step_id)).toEqual(['decision', 'visible']);
        expect(filterVisibleSteps(null, null)).toEqual([]);
        expect([...getHiddenStepIds([
            { id: 'decision', order: 1 },
            { step_id: 'fallback', order: 2, conditions: [
                { action: 'hide', source_step_order: 1, field: 'decision', operator: 'equals', value: 'upload' },
                { action: 'hide', source_step_order: 1, field: 'decision', operator: 'equals', value: 'partner' },
            ] },
            { id: 'plain', order: 3 },
        ], progress)]).toEqual(['fallback']);
    });

    test('simulates hide, block and auto-complete independently in sorted order', () => {
        const simulated = simulateJourney([
            ...steps,
            { id: 'auto', order: 4, conditions: [{ action: 'auto_complete', source_step_order: 1, field: 'decision', operator: 'equals', value: 'partner' }] },
        ], { 1: { data: { decision: 'partner' } } });
        expect([...simulated.hidden]).toEqual(['hidden']);
        expect([...simulated.blocked]).toEqual(['visible']);
        expect([...simulated.autoComplete]).toEqual(['auto']);
        expect(simulateJourney()).toEqual({ hidden: new Set(), blocked: new Set(), autoComplete: new Set() });
        expect(simulateJourney([
            { step_id: 'ignored', order: 2, conditions: [
                { action: 'hide', source_step_order: 1, field: 'decision', operator: 'equals', value: 'upload' },
                { action: 'unknown', source_step_order: 1, operator: 'status_is', value: 'pending' },
            ] },
            { id: 'plain', order: 1 },
        ], { 1: { status: 'pending' } })).toEqual({ hidden: new Set(), blocked: new Set(), autoComplete: new Set() });
        expect(simulateJourney([
            { id: 'source', order: 1 },
            { id: 'target', order: 2, conditions: [
                { action: 'hide', source_step_order: 1, field: 'choice', operator: 'equals', value: 'yes' },
                { action: 'block', source_step_order: 1, field: 'choice', operator: 'equals', value: 'yes' },
                { action: 'auto_complete', source_step_order: 1, field: 'choice', operator: 'equals', value: 'yes' },
            ] },
        ], { 1: { data: { choice: 'no' }, status: 'in_progress' } })).toEqual({
            hidden: new Set(), blocked: new Set(), autoComplete: new Set(),
        });
    });
});
