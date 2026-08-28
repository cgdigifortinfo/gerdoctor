// Stryker disable all: declarative card layout.
export function SectionCard({ title, description, toolbar, children, footer, className = '', contentClassName = 'p-4', testId }) {
    return (
        <section className={`rounded-sm border border-border bg-card ${className}`} data-testid={testId}>
            {(title || description || toolbar) && (
                <header className="flex flex-wrap items-start justify-between gap-3 border-b border-border p-4">
                    <div>
                        {title && <h2 className="text-lg font-semibold text-foreground">{title}</h2>}
                        {description && <p className="mt-1 text-xs text-muted-foreground">{description}</p>}
                    </div>
                    {toolbar && <div className="flex flex-wrap items-center gap-2">{toolbar}</div>}
                </header>
            )}
            <div className={contentClassName}>{children}</div>
            {footer && <footer className="border-t border-border">{footer}</footer>}
        </section>
    );
}

export const PageCard = SectionCard;
