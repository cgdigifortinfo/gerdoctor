import { statusStyle } from './uiDomain';

// Stryker disable all: declarative badge adapter; tone mapping lives in uiDomain.
export function StatusBadge({ children, tone = 'neutral', className = '', testId }) {
    return <span className={`inline-flex rounded-sm px-2 py-1 text-xs font-medium ${statusStyle(tone)} ${className}`} data-testid={testId}>{children}</span>;
}

export function TagBadge({ children, className = '', testId }) {
    return <StatusBadge tone="info" className={`py-0.5 ${className}`} testId={testId}>{children}</StatusBadge>;
}
