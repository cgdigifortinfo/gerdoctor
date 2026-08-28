import { filesAPI } from '../../lib/api';
import { Button } from '../../components/ui/button';
import { Label } from '../../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../../components/ui/dialog';
import { UserCircle, Image as ImageIcon, Check, ArrowRight } from '@phosphor-icons/react';
import { SearchableMultiSelect } from '../../components/admin/EntityPickers';
import {
    completionPercent,
    displayFieldValue,
    effectivePermissionLabel,
    fieldPresentation,
    hasVisibleProgressData,
    historyAction,
    partnerNameForSubmission,
    progressData,
    stepForProgress,
} from './userDetailViewModels';

// Stryker disable all: declarative rendering; user-detail decisions live in userDetailViewModels.
export function UserDetailDialog({ showUserDialog, setShowUserDialog, selectedUser, selectedUserGroupOptions, userPermissionDraft, setUserPermissionDraft, savingUserPermissions, handleSaveUserPermissions, can, permissionOptions, steps, handleUpdateUserProgress, partners }) {
    return (
        <Dialog open={showUserDialog} onOpenChange={setShowUserDialog}>
                        <DialogContent className="max-w-4xl max-h-[88vh] overflow-y-auto">
                            <DialogHeader>
                                <DialogTitle>User Details</DialogTitle>
                            </DialogHeader>
                            {selectedUser && (
                                <div className="space-y-6">
                                    {/* Profile Image + Basic Info */}
                                    <div className="flex items-start gap-6">
                                        {/* Profile Image Preview */}
                                        <div className="flex-shrink-0">
                                            {selectedUser.profile?.profile_image ? (
                                                <img
                                                    src={filesAPI.getUrl(selectedUser.profile.profile_image)}
                                                    alt={selectedUser.name}
                                                    className="w-20 h-20 rounded-full object-cover border-2 border-border"
                                                    data-testid="user-profile-image"
                                                    onError={(e) => { e.target.style.display = 'none'; e.target.nextSibling.style.display = 'flex'; }}
                                                />
                                            ) : null}
                                            <div className={`w-20 h-20 rounded-full bg-muted flex items-center justify-center ${selectedUser.profile?.profile_image ? 'hidden' : ''}`}>
                                                <UserCircle size={40} className="text-muted-foreground" />
                                            </div>
                                        </div>
                                        <div className="flex-1 grid grid-cols-2 gap-4">
                                            <div>
                                                <Label className="text-muted-foreground">Name</Label>
                                                <p className="font-medium">{selectedUser.name}</p>
                                                {selectedUser.partner_registration_status === 'pending' && <span className="inline-flex mt-1 px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 text-xs font-bold">Neu registrierter Partner · Survey-Zuordnung offen</span>}
                                            </div>
                                            <div>
                                                <Label className="text-muted-foreground">Email</Label>
                                                <p className="font-medium">{selectedUser.email}</p>
                                            </div>
                                            <div>
                                                <Label className="text-muted-foreground">Role</Label>
                                                <p className="font-medium capitalize">{selectedUser.role}</p>
                                            </div>
                                            <div>
                                                <Label className="text-muted-foreground">Created</Label>
                                                <p className="font-medium">{selectedUser.created_at ? new Date(selectedUser.created_at).toLocaleDateString() : '-'}</p>
                                            </div>
                                        </div>
                                    </div>
        
                                    {/* Groups and per-user permission overrides */}
                                    <section className="rounded-lg border border-border p-4" data-testid="user-permissions-editor">
                                        <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
                                            <div><h4 className="font-semibold">Nutzergruppen und individuelle Rechte</h4><p className="mt-1 text-xs text-muted-foreground">Gruppenrechte bilden die Basis. „Erlauben“ ergänzt Rechte; „Verweigern“ hat immer Vorrang.</p></div>
                                            <span className="rounded-full bg-[var(--brand-primary)]/10 px-3 py-1 text-xs font-medium text-[var(--brand-primary)]">{effectivePermissionLabel(selectedUser.effective_permissions)}</span>
                                        </div>
                                        {selectedUser.is_primary_admin ? (
                                            <div className="rounded-md bg-amber-50 p-3 text-sm text-amber-800 dark:bg-amber-900/20 dark:text-amber-300">Das primäre Administratorkonto behält aus Sicherheitsgründen immer Vollzugriff.</div>
                                        ) : can('users.permissions.manage') ? (
                                            <div className="space-y-4">
                                                <div><Label>Nutzergruppen</Label><p className="mb-2 text-xs text-muted-foreground">Mehrere Gruppen derselben Portalrolle können kombiniert werden.</p><SearchableMultiSelect options={selectedUserGroupOptions} values={userPermissionDraft.group_ids} onChange={(group_ids) => setUserPermissionDraft({ ...userPermissionDraft, group_ids })} placeholder="Nutzergruppen auswählen" searchPlaceholder="Nutzergruppe suchen …" testId="user-permission-groups" /></div>
                                                <div className="grid gap-4 md:grid-cols-2">
                                                    <div className="rounded-md border border-green-200 p-3 dark:border-green-900"><Label className="text-green-700 dark:text-green-300">Zusätzlich erlauben</Label><p className="mb-2 mt-1 text-xs text-muted-foreground">Diese Rechte gelten unabhängig von den Gruppen.</p><SearchableMultiSelect options={permissionOptions} values={userPermissionDraft.allow} onChange={(allow) => setUserPermissionDraft({ ...userPermissionDraft, allow, deny: userPermissionDraft.deny.filter((key) => !allow.includes(key)) })} placeholder="Rechte erlauben" searchPlaceholder="Berechtigung suchen …" testId="user-permission-allow" /></div>
                                                    <div className="rounded-md border border-red-200 p-3 dark:border-red-900"><Label className="text-red-700 dark:text-red-300">Ausdrücklich verweigern</Label><p className="mb-2 mt-1 text-xs text-muted-foreground">Deny überschreibt Gruppenrechte und individuelle Freigaben.</p><SearchableMultiSelect options={permissionOptions} values={userPermissionDraft.deny} onChange={(deny) => setUserPermissionDraft({ ...userPermissionDraft, deny, allow: userPermissionDraft.allow.filter((key) => !deny.includes(key)) })} placeholder="Rechte verweigern" searchPlaceholder="Berechtigung suchen …" testId="user-permission-deny" /></div>
                                                </div>
                                                <div className="flex justify-end"><Button type="button" onClick={handleSaveUserPermissions} disabled={savingUserPermissions} data-testid="save-user-permissions">{savingUserPermissions ? 'Speichert …' : 'Rechte speichern'}</Button></div>
                                            </div>
                                        ) : (
                                            <div className="space-y-2 text-sm text-muted-foreground"><p>Du kannst die effektiven Rechte dieses Benutzers ansehen, aber nicht überschreiben.</p><div className="flex flex-wrap gap-1">{(selectedUser.permission_groups || []).map((group) => <span key={group.id} className="rounded bg-muted px-2 py-1 text-xs">{group.name}</span>)}</div></div>
                                        )}
                                    </section>
        
                                    {/* Completion bar */}
                                    <div className="p-4 bg-muted rounded-sm">
                                        <div className="flex items-center justify-between mb-2">
                                            <span className="text-sm font-medium">Fortschritt</span>
                                            <span className="text-sm font-bold text-[var(--brand-primary)]">{completionPercent(selectedUser.completion_pct)}%</span>
                                        </div>
                                        <div className="w-full h-2 bg-background rounded-full overflow-hidden">
                                            <div className="h-full bg-[var(--brand-primary)] rounded-full transition-all" style={{ width: `${completionPercent(selectedUser.completion_pct)}%` }} />
                                        </div>
                                    </div>
        
                                    {/* Profile Data */}
                                    {selectedUser.profile && Object.keys(selectedUser.profile).length > 0 && (
                                        <div>
                                            <h4 className="font-semibold mb-3">Profile</h4>
                                            <div className="grid grid-cols-2 gap-3">
                                                {Object.entries(selectedUser.profile)
                                                    .filter(([key]) => key !== 'profile_image')
                                                    .map(([key, value]) => (
                                                    <div key={key} className="p-2 bg-background rounded-sm">
                                                        <span className="text-xs text-muted-foreground uppercase">{key.replace(/_/g, ' ')}</span>
                                                        {typeof value === 'string' && value.length === 36 && value.includes('-') ? (
                                                            <div className="flex items-center gap-2 mt-1">
                                                                <ImageIcon size={14} className="text-muted-foreground" />
                                                                <a href={filesAPI.getUrl(value)} target="_blank" rel="noopener noreferrer" className="text-sm text-[var(--brand-primary)] hover:underline">
                                                                    View file
                                                                </a>
                                                            </div>
                                                        ) : (
                                                            <p className="text-sm font-medium">{String(value)}</p>
                                                        )}
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    )}
        
                                    {/* Progress with edit ability + step data */}
                                    <div>
                                        <h4 className="font-semibold mb-3">Progress</h4>
                                        <div className="space-y-2">
                                            {selectedUser.progress?.map((p) => {
                                                const step = stepForProgress(steps, p.step_id);
                                                const stepData = progressData(p.data);
                                                const hasData = hasVisibleProgressData(stepData);
                                                return (
                                                    <div key={p.step_id} className="border border-border rounded-sm overflow-hidden">
                                                        <div className="flex items-center justify-between p-3 bg-muted/50">
                                                            <div className="flex items-center gap-2">
                                                                <div className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold ${p.status === 'completed' ? 'bg-green-500 text-white' : p.status === 'in_progress' ? 'bg-[var(--brand-primary)] text-white' : 'bg-muted text-muted-foreground'}`}>
                                                                    {p.status === 'completed' ? <Check size={10} weight="bold" /> : step?.order || '?'}
                                                                </div>
                                                                <span className="text-sm font-medium">{step?.title || 'Unknown Step'}</span>
                                                                {p.configuration_changed && <span className="px-2 py-0.5 rounded bg-amber-100 text-amber-800 text-[10px] font-semibold" data-testid={`historical-config-${p.step_id}`}>Historische Konfiguration · v{p.step_version} → v{p.current_step_version}</span>}
                                                                {p.step_deleted && <span className="px-2 py-0.5 rounded bg-red-100 text-red-700 text-[10px] font-semibold">Schritt archiviert</span>}
                                                            </div>
                                                            <Select value={p.status} onValueChange={(val) => handleUpdateUserProgress(selectedUser.id, p.step_id, val)}>
                                                                <SelectTrigger className={`w-36 h-8 text-xs border-0 ${p.status === 'completed' ? 'bg-green-100 text-green-700' : p.status === 'in_progress' ? 'bg-yellow-100 text-yellow-700' : 'bg-gray-100 text-gray-700'}`} data-testid={`user-progress-${p.step_id}`}>
                                                                    <SelectValue />
                                                                </SelectTrigger>
                                                                <SelectContent>
                                                                    <SelectItem value="pending">Pending</SelectItem>
                                                                    <SelectItem value="in_progress">In Progress</SelectItem>
                                                                    <SelectItem value="completed">Completed</SelectItem>
                                                                </SelectContent>
                                                            </Select>
                                                        </div>
                                                        {hasData && (
                                                            <div className="px-3 py-2 border-t border-border bg-background/50">
                                                                <div className="grid grid-cols-2 gap-x-4 gap-y-2">
                                                                    {Object.entries(stepData).map(([key, value]) => {
                                                                        if (key === 'skipped') return null;
                                                                        const { label, type: fieldType, removed: fieldWasRemoved } = fieldPresentation(step, p, key);
                                                                        if (fieldType === 'multiupload' && Array.isArray(value)) {
                                                                            return (
                                                                                <div key={key} className="col-span-2">
                                                                                    <span className="text-xs text-muted-foreground">{label}{fieldWasRemoved && <span className="ml-2 rounded bg-amber-100 px-1.5 py-0.5 text-[10px] font-semibold text-amber-800">Feld inzwischen gelöscht</span>}</span>
                                                                                    <div className="mt-1 space-y-1">
                                                                                        {value.map((entry, i) => (
                                                                                            <div key={i} className="flex items-center gap-2 text-sm">
                                                                                                {entry.document_type && <span className="px-1.5 py-0.5 text-[10px] font-medium bg-[var(--brand-primary)]/10 text-[var(--brand-primary)] rounded-sm">{entry.document_type}</span>}
                                                                                                {entry.file_id ? <a href={filesAPI.getUrl(entry.file_id)} target="_blank" rel="noopener noreferrer" className="text-[var(--brand-primary)] hover:underline text-xs">{entry.filename || 'Download'}</a> : <span className="text-muted-foreground text-xs">-</span>}
                                                                                            </div>
                                                                                        ))}
                                                                                    </div>
                                                                                </div>
                                                                            );
                                                                        }
                                                                        if (fieldType === 'file' && value) {
                                                                            return (<div key={key}><span className="text-xs text-muted-foreground">{label}{fieldWasRemoved && <span className="ml-2 rounded bg-amber-100 px-1.5 py-0.5 text-[10px] font-semibold text-amber-800">Feld inzwischen gelöscht</span>}</span><div><a href={filesAPI.getUrl(value)} target="_blank" rel="noopener noreferrer" className="text-xs text-[var(--brand-primary)] hover:underline">Download</a></div></div>);
                                                                        }
                                                                        const display = displayFieldValue(value);
                                                                        return (<div key={key}><span className="text-xs text-muted-foreground">{label}{fieldWasRemoved && <span className="ml-2 rounded bg-amber-100 px-1.5 py-0.5 text-[10px] font-semibold text-amber-800">Feld inzwischen gelöscht</span>}</span><p className="text-sm font-medium">{display}</p></div>);
                                                                    })}
                                                                </div>
                                                            </div>
                                                        )}
                                                    </div>
                                                );
                                            })}
                                            {(!selectedUser.progress || selectedUser.progress.length === 0) && (
                                                <p className="text-sm text-muted-foreground p-3">No progress data yet</p>
                                            )}
                                        </div>
                                    </div>
        
                                    {selectedUser.revisions?.length > 0 && (
                                        <div data-testid="answer-revisions">
                                            <h4 className="font-semibold mb-3">Antwortrevisionen</h4>
                                            <div className="space-y-2 max-h-[320px] overflow-y-auto pr-2">
                                                {selectedUser.revisions.map((revision) => (
                                                    <details key={`${revision.step_id}-${revision.revision}`} className="border border-border rounded-sm p-3">
                                                        <summary className="cursor-pointer text-sm font-medium flex flex-wrap items-center gap-2">
                                                            <span>{revision.step_title}</span>
                                                            <span className="text-xs text-muted-foreground">Antwort v{revision.revision} · Step v{revision.step_version}</span>
                                                            {revision.configuration_changed && <span className="px-2 py-0.5 rounded bg-amber-100 text-amber-800 text-[10px] font-semibold">Konfiguration nachträglich geändert</span>}
                                                        </summary>
                                                        <pre className="mt-3 p-2 bg-muted rounded text-xs whitespace-pre-wrap break-all">{JSON.stringify(revision.data || {}, null, 2)}</pre>
                                                        <p className="mt-2 text-[10px] text-muted-foreground">{new Date(revision.created_at).toLocaleString('de-DE')} · {revision.change_type}</p>
                                                    </details>
                                                ))}
                                            </div>
                                        </div>
                                    )}
        
                                    {/* Submissions */}
                                    {selectedUser.submissions?.length > 0 && (
                                        <div>
                                            <h4 className="font-semibold mb-3">Partner Submissions</h4>
                                            <div className="space-y-2">
                                                {selectedUser.submissions.map((sub) => {
                                                    const partnerName = partnerNameForSubmission(partners, sub.partner_id);
                                                    return (
                                                        <div key={sub.id} className="p-3 bg-background rounded-sm">
                                                            <p className="font-medium">{partnerName}</p>
                                                            <p className="text-sm text-muted-foreground">
                                                                Submitted: {new Date(sub.created_at).toLocaleDateString()}
                                                            </p>
                                                        </div>
                                                    );
                                                })}
                                            </div>
                                        </div>
                                    )}
        
                                    {/* History Timeline */}
                                    {selectedUser.history?.length > 0 && (
                                        <div>
                                            <h4 className="font-semibold mb-3">Verlauf</h4>
                                            <div className="relative max-h-[250px] overflow-y-auto pr-2">
                                                <div className="absolute left-3 top-0 bottom-0 w-px bg-border" />
                                                {selectedUser.history.map((h, idx) => {
                                                    const { done: isDone, inProgress: isWip, label: actionLabel } = historyAction(h.action);
                                                    return (
                                                        <div key={idx} className="relative flex items-start gap-3 py-2">
                                                            <div className={`relative z-10 w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 ${isDone ? 'bg-green-500 text-white' : isWip ? 'bg-[var(--brand-primary)] text-white' : 'bg-muted text-muted-foreground'}`}>
                                                                {isDone ? <Check size={10} /> : <ArrowRight size={10} />}
                                                            </div>
                                                            <div className="flex-1 min-w-0">
                                                                <div className="flex items-center gap-2 flex-wrap">
                                                                    <span className="text-sm font-medium">{h.step_title}</span>
                                                                    <span className={`px-1.5 py-0.5 text-[10px] rounded-sm ${isDone ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300' : 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300'}`}>
                                                                        {actionLabel}
                                                                    </span>
                                                                </div>
                                                                <p className="text-[10px] text-muted-foreground">{new Date(h.timestamp).toLocaleString('de-DE')}</p>
                                                            </div>
                                                        </div>
                                                    );
                                                })}
                                            </div>
                                        </div>
                                    )}
                                </div>
                            )}
                        </DialogContent>
                    </Dialog>
    );
}
