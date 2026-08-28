import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import PermissionGroupsManager, { PermissionMatrix } from './PermissionGroupsManager';
import { adminAPI, formatApiError } from '../../lib/api';
import { toast } from 'sonner';

jest.mock('../../lib/api', () => ({
  adminAPI: { createPermissionGroup: jest.fn(), updatePermissionGroup: jest.fn(), deletePermissionGroup: jest.fn() },
  formatApiError: jest.fn(() => 'formatted error'),
}));
jest.mock('sonner', () => ({ toast: { success: jest.fn(), error: jest.fn() } }));
jest.mock('../ui/select', () => ({
  Select: ({ children, onValueChange, disabled }) => <div>{children}<button type="button" disabled={disabled} onClick={() => onValueChange('partner')}>choose partner</button></div>,
  SelectContent: ({ children }) => <div>{children}</div>, SelectItem: ({ children }) => <span>{children}</span>,
  SelectTrigger: ({ children, ...props }) => <div {...props}>{children}</div>, SelectValue: () => <span>role</span>,
}));
jest.mock('../ui/dialog', () => ({
  Dialog: ({ open, children }) => open ? <div>{children}</div> : null,
  DialogContent: ({ children, ...props }) => <div {...props}>{children}</div>,
  DialogHeader: ({ children, ...props }) => <div {...props}>{children}</div>,
  DialogTitle: ({ children }) => <h2>{children}</h2>,
}));

const catalog = { all_permissions: ['read', 'write'], categories: [{ category: 'General', permissions: [{ key: 'read', label: 'Read', description: 'Can read' }, { key: 'write', label: 'Write', description: 'Can write' }] }] };
const groups = [
  { id: 'system', name: 'System', role: 'admin', permissions: ['*'], member_count: 2, is_system: true },
  { id: 'custom', name: 'Custom', role: 'user', permissions: ['read'], member_count: 0, description: '' },
];
const click = (element) => { try { fireEvent.click(element); } catch (error) { throw error.errors?.[0] || error; } };

beforeAll(() => { window.ResizeObserver = class { observe() {} unobserve() {} disconnect() {} }; });
beforeEach(() => { jest.clearAllMocks(); formatApiError.mockReturnValue('formatted error'); adminAPI.createPermissionGroup.mockResolvedValue({}); adminAPI.updatePermissionGroup.mockResolvedValue({}); adminAPI.deletePermissionGroup.mockResolvedValue({}); });

test('permission matrix toggles individual, partial, full, and empty categories', () => {
  const change = jest.fn();
  const { rerender } = render(<PermissionMatrix catalog={null} onChange={change} />);
  expect(screen.getByTestId('permission-matrix')).toBeEmptyDOMElement();
  rerender(<PermissionMatrix catalog={catalog} selected={['read']} onChange={change} />);
  fireEvent.click(screen.getByTestId('permission-matrix-read'));
  expect(change).toHaveBeenCalledWith([]);
  fireEvent.click(screen.getByTestId('permission-matrix-write'));
  expect(change).toHaveBeenCalledWith(['read', 'write']);
  fireEvent.click(screen.getByText('General'));
  expect(change).toHaveBeenCalledWith(['read', 'write']);
  rerender(<PermissionMatrix catalog={catalog} selected={['read', 'write']} onChange={change} disabled testId="disabled-matrix" />);
  expect(screen.getByText('General').closest('button')).toBeDisabled();
  rerender(<PermissionMatrix catalog={catalog} selected={['read', 'write']} onChange={change} />);
  fireEvent.click(screen.getByText('General'));
  expect(change).toHaveBeenLastCalledWith([]);
});

test('manager renders permissions and creates a group successfully', async () => {
  const refresh = jest.fn();
  render(<PermissionGroupsManager groups={groups} catalog={catalog} onRefresh={refresh} canCreate canUpdate canDelete />);
  expect(screen.getByText('2 Rechte')).toBeInTheDocument();
  expect(screen.getAllByText('Keine Beschreibung')).toHaveLength(2);
  expect(screen.queryByLabelText('System löschen')).not.toBeInTheDocument();
  click(screen.getByTestId('create-permission-group'));
  fireEvent.change(screen.getByTestId('permission-group-name'), { target: { value: 'New' } });
  fireEvent.change(screen.getAllByRole('textbox')[1], { target: { value: 'Description' } });
  fireEvent.click(screen.getByText('choose partner'));
  fireEvent.click(screen.getByTestId('group-permission-matrix-read'));
  fireEvent.click(screen.getByTestId('save-permission-group'));
  await waitFor(() => expect(adminAPI.createPermissionGroup).toHaveBeenCalledWith(expect.objectContaining({ name: 'New', role: 'partner', permissions: ['read'] })));
  expect(toast.success).toHaveBeenCalledWith('Nutzergruppe erstellt');
  expect(refresh).toHaveBeenCalled();
});

test('manager edits wildcard groups and reports save errors', async () => {
  adminAPI.updatePermissionGroup.mockRejectedValue(new Error('failed'));
  render(<PermissionGroupsManager groups={groups} catalog={catalog} onRefresh={jest.fn()} canUpdate />);
  click(screen.getByLabelText('System bearbeiten'));
  expect(screen.getByTestId('permission-group-name')).toHaveValue('System');
  expect(screen.getByText(/Portalrolle kann/)).toBeInTheDocument();
  expect(screen.getByText('choose partner')).toBeDisabled();
  fireEvent.click(screen.getByTestId('save-permission-group'));
  await waitFor(() => expect(toast.error).toHaveBeenCalledWith('formatted error'));
  expect(formatApiError).toHaveBeenCalled();
  adminAPI.updatePermissionGroup.mockResolvedValue({});
  fireEvent.click(screen.getByTestId('save-permission-group'));
  await waitFor(() => expect(toast.success).toHaveBeenCalledWith('Nutzergruppe aktualisiert'));
});

test('manager handles delete cancellation, success, and failure', async () => {
  const refresh = jest.fn(); const confirm = jest.spyOn(window, 'confirm');
  confirm.mockReturnValueOnce(false).mockReturnValueOnce(true).mockReturnValueOnce(true);
  const first = render(<PermissionGroupsManager groups={groups} catalog={catalog} onRefresh={refresh} canDelete />);
  fireEvent.click(screen.getByLabelText('Custom löschen'));
  expect(adminAPI.deletePermissionGroup).not.toHaveBeenCalled();
  fireEvent.click(screen.getByLabelText('Custom löschen'));
  await waitFor(() => expect(adminAPI.deletePermissionGroup).toHaveBeenCalledWith('custom'));
  await waitFor(() => expect(refresh).toHaveBeenCalled());
  first.unmount();
  adminAPI.deletePermissionGroup.mockRejectedValueOnce(new Error('failed'));
  render(<PermissionGroupsManager groups={groups} catalog={catalog} onRefresh={refresh} canDelete />);
  fireEvent.click(screen.getByLabelText('Custom löschen'));
  await waitFor(() => expect(toast.error).toHaveBeenCalledWith('formatted error'));
  confirm.mockRestore();
});

test('manager hides unauthorized actions', () => {
  render(<PermissionGroupsManager groups={[]} catalog={catalog} onRefresh={jest.fn()} />);
  expect(screen.queryByTestId('create-permission-group')).not.toBeInTheDocument();
});

test('manager tolerates sparse groups and a missing permission catalog', () => {
  const sparse = [
    { id: 'wild', name: '', role: 'user', permissions: ['*'], member_count: 0 },
    { id: 'none', name: 'None', role: 'user', member_count: 0 },
  ];
  render(<PermissionGroupsManager groups={sparse} catalog={null} onRefresh={jest.fn()} canUpdate />);
  expect(screen.getAllByText('0 Rechte')).toHaveLength(2);
  click(screen.getAllByLabelText(/bearbeiten/)[0]);
  expect(screen.getByTestId('group-permission-matrix')).toBeEmptyDOMElement();
});
