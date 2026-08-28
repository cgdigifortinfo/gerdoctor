import { paginationWindow } from './paginationDomain';

test('paginationWindow calculates first, bounded, partial, empty and all pages', () => {
    expect(paginationWindow()).toStrictEqual({ all: false, currentPage: 1, startIndex: 0, endIndex: 0, totalPages: 1 });
    expect(paginationWindow(60, 1, '25')).toStrictEqual({ all: false, currentPage: 1, startIndex: 0, endIndex: 25, totalPages: 3 });
    expect(paginationWindow(60, 9, '25')).toStrictEqual({ all: false, currentPage: 3, startIndex: 50, endIndex: 60, totalPages: 3 });
    expect(paginationWindow(0, 2, '10')).toStrictEqual({ all: false, currentPage: 1, startIndex: 0, endIndex: 0, totalPages: 1 });
    expect(paginationWindow(0, 1, 'all')).toStrictEqual({ all: true, currentPage: 1, startIndex: 0, endIndex: 0, totalPages: 1 });
    expect(paginationWindow(3, 4, 'all')).toStrictEqual({ all: true, currentPage: 1, startIndex: 0, endIndex: 3, totalPages: 1 });
});
