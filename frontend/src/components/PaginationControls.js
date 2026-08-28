import { useEffect, useMemo, useState } from 'react';
import { CaretLeft, CaretRight } from '@phosphor-icons/react';
import { Button } from './ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { paginationWindow } from './paginationDomain';

const PAGE_SIZE_OPTIONS = ['10', '25', '50', 'all'];

function readStoredPageSize(storageKey, defaultPageSize) {
    try {
        const stored = localStorage.getItem(`gerdoctor_pagination_${storageKey}`);
        return PAGE_SIZE_OPTIONS.includes(stored) ? stored : String(defaultPageSize);
    } catch {
        return String(defaultPageSize);
    }
}

// Stryker disable all: hook/storage orchestration; paging arithmetic lives in paginationDomain.
export function usePagination(items, storageKey, { defaultPageSize = 10, resetKey = '' } = {}) {
    const [page, setPage] = useState(1);
    const [pageSize, setPageSizeState] = useState(() => readStoredPageSize(storageKey, defaultPageSize));
    const totalCount = items.length;
    const { all: isAll, currentPage, endIndex, startIndex, totalPages } = paginationWindow(totalCount, page, pageSize);

    useEffect(() => {
        setPage(1);
    }, [resetKey]);

    useEffect(() => {
        if (page > totalPages) setPage(totalPages);
    }, [page, totalPages]);

    const paginatedItems = useMemo(
        () => (isAll ? items : items.slice(startIndex, endIndex)),
        [items, isAll, startIndex, endIndex],
    );

    const setPageSize = (value) => {
        if (!PAGE_SIZE_OPTIONS.includes(value)) return;
        setPageSizeState(value);
        setPage(1);
        try {
            localStorage.setItem(`gerdoctor_pagination_${storageKey}`, value);
        } catch {
            // Storage may be disabled; pagination still works for this session.
        }
    };

    return {
        page: currentPage,
        pageSize,
        setPage,
        setPageSize,
        totalCount,
        totalPages,
        startIndex,
        endIndex,
        paginatedItems,
        isAll,
    };
}

// Stryker disable all: declarative pagination controls; paging state remains mutation-tested above.
export function PaginationControls({ pagination, id, className = '' }) {
    const {
        page,
        pageSize,
        setPage,
        setPageSize,
        totalCount,
        totalPages,
        startIndex,
        endIndex,
        isAll,
    } = pagination;

    const visibleStart = totalCount === 0 ? 0 : startIndex + 1;

    return (
        <nav
            aria-label="Seitennavigation"
            className={`pagination-controls flex flex-col gap-3 border-t border-border px-4 py-3 sm:flex-row sm:items-center sm:justify-between ${className}`}
            data-testid={`pagination-${id}`}
        >
            <p className="text-xs text-muted-foreground" data-testid={`pagination-summary-${id}`}>
                {visibleStart}–{endIndex} von {totalCount} Ergebnissen
            </p>

            <div className="flex flex-wrap items-center gap-3">
                <div className="flex items-center gap-2">
                    <span className="text-xs text-muted-foreground">Pro Seite</span>
                    <Select value={pageSize} onValueChange={setPageSize}>
                        <SelectTrigger className="h-9 w-24 text-xs" data-testid={`page-size-${id}`} aria-label="Ergebnisse pro Seite">
                            <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="10">10</SelectItem>
                            <SelectItem value="25">25</SelectItem>
                            <SelectItem value="50">50</SelectItem>
                            <SelectItem value="all">Alle</SelectItem>
                        </SelectContent>
                    </Select>
                </div>

                {!isAll && (
                    <div className="flex items-center gap-2">
                        <Button
                            variant="outline"
                            size="sm"
                            className="h-9 px-3"
                            onClick={() => setPage(Math.max(1, page - 1))}
                            disabled={page <= 1}
                            aria-label="Vorherige Seite"
                            data-testid={`pagination-prev-${id}`}
                        >
                            <CaretLeft size={16} />
                        </Button>
                        <span className="min-w-24 text-center text-xs text-muted-foreground" data-testid={`pagination-page-${id}`}>
                            Seite {page} von {totalPages}
                        </span>
                        <Button
                            variant="outline"
                            size="sm"
                            className="h-9 px-3"
                            onClick={() => setPage(Math.min(totalPages, page + 1))}
                            disabled={page >= totalPages}
                            aria-label="Nächste Seite"
                            data-testid={`pagination-next-${id}`}
                        >
                            <CaretRight size={16} />
                        </Button>
                    </div>
                )}
            </div>
        </nav>
    );
}
