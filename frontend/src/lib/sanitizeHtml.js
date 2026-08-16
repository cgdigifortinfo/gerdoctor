const ALLOWED_TAGS = new Set([
    'A', 'B', 'BLOCKQUOTE', 'BR', 'CODE', 'DIV', 'EM', 'H2', 'H3', 'H4',
    'HR', 'I', 'IMG', 'LI', 'OL', 'P', 'PRE', 'SPAN', 'STRONG', 'U', 'UL',
]);
const ALLOWED_ATTRIBUTES = new Set(['alt', 'class', 'href', 'src', 'target', 'title']);

const safeUrl = (value, allowDataImage = false) => {
    const normalized = String(value || '').trim().toLowerCase();
    if (!normalized) return true;
    if (normalized.startsWith('javascript:') || normalized.startsWith('vbscript:')) return false;
    if (normalized.startsWith('data:')) return allowDataImage && /^data:image\/(png|gif|jpeg|webp);base64,/.test(normalized);
    return true;
};

export function sanitizeHtml(html) {
    if (typeof document === 'undefined') return '';
    const template = document.createElement('template');
    template.innerHTML = String(html || '');
    for (const element of [...template.content.querySelectorAll('*')]) {
        if (!ALLOWED_TAGS.has(element.tagName)) {
            element.remove();
            continue;
        }
        for (const attribute of [...element.attributes]) {
            const name = attribute.name.toLowerCase();
            if (!ALLOWED_ATTRIBUTES.has(name) || name.startsWith('on')) element.removeAttribute(attribute.name);
        }
        if (element.hasAttribute('href') && !safeUrl(element.getAttribute('href'))) element.removeAttribute('href');
        if (element.hasAttribute('src') && !safeUrl(element.getAttribute('src'), element.tagName === 'IMG')) element.removeAttribute('src');
        if (element.tagName === 'A' && element.getAttribute('target') === '_blank') element.setAttribute('rel', 'noopener noreferrer');
    }
    return template.innerHTML;
}
