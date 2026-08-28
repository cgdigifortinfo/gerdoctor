import { act, renderHook } from '@testing-library/react';
import { useAdminBilling } from './useAdminBilling';
import { useAdminCms } from './useAdminCms';
import { useAdminPartners } from './useAdminPartners';
import { useAdminSteps } from './useAdminSteps';
import { useAdminUsers } from './useAdminUsers';

beforeEach(() => localStorage.clear());

test('user state derives search, role, permissions, groups and exposes setters', () => {
  const { result } = renderHook(() => useAdminUsers());
  expect(result.current).toMatchObject({ showUserDialog: false, showCreateUserDialog: false, savingUserPermissions: false });
  act(() => {
    result.current.setUsers([{ id: '1', name: 'Alice', email: 'alice@test.de', role: 'user' }, { id: '2', name: 'Bob', email: 'other@test.de', role: 'partner' }]);
    result.current.setPermissionCatalog({ categories: [{ category: 'Users', permissions: [{ key: 'users.view', label: 'View', description: 'read' }] }] });
    result.current.setPermissionGroups([{ id: 'g1', name: 'All', role: 'user', member_count: 2, permissions: ['*'] }, { id: 'g2', name: 'Some', role: 'partner', member_count: 0, permissions: ['x'], description: 'limited' }]);
  });
  expect(result.current.filteredUsers).toHaveLength(2);
  expect(result.current.permissionOptions[0]).toMatchObject({ value: 'users.view', description: 'Users' });
  expect(result.current.selectedUserGroupOptions).toHaveLength(2);
  expect(result.current.selectedUserGroupOptions[0].description).toContain('Alle Rechte');
  act(() => {
    result.current.setPermissionCatalog({});
    result.current.setPermissionGroups([{ id: 'g3', name: 'None', role: 'user', member_count: 0 }]);
  });
  expect(result.current.permissionOptions).toEqual([]);
  expect(result.current.selectedUserGroupOptions[0]).toMatchObject({ description: '0 Mitglieder · 0 Rechte', keywords: 'user ' });
  act(() => result.current.setPermissionGroups([{ id: 'g1', name: 'All', role: 'user', member_count: 2, permissions: ['*'] }, { id: 'g2', name: 'Some', role: 'partner', member_count: 0, permissions: ['x'], description: 'limited' }]));
  act(() => result.current.setSelectedUser({ role: 'partner' }));
  expect(result.current.selectedUserGroupOptions).toHaveLength(1);
  expect(result.current.selectedUserGroupOptions[0].description).toContain('1 Rechte');
  act(() => result.current.setUserSearch('ALICE'));
  expect(result.current.filteredUsers.map(user => user.id)).toEqual(['1']);
  act(() => result.current.setUserSearch('test.de'));
  expect(result.current.filteredUsers).toHaveLength(2);
  act(() => {
    result.current.setUsers([{ id: '3', name: 'Carol', email: 'unrelated@example.org', role: 'user' }]);
    result.current.setUserSearch('carol');
    result.current.setUserRoleFilter('all');
  });
  expect(result.current.filteredUsers.map(user => user.id)).toEqual(['3']);
  act(() => result.current.setUserSearch(''));
  expect(result.current.filteredUsers.map(user => user.id)).toEqual(['3']);
  act(() => {
    result.current.setUsers([{ id: '1', name: 'Alice', email: 'alice@test.de', role: 'user' }, { id: '2', name: 'Bob', email: 'other@test.de', role: 'partner' }]);
    result.current.setUserRoleFilter('partner');
  });
  expect(result.current.filteredUsers.map(user => user.id)).toEqual(['2']);
  act(() => {
    result.current.setShowUserDialog(true); result.current.setShowCreateUserDialog(true); result.current.setUserManagementView('groups');
    result.current.setUserPermissionDraft({ group_ids: ['g1'], allow: ['x'], deny: [] }); result.current.setSavingUserPermissions(true);
    result.current.setSelectedUserIds(['1']); result.current.setBulkRole('admin');
  });
  expect(result.current).toMatchObject({ showUserDialog: true, showCreateUserDialog: true, userManagementView: 'groups', savingUserPermissions: true, bulkRole: 'admin' });
});

test('step state sorts and paginates while all setters remain usable', () => {
  const { result } = renderHook(() => useAdminSteps());
  expect(result.current).toMatchObject({ showStepDialog: false, showTemplatesPanel: false });
  act(() => {
    result.current.setSteps([{ id: 'b', order: 2 }, { id: 'a', order: 1 }]); result.current.setSurveys([{ id: 's' }]); result.current.setActiveSurveyId('s');
    result.current.setEditingStep({ id: 'a' }); result.current.setShowStepDialog(true); result.current.setStepTemplates([{ id: 't' }]); result.current.setShowTemplatesPanel(true); result.current.setStepsView('list');
  });
  expect(result.current.sortedSteps.map(step => step.id)).toEqual(['a', 'b']);
  expect(result.current.templatesPagination.paginatedItems).toHaveLength(1);
  expect(result.current).toMatchObject({ activeSurveyId: 's', showStepDialog: true, showTemplatesPanel: true, stepsView: 'list' });
});

test('partner state switches between active and pending partners', () => {
  const { result } = renderHook(() => useAdminPartners());
  expect(result.current.showPartnerDialog).toBe(false);
  act(() => {
    result.current.setPartners([{ id: 'a', registration_status: 'active' }, { id: 'p', registration_status: 'pending' }]);
    result.current.setEditingPartner({ id: 'a' }); result.current.setShowPartnerDialog(true); result.current.setShowLinkDialog({ id: 'a' });
  });
  expect(result.current.visiblePartners.map(partner => partner.id)).toEqual(['a']);
  act(() => result.current.setPartnerView('pending'));
  expect(result.current.visiblePartners.map(partner => partner.id)).toEqual(['p']);
  expect(result.current.partnersPagination.paginatedItems).toHaveLength(1);
});

test('CMS state exposes every content, translation and saving setter', () => {
  const { result } = renderHook(() => useAdminCms());
  expect(result.current.cmsSaving).toBe(false);
  act(() => {
    result.current.setCmsHome({ h: 1 }); result.current.setCmsAbout({ a: 1 }); result.current.setCmsPartners({ p: 1 }); result.current.setCmsLandingPages({ pages: [1] });
    result.current.setCmsHomeTrans({ en: 1 }); result.current.setCmsAboutTrans({ en: 2 }); result.current.setCmsPartnersTrans({ en: 3 }); result.current.setCmsLandingPagesTrans({ en: 4 });
    result.current.setCmsLang('en'); result.current.setCmsSaving(true);
  });
  expect(result.current).toMatchObject({ cmsHome: { h: 1 }, cmsAbout: { a: 1 }, cmsPartners: { p: 1 }, cmsLandingPages: { pages: [1] }, cmsLang: 'en', cmsSaving: true });
});

test('billing state exposes settings, audit, totals and busy setters', () => {
  const { result } = renderHook(() => useAdminBilling());
  expect(result.current).toMatchObject({ stripeAuditLoading: false, settingsSaving: false });
  act(() => {
    result.current.setAdminBilling({ partners: [1], totals: { value: 2 } }); result.current.setStripeAudit({ defective: 1 }); result.current.setStripeAuditLoading(true);
    result.current.setSiteSettings({ site_title: 'Title' }); result.current.setSettingsSaving(true);
  });
  expect(result.current).toMatchObject({ adminBilling: { partners: [1], totals: { value: 2 } }, stripeAudit: { defective: 1 }, stripeAuditLoading: true, siteSettings: { site_title: 'Title' }, settingsSaving: true });
});
