const EMPTY_ARRAY = Object.freeze([]);

export function asString(value) {
    return value === undefined || value === null ? '' : String(value);
}

export function asArray(value) {
    return Array.isArray(value) ? value : EMPTY_ARRAY;
}

export function asObject(value) {
    return value && typeof value === 'object' && !Array.isArray(value) ? value : {};
}
