import { Button } from '../ui/button';

// Stryker disable all: declarative collection controls.
export function SegmentedControl({ value, onChange, options, className = '', testId, joined = false }) {
    return (
        <div
            className={`${joined ? 'inline-flex overflow-hidden rounded-sm border border-border' : 'flex gap-2 rounded-lg border border-border bg-card p-1.5'} ${className}`}
            data-testid={testId}
        >
            {options.filter((option) => !option.hidden).map((option, index) => joined ? (
                <button
                    key={option.value}
                    type="button"
                    onClick={() => onChange(option.value)}
                    className={`px-3 py-1.5 text-xs font-medium transition-colors ${index ? 'border-l border-border' : ''} ${value === option.value ? 'bg-[var(--brand-primary)] text-white' : 'bg-card text-muted-foreground hover:text-foreground'}`}
                    data-testid={option.testId}
                >
                    {option.label}
                </button>
            ) : (
                <Button
                    key={option.value}
                    type="button"
                    size="sm"
                    variant={value === option.value ? 'default' : 'ghost'}
                    onClick={() => onChange(option.value)}
                    data-testid={option.testId}
                >
                    {option.label}
                </Button>
            ))}
        </div>
    );
}

export function EmptyState({ title, description, icon: Icon, action, className = '', testId }) {
    return (
        <div className={`flex flex-col items-center justify-center py-10 text-center text-muted-foreground ${className}`} data-testid={testId}>
            {Icon && <Icon size={28} className="mb-2" />}
            <p className="font-medium text-foreground">{title}</p>
            {description && <p className="mt-1 max-w-md text-sm">{description}</p>}
            {action && <div className="mt-4">{action}</div>}
        </div>
    );
}

export function TableEmptyState({ colSpan, title, description, testId }) {
    return (
        <tr data-testid={testId}>
            <td colSpan={colSpan}>
                <EmptyState title={title} description={description} />
            </td>
        </tr>
    );
}
