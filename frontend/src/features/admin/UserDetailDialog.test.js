import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { UserDetailDialog } from './UserDetailDialog';

jest.mock('../../lib/api', () => ({ filesAPI: { getUrl: id => `/files/${id}` } }));
jest.mock('../../components/ui/dialog', () => ({ Dialog: ({ open, children }) => open ? <div>{children}</div> : null, DialogContent: ({ children }) => <div>{children}</div>, DialogHeader: ({ children }) => <header>{children}</header>, DialogTitle: ({ children }) => <h2>{children}</h2> }));
jest.mock('../../components/ui/select', () => ({ Select: ({ children, onValueChange }) => <div>{children}<button data-testid="progress-change" onClick={() => onValueChange('completed')}>change</button></div>, SelectContent: ({ children }) => <>{children}</>, SelectItem: ({ children }) => <span>{children}</span>, SelectTrigger: ({ children, ...props }) => <div {...props}>{children}</div>, SelectValue: () => null }));
jest.mock('../../components/admin/EntityPickers', () => ({ SearchableMultiSelect: ({ onChange, testId }) => <button data-testid={testId} onClick={() => onChange(['x'])}>pick</button> }));
jest.mock('@phosphor-icons/react', () => new Proxy({}, { get: () => () => <i /> }));

const steps = [{ id: 's1', order: 1, title: 'Upload', fields: [{ name: 'docs', label: 'Dokumente', field_type: 'multiupload' }, { name: 'file', label: 'Datei', field_type: 'file' }, { name: 'text', label: 'Text', field_type: 'text' }] }];
const selectedUser = {
  id: 'u1', name: 'User', email: 'u@test.de', role: 'user', created_at: '2026-01-01', completion_pct: 60, partner_registration_status: 'pending',
  profile: { profile_image: 'img', document_id: '12345678-1234-1234-1234-123456789012', age: 30 }, effective_permissions: ['x'], permission_groups: [{ id: 'g', name: 'Group' }],
  progress: [{ step_id: 's1', status: 'completed', configuration_changed: true, step_version: 1, current_step_version: 2, step_deleted: true, data: { docs: [{ document_type: 'Pass', file_id: 'f1', filename: 'pass.pdf' }, {}], file: 'f2', text: ['a','b'], removed: { x: 1 }, removed_multi: [{ file_id: 'f3' }], removed_file: 'f4', empty: '' }, step_snapshot: { fields: [{ name: 'removed', label: 'Alt', field_type: 'text' }, { name: 'removed_multi', label: 'Old multi', field_type: 'multiupload' }, { name: 'removed_file', label: 'Old file', field_type: 'file' }] } }, { step_id: 'unknown', status: 'in_progress' }, { step_id: 'pending', status: 'pending', data: { skipped: true } }],
  revisions: [{ step_id: 's1', revision: 1, step_title: 'Upload', step_version: 1, configuration_changed: true, data: { x: 1 }, created_at: '2026-01-01', change_type: 'edit' }, { step_id: 's1', revision: 2, step_title: 'Empty', step_version: 1, configuration_changed: false, created_at: '2026-01-02', change_type: 'edit' }],
  submissions: [{ id: 'sub1', partner_id: 'p1', created_at: '2026-01-01' }], history: [{ action: 'completed', step_title: 'Done', timestamp: '2026-01-01' }, { action: 'in_progress', step_title: 'WIP', timestamp: '2026-01-02' }, { action: 'other', step_title: 'Other', timestamp: '2026-01-03' }],
};

const base = { showUserDialog: true, setShowUserDialog: jest.fn(), selectedUser: { ...selectedUser, progress: selectedUser.progress.map((p, i) => i ? p : { ...p, data: { ...p.data, skipped: true } }) }, selectedUserGroupOptions: [], userPermissionDraft: { group_ids: [], allow: ['x', 'y'], deny: ['x', 'z'] }, setUserPermissionDraft: jest.fn(), savingUserPermissions: false, handleSaveUserPermissions: jest.fn(), can: () => true, permissionOptions: [], steps, handleUpdateUserProgress: jest.fn(), partners: [{ id: 'p1', name: 'Partner' }] };

test('user detail renders rich profile, permissions, progress, history and submissions', () => {
  render(<UserDetailDialog {...base} />);
  expect(screen.getByText('User Details')).toBeInTheDocument(); expect(screen.getByText('Partner')).toBeInTheDocument(); expect(screen.getByText('pass.pdf')).toBeInTheDocument(); expect(screen.getAllByText('Feld inzwischen gelöscht').length).toBeGreaterThan(0);
  fireEvent.error(screen.getByTestId('user-profile-image'));
  fireEvent.click(screen.getByTestId('user-permission-groups')); fireEvent.click(screen.getByTestId('user-permission-allow')); fireEvent.click(screen.getByTestId('user-permission-deny')); fireEvent.click(screen.getByTestId('save-user-permissions'));
  screen.getAllByTestId('progress-change').forEach(button => fireEvent.click(button));
  expect(base.handleUpdateUserProgress).toHaveBeenCalled(); expect(base.handleSaveUserPermissions).toHaveBeenCalled();
});

test('user detail covers primary admin, read-only, missing profile and empty collections', () => {
  const minimal = { id: 'u2', name: 'Minimal', email: 'm@test.de', role: 'admin', profile: {}, progress: [], completion_pct: 0, is_primary_admin: true, effective_permissions: ['*'] };
  const { rerender } = render(<UserDetailDialog {...base} selectedUser={minimal} />);
  expect(screen.getByText(/primäre Administratorkonto/)).toBeInTheDocument(); expect(screen.getByText('No progress data yet')).toBeInTheDocument();
  rerender(<UserDetailDialog {...base} selectedUser={{ ...minimal, is_primary_admin: false, permission_groups: [{ id: 'g', name: 'Read only group' }], submissions: [{ id: 'missing', partner_id: 'missing', created_at: '2026-01-01' }] }} can={() => false} savingUserPermissions />);
  expect(screen.getByText(/ansehen, aber nicht überschreiben/)).toBeInTheDocument();
  expect(screen.getByText('Read only group')).toBeInTheDocument(); expect(screen.getByText('Unknown Partner')).toBeInTheDocument();
  rerender(<UserDetailDialog {...base} selectedUser={{ ...minimal, effective_permissions: undefined, is_primary_admin: false }} can={() => true} savingUserPermissions />); expect(screen.getByText('Speichert …')).toBeDisabled();
  rerender(<UserDetailDialog {...base} selectedUser={{ ...minimal, effective_permissions: [], permission_groups: undefined, is_primary_admin: false }} can={() => false} />); expect(screen.getByText(/ansehen, aber nicht überschreiben/)).toBeInTheDocument();
  rerender(<UserDetailDialog {...base} selectedUser={null} />); expect(screen.queryByText('Minimal')).not.toBeInTheDocument();
  rerender(<UserDetailDialog {...base} showUserDialog={false} />); expect(screen.queryByText('User Details')).not.toBeInTheDocument();
});
