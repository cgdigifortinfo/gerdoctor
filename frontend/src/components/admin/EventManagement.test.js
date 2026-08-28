import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import EventManagement from './EventManagement';
import { adminAPI, formatApiError } from '../../lib/api';
import { toast } from 'sonner';

jest.mock('../../lib/api', () => ({
  adminAPI: {
    listEventConfigs: jest.fn(), listEvents: jest.fn(), listEmailTemplates: jest.fn(),
    updateEventConfig: jest.fn(), retryEvent: jest.fn(),
  },
  formatApiError: jest.fn(() => 'formatted error'),
}));
jest.mock('sonner', () => ({ toast: { error: jest.fn(), success: jest.fn() } }));
jest.mock('@phosphor-icons/react', () => new Proxy({}, { get: () => () => <i /> }));
jest.mock('react-router-dom', () => ({ Link: ({ children, to }) => <a href={to}>{children}</a> }), { virtual: true });
jest.mock('../ui/button', () => ({ Button: ({ children, asChild, ...props }) => asChild ? <>{children}</> : <button {...props}>{children}</button> }));
jest.mock('../ui/switch', () => ({ Switch: ({ checked, onCheckedChange, ...props }) => <button aria-pressed={checked} onClick={() => onCheckedChange(!checked)} {...props}>switch</button> }));
jest.mock('../ui/select', () => ({
  Select: ({ children, value, onValueChange }) => {
    const flatten = (node) => Array.isArray(node) ? node.map(flatten).join(' ') : node && typeof node === 'object' ? flatten(node.props?.children) : String(node || '');
    const content = flatten(children);
    const next = content.includes('Alle Eventtypen') ? (value === 'all' ? 'doctor.created' : 'all') : content.includes('Alle Status') ? (value === 'all' ? 'failed' : 'all') : 'changed-template';
    return <div>{children}<button data-testid={`select-${value}`} onClick={() => onValueChange(next)}>change</button></div>;
  },
  SelectContent: ({ children }) => <div>{children}</div>, SelectItem: ({ children }) => <span>{children}</span>,
  SelectTrigger: ({ children, ...props }) => <div {...props}>{children}</div>, SelectValue: () => <span>value</span>,
}));
jest.mock('../PaginationControls', () => ({
  usePagination: (items) => ({ paginatedItems: items }),
  PaginationControls: ({ id }) => <div data-testid={`pagination-${id}`} />,
}));

const configs = [
  {
    event_type: 'doctor.created', label: 'Arzt angelegt', description: 'Beschreibung', enabled: true,
    handlers: [
      { id: 'mail', type: 'email', label: 'Mail', enabled: true, template_key: 'welcome' },
      { id: 'notify', type: 'notification', label: 'Notify', enabled: false, template_key: '', channels: ['browser'] },
    ],
  },
  { event_type: 'empty.event', label: 'Leeres Event', description: '', enabled: false, handlers: [] },
  { event_type: 'missing.handlers', label: 'Fallback Event' },
  { event_type: 'no.channels', label: 'No channels', handlers: [{ id: 'channel-less', type: 'notification', label: 'No channels', enabled: true }] },
];
const events = [
  { id: 1, event_id: 'e1', created_at: '2026-01-01T10:00:00Z', event_type: 'doctor.created', status: 'processed', payload: { user_name: 'Ada', step_title: 'Start' }, handler_results: [{ type: 'email', status: 'sent' }] },
  { id: 2, event_id: 'e2', created_at: '2026-01-02T10:00:00Z', event_type: 'doctor.created', status: 'failed', payload: { filename: 'demo.pdf' }, handler_results: [] },
  { id: 3, event_id: 'e3', created_at: '2026-01-03T10:00:00Z', event_type: 'empty.event', status: 'skipped' },
  { id: 4, event_id: 'e4', created_at: '2026-01-04T10:00:00Z', event_type: 'empty.event', status: 'unknown', payload: {} },
];

beforeEach(() => {
  jest.clearAllMocks();
  formatApiError.mockReturnValue('formatted error');
  adminAPI.listEventConfigs.mockResolvedValue({ data: configs });
  adminAPI.listEvents.mockResolvedValue({ data: { events } });
  adminAPI.listEmailTemplates.mockResolvedValue({ data: { templates: [{ key: 'layout', category: 'layout' }, { key: 'welcome', category: 'transactional' }] } });
  adminAPI.updateEventConfig.mockImplementation(async (type, body) => ({ data: { ...configs.find(item => item.event_type === type), ...body } }));
  adminAPI.retryEvent.mockResolvedValue({});
});

test('loads, renders, filters and edits every event configuration shape', async () => {
  render(<EventManagement />);
  expect(screen.getByText(/Events werden geladen/)).toBeInTheDocument();
  await screen.findByTestId('event-management');
  expect(screen.getByText('Ada')).toBeInTheDocument();
  expect(screen.getByText('demo.pdf')).toBeInTheDocument();
  expect(screen.getAllByText('—').length).toBeGreaterThan(0);
  expect(screen.getByText('email: sent')).toBeInTheDocument();
  expect(screen.getAllByText('Keine').length).toBeGreaterThan(0);
  expect(screen.getByTestId('pagination-admin-domain-events')).toBeInTheDocument();
  expect(screen.getByRole('link', { name: /Bearbeiten/ })).toHaveAttribute('href', expect.stringContaining('channel=email'));

  fireEvent.click(screen.getByTestId('event-enabled-doctor.created'));
  fireEvent.click(screen.getByTestId('event-handler-enabled-doctor.created-email'));
  fireEvent.click(screen.getByTestId('event-handler-enabled-doctor.created-notification'));
  fireEvent.click(screen.getByTestId('event-channel-doctor.created-browser'));
  fireEvent.click(screen.getByTestId('event-channel-doctor.created-app'));
  fireEvent.click(screen.getByTestId('event-channel-no.channels-browser'));
  fireEvent.click(screen.getByTestId('select-welcome'));
  fireEvent.click(screen.getByTestId('event-add-email-handler-empty.event'));
  fireEvent.click(screen.getByTestId('event-add-notification-handler-empty.event'));
  fireEvent.click(screen.getByTestId('event-add-email-handler-missing.handlers'));
  expect(screen.getByTestId(/^event-handler-empty\.event-notify-user-notification-/)).toBeInTheDocument();

  const allSelectors = screen.getAllByTestId('select-all');
  fireEvent.click(allSelectors[1]);
  expect(screen.getByText('demo.pdf')).toBeInTheDocument();
  fireEvent.click(screen.getByTestId('select-failed'));
  fireEvent.click(screen.getAllByTestId('select-all')[0]);
  expect(screen.queryByTestId('event-row-empty.event')).not.toBeInTheDocument();
  fireEvent.click(screen.getByTestId('select-doctor.created'));
  expect(screen.getAllByTestId('event-row-empty.event')).toHaveLength(2);
});

test('saves, retries and refreshes successfully', async () => {
  render(<EventManagement />);
  await screen.findByTestId('event-management');
  fireEvent.click(screen.getByTestId('event-save-doctor.created'));
  fireEvent.click(screen.getByTestId('event-save-missing.handlers'));
  await waitFor(() => expect(adminAPI.updateEventConfig).toHaveBeenCalledWith('doctor.created', expect.objectContaining({ enabled: true })));
  expect(toast.success).toHaveBeenCalledWith('Event „Arzt angelegt“ gespeichert');
  fireEvent.click(screen.getByTestId('event-retry-e2'));
  await waitFor(() => expect(adminAPI.retryEvent).toHaveBeenCalled());
  expect(toast.success).toHaveBeenCalledWith('Event erneut verarbeitet');
  fireEvent.click(screen.getByTestId('events-refresh-btn'));
  await waitFor(() => expect(adminAPI.listEvents).toHaveBeenCalledTimes(3));
});

test('reports load, save and retry failures and supports empty response fallbacks', async () => {
  adminAPI.listEventConfigs.mockResolvedValueOnce({});
  adminAPI.listEvents.mockResolvedValueOnce({ data: {} });
  adminAPI.listEmailTemplates.mockResolvedValueOnce({ data: {} });
  const first = render(<EventManagement />);
  await screen.findByTestId('event-management');
  expect(screen.getByText('Noch keine Ereignisse vorhanden.')).toBeInTheDocument();
  first.unmount();

  adminAPI.listEventConfigs.mockRejectedValueOnce(new Error('load'));
  const second = render(<EventManagement />);
  await screen.findByTestId('event-management');
  expect(formatApiError).toHaveBeenCalled();
  expect(toast.error).toHaveBeenCalledWith('formatted error');
  second.unmount();

  adminAPI.updateEventConfig.mockRejectedValueOnce(new Error('save'));
  adminAPI.retryEvent.mockRejectedValueOnce(new Error('retry'));
  render(<EventManagement />);
  await screen.findByTestId('event-management');
  fireEvent.click(screen.getByTestId('event-save-doctor.created'));
  fireEvent.click(screen.getByTestId('event-retry-e2'));
  await waitFor(() => expect(toast.error).toHaveBeenCalledTimes(3));
});

test('new email handlers use an empty template key when no template exists', async () => {
  adminAPI.listEventConfigs.mockResolvedValueOnce({ data: [{ event_type: 'bare', label: 'Bare' }] });
  adminAPI.listEvents.mockResolvedValueOnce({ data: { events: [] } });
  adminAPI.listEmailTemplates.mockResolvedValueOnce({ data: { templates: [] } });
  render(<EventManagement />);
  await screen.findByTestId('event-management');
  fireEvent.click(screen.getByTestId('event-add-email-handler-bare'));
  expect(screen.getByTestId(/^event-handler-bare-notify-user-email-/)).toBeInTheDocument();
});
