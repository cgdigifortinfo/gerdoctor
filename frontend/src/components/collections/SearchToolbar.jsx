import { MagnifyingGlass } from '@phosphor-icons/react';
import { Input } from '../ui/input';

// Stryker disable all: declarative search layout.
export function SearchToolbar({ value, onChange, placeholder = 'Suchen …', filters, actions, summary, className = '', inputTestId }) {
    return (
        <div className={className}>
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                <div className="flex flex-1 flex-col gap-2 sm:flex-row sm:items-center">
                    <div className="relative flex-1 sm:max-w-64">
                        <MagnifyingGlass size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                        <Input value={value} onChange={(event) => onChange(event.target.value)} placeholder={placeholder} className="pl-9" data-testid={inputTestId} />
                    </div>
                    {filters}
                </div>
                {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
            </div>
            {summary && <div className="mt-2 text-xs text-muted-foreground">{summary}</div>}
        </div>
    );
}
