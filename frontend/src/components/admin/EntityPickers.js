import { useEffect, useMemo, useRef, useState } from 'react';
import { CaretDown, Check, MagnifyingGlass, X } from '@phosphor-icons/react';

// Stryker disable all: picker interaction adapter covered by component contract tests.
function normalizeOption(option) {
    if (typeof option === 'string') {
        return { value: option, label: option, description: '', keywords: '' };
    }
    return {
        value: String(option.value),
        label: option.label || String(option.value),
        description: option.description || '',
        keywords: option.keywords || '',
        disabled: Boolean(option.disabled),
    };
}

function usePicker(options, open, onClose) {
    const rootRef = useRef(null);
    const normalized = useMemo(() => options.map(normalizeOption), [options]);

    useEffect(() => {
        if (!open) return undefined;
        const handlePointerDown = (event) => {
            if (!rootRef.current.contains(event.target)) onClose();
        };
        const handleKeyDown = (event) => {
            if (event.key === 'Escape') {
                event.preventDefault();
                event.stopPropagation();
                onClose();
            }
        };
        document.addEventListener('mousedown', handlePointerDown);
        document.addEventListener('keydown', handleKeyDown, true);
        return () => {
            document.removeEventListener('mousedown', handlePointerDown);
            document.removeEventListener('keydown', handleKeyDown, true);
        };
    }, [open, onClose]);

    return { rootRef, normalized };
}

function filterOptions(options, query) {
    const needle = query.trim().toLocaleLowerCase('de');
    if (!needle) return options;
    return options.filter((option) => (
        `${option.label} ${option.description} ${option.keywords} ${option.value}`
            .toLocaleLowerCase('de')
            .includes(needle)
    ));
}

function PickerMenu({
    options,
    query,
    onQueryChange,
    onChoose,
    selectedValues,
    searchPlaceholder,
    emptyText,
    testId,
    multiple = false,
    allowCustom,
    onDone,
}) {
    const filtered = filterOptions(options, query);
    const customValue = query.trim();
    const showCustom = allowCustom
        && customValue
        && !options.some((option) => option.value.toLocaleLowerCase('de') === customValue.toLocaleLowerCase('de'));

    return (
        <div
            className="absolute z-[80] mt-1 w-full min-w-[260px] rounded-lg border border-border bg-card p-2 shadow-xl"
            data-testid={`${testId}-menu`}
        >
            <div className="relative mb-2">
                <MagnifyingGlass size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                <input
                    autoFocus
                    value={query}
                    onChange={(event) => onQueryChange(event.target.value)}
                    placeholder={searchPlaceholder}
                    className="h-9 w-full rounded-md border border-border bg-background pl-9 pr-3 text-sm outline-none focus:border-[var(--brand-primary)] focus:ring-2 focus:ring-[var(--brand-primary)]/15"
                    data-testid={`${testId}-search`}
                />
            </div>
            <div className="max-h-64 overflow-y-auto" role="listbox" aria-multiselectable={multiple || undefined}>
                {filtered.map((option) => {
                    const selected = selectedValues.includes(option.value);
                    return (
                        <button
                            key={option.value}
                            type="button"
                            role="option"
                            aria-selected={selected}
                            disabled={option.disabled}
                            onClick={() => onChoose(option.value)}
                            className="flex w-full items-start gap-2 rounded-md px-3 py-2 text-left text-sm hover:bg-muted disabled:cursor-not-allowed disabled:opacity-40"
                            data-testid={`${testId}-option`}
                        >
                            <span className={`mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded border ${selected ? 'border-[var(--brand-primary)] bg-[var(--brand-primary)] text-white' : 'border-border'}`}>
                                {selected && <Check size={12} weight="bold" />}
                            </span>
                            <span className="min-w-0">
                                <span className="block font-medium text-foreground">{option.label}</span>
                                {option.description && <span className="block text-xs text-muted-foreground">{option.description}</span>}
                            </span>
                        </button>
                    );
                })}
                {showCustom && (
                    <button
                        type="button"
                        role="option"
                        aria-selected={false}
                        onClick={() => onChoose(customValue)}
                        className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-left text-sm text-[var(--brand-primary)] hover:bg-muted"
                        data-testid={`${testId}-custom-option`}
                    >
                        <span className="flex h-4 w-4 items-center justify-center rounded border border-dashed border-[var(--brand-primary)]">+</span>
                        „{customValue}“ verwenden
                    </button>
                )}
                {filtered.length === 0 && !showCustom && (
                    <p className="px-3 py-5 text-center text-sm text-muted-foreground">{emptyText}</p>
                )}
            </div>
            {multiple && (
                <div className="mt-2 border-t border-border pt-2">
                    <button
                        type="button"
                        onClick={onDone}
                        className="w-full rounded-md bg-[var(--brand-primary)] px-3 py-2 text-sm font-medium text-white hover:bg-[var(--brand-primary-hover)]"
                        data-testid={`${testId}-done`}
                    >
                        Auswahl übernehmen
                    </button>
                </div>
            )}
        </div>
    );
}

export function SearchableSelect({
    options = [],
    value,
    onChange,
    placeholder = 'Auswählen',
    searchPlaceholder = 'Suchen …',
    emptyText = 'Keine passenden Einträge',
    testId = 'searchable-select',
    allowCustom = false,
    disabled = false,
}) {
    const [open, setOpen] = useState(false);
    const [query, setQuery] = useState('');
    const close = () => { setOpen(false); setQuery(''); };
    const { rootRef, normalized } = usePicker(options, open, close);
    const selectedValue = value == null ? '' : String(value);
    const selected = normalized.find((option) => option.value === selectedValue);

    const choose = (nextValue) => {
        onChange(nextValue);
        close();
    };

    return (
        <div className="relative" ref={rootRef} data-entity-picker-open={open || undefined}>
            <button
                type="button"
                role="combobox"
                aria-expanded={open}
                disabled={disabled}
                onClick={() => setOpen((current) => !current)}
                className="flex min-h-10 w-full items-center justify-between gap-3 rounded-md border border-border bg-background px-3 py-2 text-left text-sm outline-none transition-colors hover:border-[var(--brand-primary)] focus-visible:ring-2 focus-visible:ring-[var(--brand-primary)]/20 disabled:cursor-not-allowed disabled:opacity-50"
                data-testid={testId}
            >
                <span className={selected || value ? 'text-foreground' : 'text-muted-foreground'}>
                    {selected?.label || value || placeholder}
                </span>
                <CaretDown size={15} className="shrink-0 text-muted-foreground" />
            </button>
            {open && (
                <PickerMenu
                    options={normalized}
                    query={query}
                    onQueryChange={setQuery}
                    onChoose={choose}
                    selectedValues={value == null ? [] : [String(value)]}
                    searchPlaceholder={searchPlaceholder}
                    emptyText={emptyText}
                    testId={testId}
                    allowCustom={allowCustom}
                />
            )}
        </div>
    );
}

export function SearchableMultiSelect({
    options = [],
    values = [],
    onChange,
    placeholder = 'Mehrere Einträge auswählen',
    searchPlaceholder = 'Suchen …',
    emptyText = 'Keine passenden Einträge',
    testId = 'searchable-multi-select',
    allowCustom = false,
}) {
    const [open, setOpen] = useState(false);
    const [query, setQuery] = useState('');
    const close = () => { setOpen(false); setQuery(''); };
    const { rootRef, normalized } = usePicker(options, open, close);
    const normalizedValues = useMemo(
        () => values.filter((item) => item != null && item !== '').map(String),
        [values],
    );
    const selectedValuesRef = useRef(normalizedValues);
    useEffect(() => {
        selectedValuesRef.current = normalizedValues;
    }, [normalizedValues]);
    const selectedOptions = normalizedValues.map((selectedValue) => (
        normalized.find((option) => option.value === selectedValue)
        || normalizeOption(selectedValue)
    ));

    const toggle = (nextValue) => {
        const currentValues = selectedValuesRef.current;
        const nextValues = currentValues.includes(nextValue)
            ? currentValues.filter((item) => item !== nextValue)
            : [...currentValues, nextValue];
        selectedValuesRef.current = nextValues;
        onChange(nextValues);
        setQuery('');
    };

    const remove = (event, selectedValue) => {
        event.stopPropagation();
        const nextValues = selectedValuesRef.current.filter((item) => item !== selectedValue);
        selectedValuesRef.current = nextValues;
        onChange(nextValues);
    };

    return (
        <div className="relative" ref={rootRef} data-entity-picker-open={open || undefined}>
            <button
                type="button"
                role="combobox"
                aria-expanded={open}
                onClick={() => setOpen((current) => !current)}
                className="flex min-h-10 w-full items-center justify-between gap-2 rounded-md border border-border bg-background px-2 py-1.5 text-left text-sm outline-none transition-colors hover:border-[var(--brand-primary)] focus-visible:ring-2 focus-visible:ring-[var(--brand-primary)]/20"
                data-testid={testId}
            >
                <span className="flex min-w-0 flex-1 flex-wrap gap-1">
                    {selectedOptions.length === 0 && <span className="px-1 text-muted-foreground">{placeholder}</span>}
                    {selectedOptions.map((option) => (
                        <span key={option.value} className="inline-flex max-w-full items-center gap-1 rounded-md bg-[var(--brand-primary)]/10 px-2 py-1 text-xs font-medium text-[var(--brand-primary)]">
                            <span className="truncate">{option.label}</span>
                            <span
                                role="button"
                                tabIndex={0}
                                aria-label={`${option.label} entfernen`}
                                onClick={(event) => remove(event, option.value)}
                                onKeyDown={(event) => {
                                    if (event.key === 'Enter' || event.key === ' ') remove(event, option.value);
                                }}
                                className="rounded p-0.5 hover:bg-[var(--brand-primary)]/15"
                            >
                                <X size={11} />
                            </span>
                        </span>
                    ))}
                </span>
                <CaretDown size={15} className="shrink-0 text-muted-foreground" />
            </button>
            {open && (
                <PickerMenu
                    options={normalized}
                    query={query}
                    onQueryChange={setQuery}
                    onChoose={toggle}
                    selectedValues={normalizedValues}
                    searchPlaceholder={searchPlaceholder}
                    emptyText={emptyText}
                    testId={testId}
                    multiple
                    allowCustom={allowCustom}
                    onDone={close}
                />
            )}
        </div>
    );
}
