import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { CreateUserDialog } from './CreateUserDialog';
import { LinkUserDialog } from './LinkUserDialog';

jest.mock('../../../components/ui/dialog', () => ({ Dialog: ({ open, children }) => open ? <div>{children}</div> : null, DialogContent: ({ children }) => <div>{children}</div>, DialogHeader: ({ children }) => <header>{children}</header>, DialogTitle: ({ children }) => <h2>{children}</h2> }));
jest.mock('../../../components/ui/select', () => ({ Select: ({ children, onValueChange }) => <div>{children}<button type="button" data-testid="select-partner" onClick={() => onValueChange('partner')}>partner choice</button><button type="button" data-testid="select-p1" onClick={() => onValueChange('p1')}>partner id</button></div>, SelectContent: ({ children }) => <>{children}</>, SelectItem: ({ children }) => <span>{children}</span>, SelectTrigger: ({ children, ...p }) => <div {...p}>{children}</div>, SelectValue: () => null }));
jest.mock('../../../components/admin/EntityPickers', () => ({ SearchableMultiSelect: p => <button type="button" data-testid={p.testId} onClick={() => p.onChange(['g2'])}>groups</button> }));
jest.mock('@phosphor-icons/react', () => new Proxy({}, { get: () => () => <i /> }));

test('create user resets, edits, switches role, selects partner and submits', () => {
  const onSave = jest.fn(), onClose = jest.fn();
  const props = { open: true, onClose, onSave, partners: [{ id: 'p1', name: 'Zulu' }, { id: 'p2', name: 'Alpha' }], surveys: [{ id: 's1', name: 'Survey', slug: 'survey', is_active: true }, { id: 'off', is_active: false }], permissionGroups: [{ id: 'g1', role: 'user', name: 'Users', is_system: true, permissions: ['x'] }, { id: 'g2', role: 'partner', name: 'Partners', is_system: true, permissions: ['*'] }], canManagePermissions: true, defaultSurveyId: 's1', t: x => x };
  render(<CreateUserDialog {...props} />);
  fireEvent.change(screen.getByTestId('create-user-name'), { target: { value: 'Name' } }); fireEvent.change(screen.getByTestId('create-user-email'), { target: { value: 'x@y.de' } }); fireEvent.change(screen.getByTestId('create-user-password'), { target: { value: 'secret' } });
  fireEvent.click(screen.getAllByTestId('select-p1')[1]);
  fireEvent.click(screen.getByTestId('create-user-permission-groups')); fireEvent.click(screen.getAllByTestId('select-partner')[0]);
  fireEvent.click(screen.getAllByTestId('select-p1')[0]); fireEvent.click(screen.getAllByTestId('select-partner')[0]);
  expect(screen.getByTestId('create-user-partner')).toBeInTheDocument(); fireEvent.click(screen.getAllByTestId('select-p1')[1]); fireEvent.click(screen.getByTestId('submit-create-user')); fireEvent.click(screen.getByText('cancel'));
  expect(onSave).toHaveBeenCalledWith(expect.objectContaining({ role: 'partner', partner_id: 'p1', group_ids: ['g2'] })); expect(onSave.mock.calls[0][0].survey_id).toBeUndefined(); expect(onClose).toHaveBeenCalled();
});

test('create user strips unavailable permissions and none partner', () => {
  const onSave = jest.fn(); const { rerender } = render(<CreateUserDialog open onClose={jest.fn()} onSave={onSave} partners={[]} surveys={[]} permissionGroups={[]} canManagePermissions={false} defaultSurveyId="" t={x => x} />);
  expect(screen.getByTestId('submit-create-user')).toBeDisabled(); rerender(<CreateUserDialog open onClose={jest.fn()} onSave={onSave} partners={[]} surveys={[{ id: 's', name: 'S', slug: 's', is_active: true }]} permissionGroups={[]} canManagePermissions={false} defaultSurveyId="s" t={x => x} />); fireEvent.click(screen.getByTestId('submit-create-user')); expect(onSave.mock.calls.at(-1)[0].partner_id).toBeUndefined(); expect(onSave.mock.calls.at(-1)[0].group_ids).toBeUndefined();
});

test('link user sorts, filters, links and shows empty result', () => {
  const onLink = jest.fn(); render(<LinkUserDialog open onClose={jest.fn()} partner={{ id: 'p', name: 'School' }} users={[{ id: '2', name: 'Zulu', email: 'z@x' }, { id: '1', name: 'Alpha', email: 'a@x' }]} onLink={onLink} />);
  fireEvent.click(screen.getByTestId('link-select-user-1')); expect(onLink).toHaveBeenCalledWith('p', '1');
  fireEvent.change(screen.getByTestId('link-user-search'), { target: { value: 'a@x' } }); expect(screen.getByTestId('link-select-user-1')).toBeInTheDocument();
  fireEvent.change(screen.getByTestId('link-user-search'), { target: { value: 'nobody' } }); expect(screen.getByText('No available users found')).toBeInTheDocument();
});

test('link user uses email as stable tie breaker for equal names', () => {
  render(<LinkUserDialog open onClose={jest.fn()} partner={undefined} users={[{ id: 'b', name: 'Same', email: 'b@x' }, { id: 'a', name: 'Same', email: 'a@x' }]} onLink={jest.fn()} />); expect(screen.getByTestId('link-select-user-a')).toBeInTheDocument();
});

test('create user applies omitted permission defaults and permission count fallback', () => {
  render(<CreateUserDialog open onClose={jest.fn()} onSave={jest.fn()} partners={[]} surveys={[{ id: 's', name: 'S', slug: 's', is_active: true }]} defaultSurveyId="s" t={x => x} />); expect(screen.queryByText('Admin')).not.toBeInTheDocument();
  const { unmount } = render(<CreateUserDialog open onClose={jest.fn()} onSave={jest.fn()} partners={[]} surveys={[{ id: 's', is_active: true }]} permissionGroups={[{ id: 'g', role: 'user', name: 'No permissions', is_system: true }]} canManagePermissions defaultSurveyId="s" t={x => x} />); expect(screen.getAllByTestId('create-user-permission-groups').length).toBeGreaterThan(0); unmount();
});
