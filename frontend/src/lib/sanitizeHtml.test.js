import { sanitizeHtml } from './sanitizeHtml';

describe('sanitizeHtml', () => {
    it('keeps useful formatting and removes executable markup', () => {
        const result = sanitizeHtml('<h2>Hallo</h2><script>alert(1)</script><p onclick="alert(2)">Text</p>');

        expect(result).toContain('<h2>Hallo</h2>');
        expect(result).toContain('<p>Text</p>');
        expect(result).not.toContain('script');
        expect(result).not.toContain('onclick');
    });

    it('blocks javascript URLs and secures new tabs', () => {
        const result = sanitizeHtml('<a href="javascript:alert(1)">Unsicher</a><a href="https://example.com" target="_blank">Sicher</a>');

        expect(result).not.toContain('javascript:');
        expect(result).toContain('rel="noopener noreferrer"');
    });
});
