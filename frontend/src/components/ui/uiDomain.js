const STATUS_STYLES = Object.freeze({
    success: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300',
    warning: 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300',
    danger: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300',
    neutral: 'bg-muted text-muted-foreground',
    info: 'bg-[var(--brand-primary)]/10 text-[var(--brand-primary)]',
});

export const statusStyle = (tone = 'neutral') => STATUS_STYLES[tone] ?? STATUS_STYLES.neutral;

export const tooltipPosition = (rect, side = 'top', viewportWidth = 0, viewportHeight = 0) => {
    const width = Math.min(288, viewportWidth - 24);
    if (side === 'right') return {
        left: Math.min(rect.right + 10, viewportWidth - width - 12),
        top: Math.max(48, Math.min(rect.top + rect.height / 2, viewportHeight - 48)),
    };
    return {
        left: Math.max(12, Math.min(rect.left + rect.width / 2 - width / 2, viewportWidth - width - 12)),
        top: Math.max(12, rect.top - 10),
    };
};
