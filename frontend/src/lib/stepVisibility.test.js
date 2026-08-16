import { evaluateCondition } from './stepVisibility';


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
});
