import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { BarChart, PendingActivationPage, resolvePartnerDeepLink, scoreUserForPartner, Timeline, UserTable } from './PartnerDashboard';

jest.mock('react-router-dom', () => ({ useNavigate: () => jest.fn() }), { virtual: true });
jest.mock('../contexts/AuthContext', () => ({ useAuth: () => ({ user: {}, logout: jest.fn() }) }));
jest.mock('../contexts/LanguageContext', () => ({ useLanguage: () => ({ t: (key) => key }) }));
jest.mock('../lib/api', () => ({ partnerDashboardAPI: {}, filesAPI: { getUrl: (id) => `/file/${id}` }, formatApiError: () => 'error' }));
jest.mock('sonner', () => ({ toast: { success: jest.fn(), error: jest.fn() } }));
jest.mock('@phosphor-icons/react', () => new Proxy({}, { get: () => () => <i /> }));
jest.mock('../components/ThemeLangToggle', () => ({ ThemeLangToggle: () => <i /> }));
jest.mock('../components/Logo', () => ({ Logo: () => <i /> }));
jest.mock('../components/ui/button', () => ({ Button: ({ children, asChild, ...props }) => asChild ? <>{children}</> : <button {...props}>{children}</button> }));
jest.mock('../components/ui/select', () => ({
  Select: ({ children, value, onValueChange }) => <div>{children}<button data-testid={`select-${value}`} onClick={() => onValueChange(value === 'all' ? 'Cardiology' : 'all')}>select</button></div>,
  SelectContent: ({ children }) => <div>{children}</div>, SelectItem: ({ children }) => <span>{children}</span>, SelectTrigger: ({ children, ...props }) => <div {...props}>{children}</div>, SelectValue: () => <i />,
}));
jest.mock('../components/PaginationControls', () => ({ usePagination: (items) => ({ paginatedItems: items }), PaginationControls: ({ id }) => <div data-testid={`pagination-${id}`} /> }));

const t = (key) => key;
const users = [
  { id: '1', user_id: 'u1', user_name: 'Zed', user_email: 'z@x.de', field_of_study: 'Cardiology', bundesland: 'Berlin', completion_pct: 50, status: 'submitted', estimated_completion: '2026-08-10', created_at: '2026-01-02', service_step_title: 'Service', partner_work_completed: true, partner_work_completed_at: '2026-08-20' },
  { id: '2', user_name: 'Ada', user_email: 'a@x.de', field_of_study: 'Neurology', anerkennungsverfahren_bundesland: 'Bayern', completion_pct: 0, status: 'reviewed', estimated_completion: '2026-09-10', created_at: '', partner_milestone_step_title: 'Milestone', partner_work_completed: false },
  { id: '3', user_name: 'Ada', user_email: '', field_of_study: '', completion_pct: null, status: '', estimated_completion: '', service_step_id: 'step', step_id: 'legacy' },
];

test('partner matching scores specialty, both state fields and empty inputs', () => {
  expect(scoreUserForPartner(users[0], ['CARDIOLOGY', 'berlin'])).toBe(15);
  expect(scoreUserForPartner(users[1], ['neurology', 'bayern'])).toBe(15);
  expect(scoreUserForPartner({}, ['Berlin'])).toBe(0);
  expect(scoreUserForPartner(users[0])).toBe(0);
});

test('resolves every partner deep-link destination', () => {
  const active = { user_id: 'a', partner_work_completed: false };
  const completed = { user_id: 'c', partner_work_completed: true };
  const other = { user_id: 'o' };
  expect(resolvePartnerDeepLink('a', [active, completed], [other])).toEqual({ match: active, tab: 'my-users' });
  expect(resolvePartnerDeepLink('c', [active, completed], [other])).toEqual({ match: completed, tab: 'completed-users' });
  expect(resolvePartnerDeepLink('o', [active, completed], [other])).toEqual({ match: other, tab: 'other-users' });
  expect(resolvePartnerDeepLink('x', [active, completed], [other])).toBeNull();
});

test('bar chart and timeline cover missing, zero and populated datasets', () => {
  const first = render(<BarChart />); expect(screen.getByText('Keine Daten verfügbar')).toBeInTheDocument(); first.unmount();
  const zero = render(<BarChart data={[{ label: 'Zero', count: 0 }]} valueSuffix="%" />);
  expect(screen.getByText('0%')).toBeInTheDocument(); zero.unmount();
  const bars = render(<BarChart data={[{ label: 'A', count: 2 }, { label: 'B', count: 1 }]} accent="red" testid="bars" />);
  expect(screen.getByTestId('bars')).toBeInTheDocument(); bars.unmount();
  const none = render(<Timeline />); expect(none.container).toBeEmptyDOMElement(); none.unmount();
  const empty = render(<Timeline series={[{ date: 'd', count: 0 }]} />); expect(screen.getByTestId('timeline-30d-empty')).toBeInTheDocument(); empty.unmount();
  render(<Timeline series={[{ date: 'a', count: 2 }, { date: 'b', count: 0 }]} accent="blue" />);
  expect(screen.getByTestId('timeline-30d')).toBeInTheDocument();
});

test('pending activation renders optional name and opens profile and billing', () => {
  const profile = jest.fn(); const billing = jest.fn();
  const { rerender } = render(<PendingActivationPage partnerName="School" onOpenProfile={profile} onOpenBilling={billing} />);
  expect(screen.getByText('Willkommen, School')).toBeInTheDocument();
  fireEvent.click(screen.getByTestId('pending-open-profile')); fireEvent.click(screen.getByTestId('pending-open-billing'));
  expect(profile).toHaveBeenCalled(); expect(billing).toHaveBeenCalled();
  rerender(<PendingActivationPage onOpenProfile={profile} onOpenBilling={billing} />);
  expect(screen.getByText('Willkommen')).toBeInTheDocument();
});

test('user table scores, filters, sorts every type and exposes all row actions and statuses', () => {
  const view = jest.fn(); const reopen = jest.fn();
  render(<UserTable data={users} onViewUser={view} onReopenUser={reopen} showStatus showCompleted tableId="rich" t={t} partnerTags={['Cardiology', 'Berlin']} />);
  expect(screen.getByTestId('match-u1')).toHaveTextContent('15');
  expect(screen.getByText('Allgemeine Zuordnung')).toBeInTheDocument();
  expect(screen.getByTestId('completed-at-u1')).not.toHaveTextContent('-');
  fireEvent.click(screen.getByTestId('view-user-u1')); fireEvent.click(screen.getByTestId('reopen-user-u1'));
  expect(view).toHaveBeenCalledWith(expect.objectContaining(users[0])); expect(reopen).toHaveBeenCalledWith(expect.objectContaining(users[0]));
  for (const key of ['match_score', 'user_name', 'service_step_title', 'user_email', 'field_of_study', 'completion_pct', 'status', 'estimated_completion', 'partner_work_completed_at']) {
    fireEvent.click(screen.getByTestId(`sort-rich-${key}`));
    fireEvent.click(screen.getByTestId(`sort-rich-${key}`));
  }
  fireEvent.click(screen.getByTestId('select-all'));
  expect(screen.queryByTestId('view-user-2')).not.toBeInTheDocument();
  fireEvent.change(screen.getByTestId('filter-rich-forecast-from'), { target: { value: '2026-08-01' } });
  fireEvent.change(screen.getByTestId('filter-rich-forecast-to'), { target: { value: '2026-08-31' } });
  fireEvent.click(screen.getByTestId('filter-rich-reset'));
  expect(screen.getByTestId('pagination-partner-rich')).toBeInTheDocument();
});

test('user table supports defaults, disabled actions and empty filtered results', () => {
  const view = jest.fn();
  const { rerender } = render(<UserTable data={users} onViewUser={view} t={t} actionsDisabled />);
  fireEvent.click(screen.getByTestId('view-user-u1'));
  expect(view).not.toHaveBeenCalled();
  expect(screen.queryByTestId('match-u1')).not.toBeInTheDocument();
  rerender(<UserTable data={[]} onViewUser={view} t={t} />);
  expect(screen.getByText('partner_no_entries')).toBeInTheDocument();
  expect(screen.getByTestId('table-table')).toBeInTheDocument();
});

test('user table covers empty comparison dates, fallback row IDs and translated match labels', () => {
  const reopen = jest.fn();
  render(<UserTable data={[
    { id: 'fallback', user_name: 'Empty date', estimated_completion: '', partner_work_completed: true },
    { id: 'dated', user_name: 'Dated', estimated_completion: '2026-01-01', partner_work_completed: true },
  ]} onViewUser={jest.fn()} onReopenUser={reopen} showCompleted tableId="fallbacks" t={() => ''} partnerTags={['Tag']} />);
  fireEvent.click(screen.getByTestId('sort-fallbacks-estimated_completion'));
  fireEvent.click(screen.getByTestId('reopen-user-fallback'));
  expect(reopen).toHaveBeenCalled();
  expect(screen.getByText('Match')).toBeInTheDocument();
});
