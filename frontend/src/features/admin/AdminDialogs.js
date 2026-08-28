import { ConfirmDialog } from '../../components/ConfirmDialog';
import { StepDialog } from './AdminDashboardComponents/StepDialog';
import { PartnerDialog } from './AdminDashboardComponents/PartnerDialog';
import { LinkUserDialog } from './AdminDashboardComponents/LinkUserDialog';
import { CreateUserDialog } from './AdminDashboardComponents/CreateUserDialog';
import { UserDetailDialog } from './UserDetailDialog';
import {
    defaultSurveyId,
    dialogIsOpen,
    partnerUserFeeCents,
    partnerUsers,
} from './adminDialogViewModels';

// Stryker disable all: declarative dialog composition; selection rules live in adminDialogViewModels.
export function AdminDialogs(props) {
    const { t, users, steps, surveys, activeSurveyId, partners, selectedUser, showUserDialog, setShowUserDialog, showCreateUserDialog, setShowCreateUserDialog, permissionGroups, userPermissionDraft, setUserPermissionDraft, savingUserPermissions, editingStep, setEditingStep, showStepDialog, setShowStepDialog, editingPartner, setEditingPartner, showPartnerDialog, setShowPartnerDialog, showLinkDialog, setShowLinkDialog, confirmDialog, setConfirmDialog, siteSettings, can, permissionOptions, selectedUserGroupOptions, handleSaveUserPermissions, handleUpdateUserProgress, handleSaveStep, handleSurveyChange, handleSavePartner, handleLinkUser, handleCreateUser } = props;
    return <>
{/* User Detail Dialog */}
            <UserDetailDialog
                showUserDialog={showUserDialog}
                setShowUserDialog={setShowUserDialog}
                selectedUser={selectedUser}
                selectedUserGroupOptions={selectedUserGroupOptions}
                userPermissionDraft={userPermissionDraft}
                setUserPermissionDraft={setUserPermissionDraft}
                savingUserPermissions={savingUserPermissions}
                handleSaveUserPermissions={handleSaveUserPermissions}
                can={can}
                permissionOptions={permissionOptions}
                steps={steps}
                handleUpdateUserProgress={handleUpdateUserProgress}
                partners={partners}
            />

            {/* Step Edit Dialog */}
            <StepDialog
                open={showStepDialog}
                onClose={() => { setShowStepDialog(false); setEditingStep(null); }}
                step={editingStep}
                onSave={handleSaveStep}
                existingSteps={steps}
                surveys={surveys}
                partners={partners}
                activeSurveyId={activeSurveyId}
                onSurveyChange={handleSurveyChange}
                t={t}
            />

            {/* Partner Edit Dialog */}
            <PartnerDialog
                open={showPartnerDialog}
                onClose={() => { setShowPartnerDialog(false); setEditingPartner(null); }}
                partner={editingPartner}
                onSave={handleSavePartner}
                allUsers={users}
                allPartners={partners}
                surveys={surveys}
                defaultUserFeeCents={partnerUserFeeCents(siteSettings)}
                t={t}
            />

            {/* Link User to Partner Dialog */}
            <LinkUserDialog
                open={dialogIsOpen(showLinkDialog)}
                onClose={() => setShowLinkDialog(null)}
                partner={showLinkDialog}
                users={partnerUsers(users)}
                onLink={handleLinkUser}
            />

            {/* Create User Dialog */}
            <CreateUserDialog
                open={showCreateUserDialog}
                onClose={() => setShowCreateUserDialog(false)}
                onSave={handleCreateUser}
                partners={partners}
                surveys={surveys}
                permissionGroups={permissionGroups}
                canManagePermissions={can('users.permissions.manage')}
                defaultSurveyId={defaultSurveyId(activeSurveyId, surveys)}
                t={t}
            />
            <ConfirmDialog open={dialogIsOpen(confirmDialog)} onOpenChange={() => setConfirmDialog(null)} message={confirmDialog?.message} confirmLabel="Ja, loeschen" destructive onConfirm={() => confirmDialog?.onConfirm()} />
    </>;
}
