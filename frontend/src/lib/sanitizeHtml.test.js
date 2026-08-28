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

    it('handles empty input, blocked tags, attributes and URL schemes', () => {
        const result = sanitizeHtml('<iframe src="https://example.com"></iframe><img src="vbscript:bad" onerror="bad"><img src="data:text/html;base64,AAAA"><img src="data:image/png;base64,AAAA" title="ok">');

        expect(result).not.toContain('iframe');
        expect(result).not.toContain('vbscript');
        expect(result).not.toContain('data:text/html');
        expect(result).not.toContain('onerror');
        expect(result).toContain('data:image/png;base64,AAAA');
        expect(result).toContain('title="ok"');
        expect(sanitizeHtml(null)).toBe('');
    });

    it('keeps safe relative and HTTPS links without adding rel to same-window links', () => {
        const result = sanitizeHtml('<a href="/intern">Intern</a><a href="https://example.com">Extern</a>');

        expect(result).toContain('href="/intern"');
        expect(result).toContain('href="https://example.com"');
        expect(result).not.toContain('noopener');
    });

    it('preserves every supported formatting element and attribute', () => {
        const tags = '<b>B</b><blockquote>Q</blockquote><br><code>C</code><div>D</div><em>E</em>' +
            '<h3>H3</h3><h4>H4</h4><hr><i>I</i><ol><li>L</li></ol><p>P</p><pre>Pre</pre>' +
            '<span class="mark">S</span><strong>Strong</strong><u>U</u><ul><li>X</li></ul>';
        const image = '<img alt="portrait" src="/safe.png" title="Profile">';
        const result = sanitizeHtml(tags + image);

        ['b', 'blockquote', 'br', 'code', 'div', 'em', 'h3', 'h4', 'hr', 'i', 'ol',
            'li', 'p', 'pre', 'span', 'strong', 'u', 'ul', 'img'].forEach(tag => {
            expect(result).toContain(`<${tag}`);
        });
        expect(result).toContain('class="mark"');
        expect(result).toContain('alt="portrait"');
        expect(result).toContain('src="/safe.png"');
        expect(result).toContain('title="Profile"');
        expect(sanitizeHtml('<b>B</b>')).toBe('<b>B</b>');
        expect(sanitizeHtml('<i>I</i>')).toBe('<i>I</i>');
        expect(sanitizeHtml('<u>U</u>')).toBe('<u>U</u>');
    });

    it('trims URL schemes before validating and removes arbitrary attributes', () => {
        const result = sanitizeHtml('<a href="  javascript:alert(1)" style="color:red" data-x="x">X</a>');
        expect(result).toBe('<a>X</a>');
    });

    it('rejects data URLs outside image src attributes and malformed image prefixes', () => {
        const result = sanitizeHtml(
            '<a href="data:image/png;base64,AAAA">link</a>' +
            '<span src="data:image/png;base64,AAAA">span</span>' +
            '<img src="data:invalid-data:image/png;base64,AAAA">'
        );
        expect(result).toBe('<a>link</a><span>span</span><img>');
    });

    it('handles empty URLs and only secures anchor targets', () => {
        const result = sanitizeHtml('<a href="">empty</a><span target="_blank">span</span>');
        expect(result).toBe('<a href="">empty</a><span target="_blank">span</span>');
    });

    it('returns an empty result when no DOM is available', () => {
        const originalDocument = global.document;
        Object.defineProperty(global, 'document', { configurable: true, value: undefined });
        try {
            expect(sanitizeHtml('<b>ignored</b>')).toBe('');
        } finally {
            Object.defineProperty(global, 'document', { configurable: true, value: originalDocument });
        }
    });
});
