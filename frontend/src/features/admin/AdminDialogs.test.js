import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { AdminDialogs } from './AdminDialogs';

jest.mock('./UserDetailDialog', () => ({ UserDetailDialog: p => <button onClick={() => p.setShowUserDialog(false)}>user-detail</button> }));
jest.mock('./AdminDashboardComponents/StepDialog', () => ({ StepDialog: p => <button onClick={p.onClose}>step-dialog</button> }));
jest.mock('./AdminDashboardComponents/PartnerDialog', () => ({ PartnerDialog: p => <button onClick={p.onClose}>partner-dialog-{p.defaultUserFeeCents}</button> }));
jest.mock('./AdminDashboardComponents/LinkUserDialog', () => ({ LinkUserDialog: p => <button onClick={p.onClose}>link-{p.users.length}</button> }));
jest.mock('./AdminDashboardComponents/CreateUserDialog', () => ({ CreateUserDialog: p => <button onClick={p.onClose}>create-{p.defaultSurveyId}</button> }));
jest.mock('../../components/ConfirmDialog', () => ({ ConfirmDialog: p => <><button onClick={p.onOpenChange}>close-confirm</button><button onClick={p.onConfirm}>confirm</button></> }));

test('dialog composition narrows users, computes defaults and closes every dialog', () => {
  const f = () => jest.fn(), setShowUserDialog = f(), setShowStepDialog = f(), setEditingStep = f(), setShowPartnerDialog = f(), setEditingPartner = f(), setShowLinkDialog = f(), setShowCreateUserDialog = f(), setConfirmDialog = f(), onConfirm = f();
  const base = { t: x => x, users: [{ id: 'u', role: 'user' }, { id: 'a', role: 'admin' }], steps: [], surveys: [{ id: 'default', is_default: true }], activeSurveyId: '', partners: [], selectedUser: null, showUserDialog: true, setShowUserDialog, showCreateUserDialog: true, setShowCreateUserDialog, permissionGroups: [], userPermissionDraft: {}, setUserPermissionDraft: f(), savingUserPermissions: false, editingStep: {}, setEditingStep, showStepDialog: true, setShowStepDialog, editingPartner: {}, setEditingPartner, showPartnerDialog: true, setShowPartnerDialog, showLinkDialog: {}, setShowLinkDialog, confirmDialog: { message: 'sure', onConfirm }, setConfirmDialog, siteSettings: {}, can: () => true, permissionOptions: [], selectedUserGroupOptions: [], handleSaveUserPermissions: f(), handleUpdateUserProgress: f(), handleSaveStep: f(), handleSurveyChange: f(), handleSavePartner: f(), handleLinkUser: f(), handleCreateUser: f() };
  const { rerender } = render(<AdminDialogs {...base} />);
  ['user-detail', 'step-dialog', 'partner-dialog-0', 'link-1', 'create-default', 'close-confirm', 'confirm'].forEach(x => fireEvent.click(screen.getByText(x)));
  expect(setEditingStep).toHaveBeenCalledWith(null); expect(setEditingPartner).toHaveBeenCalledWith(null); expect(onConfirm).toHaveBeenCalled();
  rerender(<AdminDialogs {...base} activeSurveyId="active" siteSettings={{ stripe_partner_user_fee_cents: 99 }} confirmDialog={null} surveys={[]} />);
  expect(screen.getByText('create-active')).toBeInTheDocument(); fireEvent.click(screen.getByText('confirm'));
  rerender(<AdminDialogs {...base} activeSurveyId="" surveys={[{ id: 'first' }]} />); expect(screen.getByText('create-first')).toBeInTheDocument(); rerender(<AdminDialogs {...base} activeSurveyId="" surveys={[]} />); expect(screen.getByText('create-')).toBeInTheDocument();
});
