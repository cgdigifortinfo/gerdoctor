export const paginationWindow = (totalCount = 0, page = 1, pageSize = '10') => {
    const all = pageSize === 'all';
    const numericPageSize = Number(pageSize);
    const totalPages = all ? 1 : Math.max(1, Math.ceil(totalCount / numericPageSize));
    const currentPage = Math.min(page, totalPages);
    const startIndex = all ? 0 : (currentPage - 1) * numericPageSize;
    const endIndex = all ? totalCount : Math.min(startIndex + numericPageSize, totalCount);
    return { all, currentPage, endIndex, startIndex, totalPages };
};
