import { adminAPI, settingsAPI } from '../../../lib/api';
import { toast } from 'sonner';
import { useAdminBillingCommands } from './useAdminBillingCommands';
import { useAdminCmsCommands } from './useAdminCmsCommands';
import { useAdminPartnerCommands } from './useAdminPartnerCommands';
import { useAdminStepCommands } from './useAdminStepCommands';
import { useAdminUserCommands } from './useAdminUserCommands';

jest.mock('../../../lib/api', () => ({
  adminAPI: Object.fromEntries(['auditStripeConnections','repairStripeConnection','repairAllStripeConnections','updateCmsContent','updatePartner','createPartner','deletePartner','linkPartnerUser','unlinkPartnerUser','updateStep','createStep','createSurvey','deleteStep','reorderSteps','saveStepAsTemplate','applyStepTemplate','deleteStepTemplate','impersonateUser','getUser','updateUserPermissions','updateUserRole','updateUserProgress','bulkUpdateRole','exportUsersCsv','createUser'].map(key => [key, jest.fn()])),
  settingsAPI: { update: jest.fn() },
  formatApiError: () => 'api error',
}));
jest.mock('sonner', () => ({ toast: { success: jest.fn(), error: jest.fn() } }));

const ok = (data = {}) => Promise.resolve({ data });
const fail = () => Promise.reject(new Error('failed'));

beforeEach(() => {
  jest.clearAllMocks();
  Object.values(adminAPI).forEach(mock => mock.mockReturnValue(ok()));
  settingsAPI.update.mockReturnValue(ok());
});

test('billing commands cover settings, audits, individual and bulk repairs', async () => {
  const deps = { setSettingsSaving: jest.fn(), siteSettings: { title: 'x' }, loadData: jest.fn(), setStripeAuditLoading: jest.fn(), setStripeAudit: jest.fn() };
  const commands = useAdminBillingCommands(deps);
  adminAPI.auditStripeConnections.mockReturnValue(ok({ entries: [1] }));
  await commands.handleSaveSettings();
  expect(deps.setSettingsSaving.mock.calls).toEqual([[true], [false]]);
  await commands.auditStripeConnections();
  expect(deps.setStripeAuditLoading.mock.calls.slice(0, 2)).toEqual([[true], [false]]);
  await commands.repairStripeConnection('p1');
  expect(deps.setStripeAudit).toHaveBeenCalledWith({ entries: [1] });
  expect(deps.loadData).toHaveBeenCalledTimes(2);
  deps.setStripeAuditLoading.mockClear();
  jest.spyOn(window, 'confirm').mockReturnValueOnce(false).mockReturnValueOnce(true);
  await commands.repairAllStripeConnections();
  expect(adminAPI.repairAllStripeConnections).not.toHaveBeenCalled();
  adminAPI.repairAllStripeConnections.mockReturnValue(ok({ repaired: 2, skipped: 1 }));
  await commands.repairAllStripeConnections();
  expect(deps.setStripeAuditLoading.mock.calls).toEqual([[true], [true], [false]]);
  expect(toast.success).toHaveBeenCalledWith('2 Stripe-Verbindungen repariert, 1 übersprungen');
  window.confirm.mockRestore();
});

test('billing commands report every failure and reset busy state', async () => {
  const deps = { setSettingsSaving: jest.fn(), siteSettings: {}, loadData: jest.fn(), setStripeAuditLoading: jest.fn(), setStripeAudit: jest.fn() };
  const commands = useAdminBillingCommands(deps);
  settingsAPI.update.mockImplementationOnce(fail);
  await commands.handleSaveSettings();
  adminAPI.auditStripeConnections.mockImplementationOnce(fail);
  await commands.auditStripeConnections();
  adminAPI.repairStripeConnection.mockImplementationOnce(fail);
  await commands.repairStripeConnection('p');
  jest.spyOn(window, 'confirm').mockReturnValue(true);
  adminAPI.repairAllStripeConnections.mockImplementationOnce(fail);
  await commands.repairAllStripeConnections();
  expect(toast.error).toHaveBeenCalledTimes(4);
  expect(deps.setSettingsSaving).toHaveBeenLastCalledWith(false);
  expect(deps.setStripeAuditLoading).toHaveBeenLastCalledWith(false);
  window.confirm.mockRestore();
});

test('CMS command saves and reports failures with balanced busy state', async () => {
  const deps = { setCmsSaving: jest.fn(), loadData: jest.fn() };
  const { handleSaveCms } = useAdminCmsCommands(deps);
  await handleSaveCms('home', { a: 1 }, { en: {} });
  expect(deps.setCmsSaving.mock.calls).toEqual([[true], [false]]);
  expect(adminAPI.updateCmsContent).toHaveBeenCalledWith('home', { a: 1 }, { en: {} });
  expect(deps.loadData).toHaveBeenCalled();
  adminAPI.updateCmsContent.mockImplementationOnce(fail);
  await handleSaveCms('about', {}, {});
  expect(toast.error).toHaveBeenCalledWith('api error');
  expect(deps.setCmsSaving).toHaveBeenLastCalledWith(false);
});

function partnerCommands(editingPartner = null) {
  const deps = { editingPartner, setShowPartnerDialog: jest.fn(), setEditingPartner: jest.fn(), loadData: jest.fn(), setConfirmDialog: jest.fn(), setShowLinkDialog: jest.fn() };
  return { deps, commands: useAdminPartnerCommands(deps) };
}

test('partner commands create, update, delete, link and unlink', async () => {
  let setup = partnerCommands();
  await setup.commands.handleSavePartner({ name: 'new' });
  expect(adminAPI.createPartner).toHaveBeenCalled();
  setup = partnerCommands({ id: 'p1' });
  await setup.commands.handleSavePartner({ name: 'updated' });
  expect(setup.deps.setShowPartnerDialog).toHaveBeenCalledWith(false);
  expect(adminAPI.updatePartner).toHaveBeenCalledWith('p1', { name: 'updated' });
  await setup.commands.handleLinkUser('p1', 'u1');
  await setup.commands.handleUnlinkUser('p1');
  await setup.commands.handleDeletePartner('p1');
  const dialog = setup.deps.setConfirmDialog.mock.calls[0][0];
  await dialog.onConfirm();
  expect(adminAPI.deletePartner).toHaveBeenCalledWith('p1');
  expect(setup.deps.setConfirmDialog).toHaveBeenLastCalledWith(null);
});

test('partner commands report failures including deferred delete', async () => {
  const { deps, commands } = partnerCommands({ id: 'p1' });
  for (const [method, invoke] of [
    ['updatePartner', () => commands.handleSavePartner({})],
    ['linkPartnerUser', () => commands.handleLinkUser('p1', 'u1')],
    ['unlinkPartnerUser', () => commands.handleUnlinkUser('p1')],
  ]) {
    adminAPI[method].mockImplementationOnce(fail);
    await invoke();
  }
  await commands.handleDeletePartner('p1');
  adminAPI.deletePartner.mockImplementationOnce(fail);
  await deps.setConfirmDialog.mock.calls[0][0].onConfirm();
  expect(toast.error).toHaveBeenCalledTimes(4);
});

function stepCommands(overrides = {}) {
  const deps = { activeSurveyId: 'survey', editingStep: null, setSteps: jest.fn(), setShowStepDialog: jest.fn(), setEditingStep: jest.fn(), loadData: jest.fn(), setActiveSurveyId: jest.fn(), setShowTemplatesPanel: jest.fn(), setStepsView: jest.fn(), surveys: [{ id: 'survey', slug: 'survey-slug' }], navigate: jest.fn(), setConfirmDialog: jest.fn(), steps: [{ id: 'a', order: 1 }, { id: 'b', order: 2 }], ...overrides };
  return { deps, commands: useAdminStepCommands(deps) };
}

test('step commands create and update steps and switch surveys', async () => {
  let setup = stepCommands();
  await setup.commands.handleSaveStep({ title: 'New' });
  expect(adminAPI.createStep).toHaveBeenCalledWith(expect.objectContaining({ survey_id: 'survey' }));
  setup = stepCommands({ editingStep: { id: 'a' } });
  await setup.commands.handleSaveStep({ title: 'Changed', survey_id: 'other' });
  const update = setup.deps.setSteps.mock.calls[0][0];
  expect(update([{ id: 'a', old: true }, { id: 'b' }])[0]).toMatchObject({ id: 'a', title: 'Changed' });
  expect(update([{ id: 'a' }, { id: 'b' }])[1]).toEqual({ id: 'b' });
  setup.commands.handleSurveyChange('survey');
  expect(setup.deps.navigate).toHaveBeenCalledWith('/admin?tab=steps&survey=survey-slug&step=1', { replace: true });
  setup = stepCommands({ surveys: [] });
  setup.commands.handleSurveyChange('raw id');
  expect(setup.deps.navigate).toHaveBeenCalledWith('/admin?tab=steps&survey=raw%20id&step=1', { replace: true });
});

test('step survey and template prompts cover aborts, validation and success', async () => {
  const { commands } = stepCommands({ steps: [] });
  jest.spyOn(window, 'prompt');
  window.prompt.mockReturnValueOnce(null);
  await commands.handleCreateSurvey();
  window.prompt.mockReturnValueOnce('  ').mockReturnValueOnce('Name').mockReturnValueOnce('  ').mockReturnValueOnce(' My Survey ').mockReturnValueOnce(' my-slug ');
  await commands.handleCreateSurvey(); await commands.handleCreateSurvey(); await commands.handleCreateSurvey();
  expect(adminAPI.createSurvey).toHaveBeenCalledWith(expect.objectContaining({ name: 'My Survey', slug: 'my-slug' }));
  window.prompt.mockReturnValueOnce('').mockReturnValueOnce('  ').mockReturnValueOnce('Template Name');
  await commands.handleSaveStepAsTemplate({ id: 's', title: 'Step' });
  await commands.handleSaveStepAsTemplate({ id: 's', title: 'Step' });
  await commands.handleSaveStepAsTemplate({ id: 's', title: 'Step' });
  expect(adminAPI.saveStepAsTemplate).toHaveBeenCalledWith('s', 'Template Name', '');
  for (const input of [null, 'x', '0', '2']) { window.prompt.mockReturnValueOnce(input); await commands.handleApplyTemplate({ id: 't', name: 'Tpl' }); }
  expect(adminAPI.applyStepTemplate).toHaveBeenCalledWith('t', 2, 'survey');
  window.prompt.mockRestore();
});

test('step move and deferred delete commands cover boundaries and failures', async () => {
  const { deps, commands } = stepCommands();
  await commands.handleMoveStep('a', 'up');
  await commands.handleMoveStep('b', 'down');
  await commands.handleMoveStep('b', 'up');
  await commands.handleMoveStep('a', 'down');
  expect(adminAPI.reorderSteps).toHaveBeenCalledWith(['b', 'a'], 'survey');
  await commands.handleDeleteStep('a'); const deleteStep = deps.setConfirmDialog.mock.calls[0][0]; await deleteStep.onConfirm();
  commands.handleDeleteTemplate({ id: 't', name: 'Tpl' }); const deleteTemplate = deps.setConfirmDialog.mock.calls[2][0]; await deleteTemplate.onConfirm();
  adminAPI.reorderSteps.mockImplementationOnce(fail); await commands.handleMoveStep('b', 'up');
  adminAPI.deleteStep.mockImplementationOnce(fail); await commands.handleDeleteStep('a'); await deps.setConfirmDialog.mock.calls[4][0].onConfirm();
  adminAPI.deleteStepTemplate.mockImplementationOnce(fail); commands.handleDeleteTemplate({ id: 't', name: 'Tpl' }); await deps.setConfirmDialog.mock.calls[6][0].onConfirm();
  expect(toast.error).toHaveBeenCalledTimes(3);
});

test('step API failures are reported for save, survey, and template commands', async () => {
  const { commands } = stepCommands();
  adminAPI.createStep.mockImplementationOnce(fail); await commands.handleSaveStep({});
  jest.spyOn(window, 'prompt').mockReturnValueOnce('Name').mockReturnValueOnce('slug'); adminAPI.createSurvey.mockImplementationOnce(fail); await commands.handleCreateSurvey();
  window.prompt.mockReturnValueOnce('Tpl'); adminAPI.saveStepAsTemplate.mockImplementationOnce(fail); await commands.handleSaveStepAsTemplate({ id: 's', title: 'S', description: 'D' });
  window.prompt.mockReturnValueOnce('1'); adminAPI.applyStepTemplate.mockImplementationOnce(fail); await commands.handleApplyTemplate({ id: 't', name: 'T' });
  expect(toast.error).toHaveBeenCalledTimes(4); window.prompt.mockRestore();
});

test('step commands preserve every prompt, state transition, payload and notification', async () => {
  let setup = stepCommands();
  await setup.commands.handleSaveStep({ title: 'New' });
  expect(toast.success).toHaveBeenLastCalledWith('Step created');
  expect(setup.deps.setShowStepDialog).toHaveBeenCalledWith(false);
  expect(setup.deps.setEditingStep).toHaveBeenCalledWith(null);
  expect(setup.deps.loadData).toHaveBeenCalledTimes(1);

  setup = stepCommands({ editingStep: { id: 'a' } });
  await setup.commands.handleSaveStep({ title: 'Updated' });
  expect(toast.success).toHaveBeenLastCalledWith('Step updated');

  jest.spyOn(window, 'prompt');
  window.prompt.mockReturnValueOnce('My Multi Word Survey').mockReturnValueOnce(' survey-slug ');
  await setup.commands.handleCreateSurvey();
  expect(window.prompt).toHaveBeenNthCalledWith(1, 'Name des neuen Surveys:', 'FSP Pflege');
  expect(window.prompt).toHaveBeenNthCalledWith(2, 'URL-Slug, z.B. pflege:', 'my-multi-word-survey');
  expect(adminAPI.createSurvey).toHaveBeenCalledWith({ name: 'My Multi Word Survey', slug: 'survey-slug', description: '', audience: '', is_active: true, is_default: false });
  expect(toast.success).toHaveBeenLastCalledWith('Survey angelegt');
  expect(setup.deps.setActiveSurveyId).toHaveBeenCalledWith('');

  setup.commands.handleSurveyChange('survey');
  expect(setup.deps.setEditingStep).toHaveBeenLastCalledWith(null);
  expect(setup.deps.setShowTemplatesPanel).toHaveBeenCalledWith(false);
  expect(setup.deps.setStepsView).toHaveBeenCalledWith('list');
  expect(setup.deps.setSteps).toHaveBeenCalledWith([]);

  await setup.commands.handleDeleteStep('a');
  const stepConfirmation = setup.deps.setConfirmDialog.mock.calls[0][0];
  expect(stepConfirmation.message).toBe('Sind Sie sicher, dass Sie diesen Schritt loeschen moechten? Alle Fortschrittsdaten der Nutzer fuer diesen Schritt werden ebenfalls entfernt.');
  await stepConfirmation.onConfirm();
  expect(toast.success).toHaveBeenLastCalledWith('Step deleted');

  setup = stepCommands({ steps: [{ id: 'c', order: 3 }, { id: 'a', order: 1 }, { id: 'b', order: 2 }] });
  await setup.commands.handleMoveStep('b', 'up');
  expect(adminAPI.reorderSteps).toHaveBeenLastCalledWith(['b', 'a', 'c'], 'survey');
  expect(toast.success).toHaveBeenLastCalledWith('Steps reordered');
  await setup.commands.handleMoveStep('b', 'down');
  expect(adminAPI.reorderSteps).toHaveBeenLastCalledWith(['a', 'c', 'b'], 'survey');

  window.prompt.mockClear().mockReturnValueOnce('  Saved Template  ');
  await setup.commands.handleSaveStepAsTemplate({ id: 's', title: 'Source', description: undefined });
  expect(window.prompt).toHaveBeenCalledWith('Template-Name für "Source":', 'Source');
  expect(adminAPI.saveStepAsTemplate).toHaveBeenLastCalledWith('s', 'Saved Template', '');
  expect(toast.success).toHaveBeenLastCalledWith('Als Template gespeichert');

  window.prompt.mockClear().mockReturnValueOnce('1');
  await setup.commands.handleApplyTemplate({ id: 'template', name: 'Template' });
  expect(window.prompt).toHaveBeenCalledWith('An welcher Position soll "Template" eingefügt werden? (1-4)', '4');
  expect(adminAPI.applyStepTemplate).toHaveBeenLastCalledWith('template', 1, 'survey');
  expect(toast.success).toHaveBeenLastCalledWith('Template "Template" eingefügt');

  window.prompt.mockReturnValueOnce('0');
  await setup.commands.handleApplyTemplate({ id: 'invalid', name: 'Invalid' });
  expect(toast.error).toHaveBeenLastCalledWith('Ungültige Position');

  setup.commands.handleDeleteTemplate({ id: 'template', name: 'Template' });
  const templateConfirmation = setup.deps.setConfirmDialog.mock.calls.at(-1)[0];
  expect(templateConfirmation.message).toBe('Template "Template" dauerhaft löschen?');
  await templateConfirmation.onConfirm();
  expect(toast.success).toHaveBeenLastCalledWith('Template gelöscht');
  window.prompt.mockRestore();
});

test('step command guards reject cancelled input and movement boundaries exactly', async () => {
  const setup = stepCommands({
    surveys: [{ id: 'other', slug: 'wrong' }, { id: 'survey', slug: 'right' }],
    steps: [{ id: 'first', order: 1 }, { id: 'middle', order: 2 }, { id: 'last', order: 3 }],
  });
  jest.spyOn(window, 'prompt');

  window.prompt.mockReturnValueOnce('My   Spaced Survey').mockReturnValueOnce(null);
  await setup.commands.handleCreateSurvey();
  expect(window.prompt).toHaveBeenNthCalledWith(2, 'URL-Slug, z.B. pflege:', 'my-spaced-survey');
  expect(adminAPI.createSurvey).not.toHaveBeenCalled();
  window.prompt.mockReturnValueOnce('Name').mockReturnValueOnce('   ');
  await setup.commands.handleCreateSurvey();
  expect(adminAPI.createSurvey).not.toHaveBeenCalled();

  setup.commands.handleSurveyChange('survey');
  expect(setup.deps.navigate).toHaveBeenCalledWith('/admin?tab=steps&survey=right&step=1', { replace: true });

  adminAPI.reorderSteps.mockClear();
  await setup.commands.handleMoveStep('first', 'up');
  await setup.commands.handleMoveStep('last', 'down');
  expect(adminAPI.reorderSteps).not.toHaveBeenCalled();
  await setup.commands.handleMoveStep('first', 'down');
  expect(adminAPI.reorderSteps).toHaveBeenLastCalledWith(['middle', 'first', 'last'], 'survey');

  adminAPI.saveStepAsTemplate.mockClear();
  window.prompt.mockReturnValueOnce(null);
  await setup.commands.handleSaveStepAsTemplate({ id: 's', title: 'Source' });
  window.prompt.mockReturnValueOnce('   ');
  await setup.commands.handleSaveStepAsTemplate({ id: 's', title: 'Source' });
  expect(adminAPI.saveStepAsTemplate).not.toHaveBeenCalled();

  adminAPI.applyStepTemplate.mockClear();
  toast.error.mockClear();
  window.prompt.mockReturnValueOnce(null);
  await setup.commands.handleApplyTemplate({ id: 't', name: 'Template' });
  expect(adminAPI.applyStepTemplate).not.toHaveBeenCalled();
  expect(toast.error).not.toHaveBeenCalled();
  window.prompt.mockRestore();
});

function userCommands(overrides = {}) {
  const deps = { impersonate: jest.fn(), navigate: jest.fn(), setSelectedUser: jest.fn(), setUserPermissionDraft: jest.fn(), setShowUserDialog: jest.fn(), selectedUser: { id: 'u1' }, setSavingUserPermissions: jest.fn(), userPermissionDraft: { allow: [] }, loadPermissionData: jest.fn(), loadData: jest.fn(), setSelectedUserIds: jest.fn(), selectedUserIds: ['u1'], filteredUsers: [{ id: 'u1' }, { id: 'u2' }], bulkRole: 'partner', setShowCreateUserDialog: jest.fn(), ...overrides };
  return { deps, commands: useAdminUserCommands(deps) };
}

test('user commands cover impersonation, details, permissions, progress and roles', async () => {
  const setup = userCommands();
  adminAPI.impersonateUser.mockReturnValueOnce(ok({ access_token: 'token', user: { role: 'partner' } })).mockReturnValueOnce(ok({ access_token: 'token', user: { role: 'user' } }));
  await setup.commands.handleImpersonate('p'); await setup.commands.handleImpersonate('u');
  expect(setup.deps.navigate).toHaveBeenNthCalledWith(1, '/partner-dashboard'); expect(setup.deps.navigate).toHaveBeenNthCalledWith(2, '/dashboard');
  adminAPI.getUser.mockReturnValue(ok({ id: 'u1' })); await setup.commands.handleViewUser('u1');
  expect(setup.deps.setShowUserDialog).toHaveBeenCalledWith(true);
  expect(setup.deps.setUserPermissionDraft).toHaveBeenCalledWith({ group_ids: [], allow: [], deny: [] });
  adminAPI.updateUserPermissions.mockReturnValue(ok({ group_ids: ['g'], permission_overrides: {}, effective_permissions: ['x'] })); await setup.commands.handleSaveUserPermissions();
  expect(setup.deps.setSavingUserPermissions.mock.calls).toEqual([[true], [false]]);
  expect(setup.deps.setSelectedUser.mock.calls.at(-1)[0]({ name: 'U' })).toMatchObject({ name: 'U', group_ids: ['g'] });
  await setup.commands.handleUpdateUserRole('u1', 'admin');
  adminAPI.getUser.mockReturnValue(ok({ id: 'u1', fresh: true })); await setup.commands.handleUpdateUserProgress('u1', 's1', 'completed');
});

test('user selections, bulk update, export and creation cover both paths', async () => {
  let setup = userCommands();
  setup.commands.toggleUserSelection('u1'); let updater = setup.deps.setSelectedUserIds.mock.calls[0][0]; expect(updater(['u1','u2'])).toEqual(['u2']); expect(updater([])).toEqual(['u1']);
  setup.commands.toggleSelectAll(); expect(setup.deps.setSelectedUserIds).toHaveBeenCalledWith(setup.deps.filteredUsers.map(u => u.id));
  setup = userCommands({ selectedUserIds: ['u1','u2'] }); setup.commands.toggleSelectAll(); expect(setup.deps.setSelectedUserIds).toHaveBeenCalledWith([]);
  await setup.commands.handleBulkRoleUpdate(); expect(adminAPI.bulkUpdateRole).toHaveBeenCalledWith(['u1','u2'], 'partner');
  setup = userCommands({ selectedUserIds: [] }); await setup.commands.handleBulkRoleUpdate(); expect(toast.error).toHaveBeenCalledWith('No users selected');
  window.URL.createObjectURL = jest.fn(() => 'blob:url'); window.URL.revokeObjectURL = jest.fn(); jest.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});
  adminAPI.exportUsersCsv.mockReturnValue(ok('csv')); await setup.commands.handleExportCsv(); expect(window.URL.revokeObjectURL).toHaveBeenCalledWith('blob:url');
  await setup.commands.handleCreateUser({ email: 'u@example.com' }); expect(setup.deps.setShowCreateUserDialog).toHaveBeenCalledWith(false);
  HTMLAnchorElement.prototype.click.mockRestore();
});

test('user commands report all API failures and permissions guard null user', async () => {
  let setup = userCommands({ selectedUser: null }); await setup.commands.handleSaveUserPermissions(); expect(adminAPI.updateUserPermissions).not.toHaveBeenCalled();
  setup = userCommands();
  for (const [method, invoke] of [
    ['impersonateUser', () => setup.commands.handleImpersonate('u')], ['getUser', () => setup.commands.handleViewUser('u')], ['updateUserPermissions', () => setup.commands.handleSaveUserPermissions()], ['updateUserRole', () => setup.commands.handleUpdateUserRole('u','admin')], ['updateUserProgress', () => setup.commands.handleUpdateUserProgress('u','s','completed')], ['bulkUpdateRole', () => setup.commands.handleBulkRoleUpdate()], ['exportUsersCsv', () => setup.commands.handleExportCsv()], ['createUser', () => setup.commands.handleCreateUser({})],
  ]) { adminAPI[method].mockImplementationOnce(fail); await invoke(); }
  expect(toast.error).toHaveBeenCalledTimes(8);
});
