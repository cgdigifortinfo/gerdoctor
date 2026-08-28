export function DataTable({ children, className = '', testId }) {
    return <div className="overflow-x-auto"><table className={`w-full ${className}`} data-testid={testId}>{children}</table></div>;
}

export function TableHeader({ children, className = '' }) {
    return <thead className={`bg-background ${className}`}>{children}</thead>;
}

export function TableHeading({ children, className = '', ...props }) {
    return <th className={`px-4 py-3 text-left text-xs font-bold uppercase tracking-wider text-muted-foreground ${className}`} {...props}>{children}</th>;
}

export function TableRow({ children, className = '', ...props }) {
    return <tr className={`border-t border-border table-row-hover ${className}`} {...props}>{children}</tr>;
}

export function TableCell({ children, className = '', ...props }) {
    return <td className={`px-4 py-3 ${className}`} {...props}>{children}</td>;
}

export function TableActions({ children, className = '' }) {
    return <div className={`flex items-center gap-2 ${className}`}>{children}</div>;
}
