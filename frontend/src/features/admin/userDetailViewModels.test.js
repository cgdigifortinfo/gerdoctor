import {
    completionPercent,
    displayFieldValue,
    effectivePermissionLabel,
    fieldPresentation,
    hasVisibleProgressData,
    historyAction,
    partnerNameForSubmission,
    progressData,
    stepForProgress,
} from './userDetailViewModels';

describe('userDetailViewModels', () => {
    test('builds permission and completion labels from normalized values', () => {
        expect(effectivePermissionLabel(['*'])).toBe('Vollzugriff');
        expect(effectivePermissionLabel(['users.read'])).toBe('1 wirksame Rechte');
        expect(effectivePermissionLabel()).toBe('0 wirksame Rechte');
        expect(completionPercent(42)).toBe(42);
        expect(completionPercent(null)).toBe(0);
        expect(completionPercent()).toBe(0);
    });

    test('finds steps and distinguishes visible progress data', () => {
        const step = { id: 's1' };
        expect(stepForProgress([step], 's1')).toBe(step);
        expect(stepForProgress([step], 'missing')).toBeUndefined();
        expect(stepForProgress()).toBeUndefined();
        expect(progressData(null)).toStrictEqual({});
        expect(hasVisibleProgressData({ skipped: true })).toBe(false);
        expect(hasVisibleProgressData()).toBe(false);
        expect(hasVisibleProgressData({ skipped: false, answer: '' })).toBe(true);
    });

    test('prefers current field metadata and reports removed historical fields', () => {
        const progress = { step_snapshot: { fields: [{ name: 'given_name', label: 'Alt', field_type: 'text' }] } };
        expect(fieldPresentation({ fields: [{ name: 'given_name', label: 'Neu', field_type: 'file' }] }, progress, 'given_name')).toStrictEqual({ label: 'Neu', type: 'file', removed: false });
        const historyWithEarlierField = { step_snapshot: { fields: [{ name: 'other', label: 'Falsch' }, ...progress.step_snapshot.fields] } };
        expect(fieldPresentation({}, historyWithEarlierField, 'given_name')).toStrictEqual({ label: 'Alt', type: 'text', removed: true });
        expect(fieldPresentation({ fields: undefined }, { step_snapshot: { fields: undefined } }, 'given_name')).toStrictEqual({ label: 'given name', type: '', removed: false });
        expect(fieldPresentation(undefined, {}, 'given_name')).toStrictEqual({ label: 'given name', type: '', removed: false });
    });

    test('formats scalar, collection, object and missing field values', () => {
        expect(displayFieldValue(['a', 'b'])).toBe('a, b');
        expect(displayFieldValue({ ok: true })).toBe('{"ok":true}');
        expect(displayFieldValue('text')).toBe('text');
        expect(displayFieldValue(false)).toBe('false');
        expect(displayFieldValue(null)).toBe('-');
    });

    test('resolves submission partners and every history state', () => {
        expect(partnerNameForSubmission([{ id: 'p1', name: 'Schule' }], 'p1')).toBe('Schule');
        expect(partnerNameForSubmission([], 'p1')).toBe('Unknown Partner');
        expect(partnerNameForSubmission()).toBe('Unknown Partner');
        expect(historyAction('completed')).toStrictEqual({ done: true, inProgress: false, label: 'Abgeschlossen' });
        expect(historyAction('in_progress')).toStrictEqual({ done: false, inProgress: true, label: 'In Bearbeitung' });
        expect(historyAction('pending')).toStrictEqual({ done: false, inProgress: false, label: 'pending' });
        expect(historyAction()).toStrictEqual({ done: false, inProgress: false, label: '' });
    });
});
