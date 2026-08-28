export const CONTENT_FIELD_TYPES = new Set(['heading', 'paragraph', 'html', 'image', 'divider']);
export const CHOICE_FIELD_TYPES = new Set(['select', 'selectbox', 'radio', 'multiselect', 'decision']);

export const TYPE_LABELS = {
    text: 'Textfeld', textarea: 'Textbereich', email: 'E-Mail', phone: 'Telefon', number: 'Zahl',
    date: 'Datum', time: 'Uhrzeit', checkbox: 'Checkbox', selectbox: 'Auswahlliste', radio: 'Einzelauswahl',
    multiselect: 'Mehrfachauswahl', decision: 'Entscheidungskarten', file: 'Datei-Upload',
    multiupload: 'Dokumentenliste', heading: 'Überschrift', paragraph: 'Textabsatz', html: 'HTML-Inhalt',
    image: 'Bild', divider: 'Trennlinie',
};

export const slugify = (value) => String(value ?? '')
    .toLowerCase()
    .replace(/[^a-z0-9_]+/g, '_')
    .replace(/^_+|_+$/g, '');

// Stryker disable next-line MethodExpression: the random suffix length is an opaque ID implementation detail.
export const makeFieldId = (type) => `${type}_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 7)}`;

export function createField(type, index = 0) {
    const label = TYPE_LABELS[type] ?? 'Neues Feld';
    const field = {
        id: makeFieldId(type),
        name: `${slugify(label)}_${index + 1}`,
        field_type: type,
        label,
        help_text: '',
        placeholder: '',
        required: false,
        width: 'full',
    };
    if (CHOICE_FIELD_TYPES.has(type)) field.options = ['Option 1', 'Option 2'];
    if (type === 'multiupload') Object.assign(field, { options: ['Dokument'], accept: '.pdf,.png,.jpg,.jpeg,.doc,.docx', multiple: true });
    if (type === 'file') Object.assign(field, { accept: '.pdf,.png,.jpg,.jpeg,.doc,.docx', multiple: false });
    if (type === 'textarea') field.rows = 4;
    if (type === 'heading') Object.assign(field, { content: 'Neue Überschrift', heading_level: 2 });
    if (type === 'paragraph') field.content = 'Hier kann ein erklärender Text stehen.';
    if (type === 'html') field.content = '<p>Hier kann formatierter Inhalt stehen.</p>';
    if (type === 'image') Object.assign(field, { image_url: '', alt_text: '', caption: '' });
    return field;
}

export const optionValue = (option) => typeof option === 'object' && option !== null
    ? String(option.value ?? option.label ?? '')
    : String(option ?? '');

export const optionLabel = (option) => typeof option === 'object' && option !== null
    ? String(option.label ?? option.value ?? '')
    : String(option ?? '');

export function updateFieldOption(options, fieldType, index, key, value) {
    const next = [...options];
    const current = next[index];
    const currentObject = current && typeof current === 'object' ? current : {};
    if (fieldType === 'decision' || currentObject === current) {
        next[index] = {
            ...currentObject,
            value: key === 'value' ? value : optionValue(current),
            label: key === 'label' ? value : optionLabel(current),
        };
    } else {
        next[index] = value;
    }
    return next;
}

export function appendFieldOption(options, fieldType) {
    const number = options.length + 1;
    const option = fieldType === 'decision'
        ? { value: `option_${number}`, label: `Option ${number}` }
        : `Option ${number}`;
    return [...options, option];
}

export const removeFieldOption = (options, index) => options.filter((_, optionIndex) => optionIndex !== index);

export function moveField(fields, index, direction) {
    const target = index + direction;
    if (target < 0 || target >= fields.length) return fields;
    const next = [...fields];
    [next[index], next[target]] = [next[target], next[index]];
    return next;
}

export function duplicateField(fields, index) {
    const original = fields[index];
    const copy = {
        ...original,
        id: makeFieldId(original.field_type),
        name: `${original.name || original.field_type}_kopie`,
        label: `${original.label || TYPE_LABELS[original.field_type]} (Kopie)`,
    };
    const next = [...fields];
    next.splice(index + 1, 0, copy);
    return { fields: next, selectedId: copy.id };
}
