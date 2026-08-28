import { useState, useEffect, useCallback } from 'react';
import { Button } from '../../../components/ui/button';
import { Input } from '../../../components/ui/input';
import { Label } from '../../../components/ui/label';

import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../../components/ui/select';


import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../../../components/ui/dialog';

import { SearchableMultiSelect } from '../../../components/admin/EntityPickers';
import { activeSurveys, createUserPayload, emptyCreateUser, groupsForRole, sortedPartners, systemGroupIdsForRole } from '../adminUserDialogDomain';


const EMPTY_PERMISSION_GROUPS = [];

// Stryker disable all: declarative form adapter; form rules live in adminUserDialogDomain.
export function CreateUserDialog({ open, onClose, onSave, partners, surveys, permissionGroups = EMPTY_PERMISSION_GROUPS, canManagePermissions = false, defaultSurveyId, t }) {
    const defaultGroupsForRole = useCallback((role) => systemGroupIdsForRole(permissionGroups, role), [permissionGroups]);
    const [formData, setFormData] = useState(() => emptyCreateUser(defaultSurveyId));

    useEffect(() => {
        if (open) setFormData(emptyCreateUser(defaultSurveyId, defaultGroupsForRole('user')));
    }, [open, defaultSurveyId, defaultGroupsForRole]);

    const handleSubmit = (e) => {
        e.preventDefault();
        onSave(createUserPayload(formData, canManagePermissions));
    };

    return (
        <Dialog open={open} onOpenChange={onClose}>
            <DialogContent className="max-w-md max-h-[85vh] overflow-y-auto">
                <DialogHeader>
                    <DialogTitle>{t('create_user_title')}</DialogTitle>
                </DialogHeader>
                <form onSubmit={handleSubmit} className="space-y-4">
                    <div><Label>{t('create_user_name')}</Label><Input value={formData.name} onChange={e => setFormData({ ...formData, name: e.target.value })} className="mt-1" required data-testid="create-user-name" /></div>
                    <div><Label>{t('create_user_email')}</Label><Input type="email" value={formData.email} onChange={e => setFormData({ ...formData, email: e.target.value })} className="mt-1" required data-testid="create-user-email" /></div>
                    <div><Label>{t('create_user_password')}</Label><Input type="password" value={formData.password} onChange={e => setFormData({ ...formData, password: e.target.value })} className="mt-1" required minLength={6} data-testid="create-user-password" /></div>
                    <div>
                        <Label>{t('create_user_role')}</Label>
                        <Select value={formData.role} onValueChange={val => setFormData({ ...formData, role: val, partner_id: val !== 'partner' ? 'none' : formData.partner_id, group_ids: defaultGroupsForRole(val) })}>
                            <SelectTrigger className="mt-1" data-testid="create-user-role"><SelectValue /></SelectTrigger>
                            <SelectContent>
                                <SelectItem value="user">{t('user')}</SelectItem>
                                <SelectItem value="partner">{t('partner')}</SelectItem>
                                {canManagePermissions && <SelectItem value="admin">Admin</SelectItem>}
                            </SelectContent>
                        </Select>
                    </div>
                    {canManagePermissions && <div>
                        <Label>Nutzergruppen</Label>
                        <p className="mb-2 mt-1 text-xs text-muted-foreground">Passende Gruppen für die gewählte Portalrolle zuweisen.</p>
                        <SearchableMultiSelect
                            options={groupsForRole(permissionGroups, formData.role)}
                            values={formData.group_ids}
                            onChange={(group_ids) => setFormData({ ...formData, group_ids })}
                            placeholder="Nutzergruppen auswählen"
                            searchPlaceholder="Nutzergruppe suchen …"
                            testId="create-user-permission-groups"
                        />
                    </div>}
                    {formData.role === 'user' && (
                        <div>
                            <Label>Survey</Label>
                            <Select value={formData.survey_id} onValueChange={val => setFormData({ ...formData, survey_id: val })} required>
                                <SelectTrigger className="mt-1" data-testid="create-user-survey">
                                    <SelectValue placeholder="Survey auswählen" />
                                </SelectTrigger>
                                <SelectContent>
                                    {activeSurveys(surveys).map(s => (
                                        <SelectItem key={s.id} value={s.id}>{s.name} /s/{s.slug}</SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                    )}
                    {formData.role === 'partner' && (
                        <div>
                            <Label>{t('create_user_partner')}</Label>
                            <Select value={formData.partner_id} onValueChange={val => setFormData({ ...formData, partner_id: val })}>
                                <SelectTrigger className="mt-1" data-testid="create-user-partner"><SelectValue placeholder={t('create_user_no_partner')} /></SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="none">{t('create_user_no_partner')}</SelectItem>
                                    {sortedPartners(partners)
                                        .map(p => <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>)}
                                </SelectContent>
                            </Select>
                        </div>
                    )}
                    <div className="flex justify-end gap-3 pt-2">
                        <Button type="button" variant="outline" onClick={onClose}>{t('cancel')}</Button>
                        <Button type="submit" disabled={formData.role === 'user' && !formData.survey_id} className="bg-[var(--brand-primary)] hover:bg-[var(--brand-primary-hover)] text-white" data-testid="submit-create-user">{t('create_user_submit')}</Button>
                    </div>
                </form>
            </DialogContent>
        </Dialog>
    );
}
