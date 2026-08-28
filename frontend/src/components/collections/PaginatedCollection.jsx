import { PaginationControls } from '../PaginationControls';
import { EmptyState } from './CollectionControls';

export function PaginatedCollection({ pagination, id, children, getKey = (item) => item.id, className = '', emptyTitle = 'Keine Einträge', emptyDescription, paginationClassName = '' }) {
    if (!pagination.totalCount) return <EmptyState title={emptyTitle} description={emptyDescription} />;
    return (
        <>
            <div className={className}>
                {pagination.paginatedItems.map((item, index) => <div key={getKey(item, index)}>{children(item, index)}</div>)}
            </div>
            <PaginationControls pagination={pagination} id={id} className={paginationClassName} />
        </>
    );
}
