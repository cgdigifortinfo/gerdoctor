/** @jest-environment @stryker-mutator/jest-runner/jest-env/node */
import { sanitizeHtml } from './sanitizeHtml';

test('returns an empty result when no DOM is available', () => {
    expect(sanitizeHtml('<b>ignored</b>')).toBe('');
});
