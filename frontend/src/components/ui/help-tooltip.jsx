import { useCallback, useEffect, useId, useLayoutEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { Question } from '@phosphor-icons/react';

export function HelpTooltip({ content, label = 'Hilfe anzeigen', side = 'top', testId }) {
    const [open, setOpen] = useState(false);
    const [position, setPosition] = useState({ left: 0, top: 0 });
    const triggerRef = useRef(null);
    const tooltipId = useId();

    const updatePosition = useCallback(() => {
        const trigger = triggerRef.current;
        if (!trigger) return;
        const rect = trigger.getBoundingClientRect();
        const width = Math.min(288, window.innerWidth - 24);
        const left = side === 'right'
            ? Math.min(rect.right + 10, window.innerWidth - width - 12)
            : Math.max(12, Math.min(rect.left + rect.width / 2 - width / 2, window.innerWidth - width - 12));
        const top = side === 'right'
            ? Math.max(48, Math.min(rect.top + rect.height / 2, window.innerHeight - 48))
            : Math.max(12, rect.top - 10);
        setPosition({ left, top });
    }, [side]);

    useLayoutEffect(() => {
        if (open) updatePosition();
    }, [open, updatePosition]);
    useEffect(() => {
        if (!open) return undefined;
        const reposition = () => updatePosition();
        window.addEventListener('resize', reposition);
        window.addEventListener('scroll', reposition, true);
        return () => {
            window.removeEventListener('resize', reposition);
            window.removeEventListener('scroll', reposition, true);
        };
    }, [open, updatePosition]);

    if (!content) return null;
    return (
        <>
            <span
                ref={triggerRef}
                role="button"
                tabIndex={0}
                aria-label={label}
                aria-describedby={open ? tooltipId : undefined}
                onMouseEnter={() => setOpen(true)}
                onMouseLeave={() => setOpen(false)}
                onFocus={() => setOpen(true)}
                onBlur={() => setOpen(false)}
                onKeyDown={(event) => {
                    if (event.key === 'Escape') {
                        event.preventDefault();
                        event.stopPropagation();
                        setOpen(false);
                    }
                }}
                className="inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full align-middle text-muted-foreground transition-colors hover:bg-muted hover:text-[var(--brand-primary)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--brand-primary)]"
                data-testid={testId}
            >
                <Question size={15} weight="bold" />
            </span>
            {open && createPortal(
                <span
                    id={tooltipId}
                    role="tooltip"
                    data-testid={testId ? `${testId}-content` : undefined}
                    className={`pointer-events-none fixed z-[9999] w-72 rounded-lg bg-slate-950 px-3 py-2 text-left text-xs font-normal leading-5 text-white shadow-xl ${side === 'right' ? '-translate-y-1/2' : '-translate-y-full'}`}
                    style={{ left: position.left, top: position.top }}
                >
                    {content}
                </span>,
                document.body,
            )}
        </>
    );
}

export function HelpLabel({ children, help, className = '', testId }) {
    return <span className={`inline-flex items-center gap-1.5 ${className}`}>{children}<HelpTooltip content={help} testId={testId} /></span>;
}
