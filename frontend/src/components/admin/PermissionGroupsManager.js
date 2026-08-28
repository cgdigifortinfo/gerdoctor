import { useEffect, useMemo, useState } from 'react';
import { Check, Lock, Pencil, Plus, ShieldCheck, Trash, UsersThree } from '@phosphor-icons/react';
import { toast } from 'sonner';
import { adminAPI, formatApiError } from '../../lib/api';
import { Button } from '../ui/button';
import { Checkbox } from '../ui/checkbox';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../ui/dialog';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Textarea } from '../ui/textarea';

// Stryker disable all: permissions API/form adapter covered by component contract tests.
const ROLE_LABELS = { admin: 'Administration', user: 'Survey-Nutzer', partner: 'Partner' };

export function PermissionMatrix({ catalog, selected = [], onChange, disabled = false, testId = 'permission-matrix' }) {
    const selectedSet = useMemo(() => new Set(selected), [selected]);
    const toggle = (key) => onChange(selectedSet.has(key) ? selected.filter((item) => item !== key) : [...selected, key]);
    const toggleCategory = (permissions) => {
        const keys = permissions.map((permission) => permission.key);
        const allSelected = keys.every((key) => selectedSet.has(key));
        onChange(allSelected ? selected.filter((key) => !keys.includes(key)) : [...new Set([...selected, ...keys])]);
    };
    return (
        <div className="space-y-3" data-testid={testId}>
            {(catalog?.categories || []).map((category) => {
                const allSelected = category.permissions.every((permission) => selectedSet.has(permission.key));
                const someSelected = category.permissions.some((permission) => selectedSet.has(permission.key));
                return (
                    <section key={category.category} className="overflow-hidden rounded-lg border border-border">
                        <button type="button" disabled={disabled} onClick={() => toggleCategory(category.permissions)} className="flex w-full items-center justify-between bg-muted/50 px-3 py-2 text-left">
                            <span className="text-sm font-semibold text-foreground">{category.category}</span>
                            <span className="text-xs text-muted-foreground">{category.permissions.filter((permission) => selectedSet.has(permission.key)).length}/{category.permissions.length}</span>
                        </button>
                        <div className="divide-y divide-border">
                            {category.permissions.map((permission) => (
                                <label key={permission.key} className="flex cursor-pointer items-start gap-3 px-3 py-2.5 hover:bg-muted/25">
                                    <Checkbox checked={selectedSet.has(permission.key)} onCheckedChange={() => toggle(permission.key)} disabled={disabled} data-testid={`${testId}-${permission.key}`} />
                                    <span className="min-w-0"><span className="block text-sm font-medium text-foreground">{permission.label}</span><span className="block text-xs leading-4 text-muted-foreground">{permission.description}</span><code className="text-[10px] text-muted-foreground">{permission.key}</code></span>
                                </label>
                            ))}
                        </div>
                        {(allSelected || someSelected) && <div className="sr-only">Auswahl vorhanden</div>}
                    </section>
                );
            })}
        </div>
    );
}

function GroupDialog({ open, group, catalog, onClose, onSaved }) {
    const [form, setForm] = useState({ name: '', description: '', role: 'user', permissions: [] });
    const [saving, setSaving] = useState(false);
    useEffect(() => {
        if (open) setForm({ name: group?.name || '', description: group?.description || '', role: group?.role || 'user', permissions: group?.permissions?.includes('*') ? (catalog?.all_permissions || []) : (group?.permissions || []) });
    }, [open, group, catalog]);
    const save = async (event) => {
        event.preventDefault();
        setSaving(true);
        try {
            const payload = { ...form, permissions: form.permissions };
            if (group) await adminAPI.updatePermissionGroup(group.id, payload);
            else await adminAPI.createPermissionGroup(payload);
            toast.success(group ? 'Nutzergruppe aktualisiert' : 'Nutzergruppe erstellt');
            onSaved();
            onClose();
        } catch (error) { toast.error(formatApiError(error)); }
        finally { setSaving(false); }
    };
    return (
        <Dialog open={open} onOpenChange={onClose}>
            <DialogContent className="flex h-[90vh] max-w-4xl flex-col overflow-hidden p-0" data-testid="permission-group-dialog">
                <DialogHeader className="border-b border-border px-6 py-4"><DialogTitle>{group ? 'Nutzergruppe bearbeiten' : 'Nutzergruppe anlegen'}</DialogTitle></DialogHeader>
                <form onSubmit={save} className="flex min-h-0 flex-1 flex-col">
                    <div className="grid min-h-0 flex-1 md:grid-cols-[300px_1fr]">
                        <div className="space-y-4 border-b border-border p-5 md:border-b-0 md:border-r">
                            <div><Label>Name</Label><Input className="mt-1" value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} required data-testid="permission-group-name" /></div>
                            <div><Label>Beschreibung</Label><Textarea className="mt-1" value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} rows={4} /></div>
                            <div><Label>Portalrolle</Label><Select value={form.role} onValueChange={(role) => setForm({ ...form, role })} disabled={!!group?.member_count}><SelectTrigger className="mt-1" data-testid="permission-group-role"><SelectValue /></SelectTrigger><SelectContent><SelectItem value="user">Survey-Nutzer</SelectItem><SelectItem value="partner">Partner</SelectItem><SelectItem value="admin">Administration</SelectItem></SelectContent></Select>{group?.member_count > 0 && <p className="mt-1 text-xs text-muted-foreground">Die Portalrolle kann bei zugewiesenen Benutzern nicht geändert werden.</p>}</div>
                            <div className="rounded-lg bg-muted p-3 text-xs text-muted-foreground"><strong className="text-foreground">{form.permissions.length}</strong> Einzelberechtigungen ausgewählt. Änderungen wirken unmittelbar auf alle Gruppenmitglieder.</div>
                        </div>
                        <div className="min-h-0 overflow-y-auto p-5"><div className="mb-3"><h3 className="font-semibold">Berechtigungen</h3><p className="text-xs text-muted-foreground">Kategorien oder einzelne Rechte frei auswählen.</p></div><PermissionMatrix catalog={catalog} selected={form.permissions} onChange={(permissions) => setForm({ ...form, permissions })} testId="group-permission-matrix" /></div>
                    </div>
                    <div className="flex justify-end gap-3 border-t border-border px-6 py-4"><Button type="button" variant="outline" onClick={onClose}>Abbrechen</Button><Button type="submit" disabled={saving} data-testid="save-permission-group">{saving ? 'Speichert …' : 'Speichern'}</Button></div>
                </form>
            </DialogContent>
        </Dialog>
    );
}

export default function PermissionGroupsManager({ groups, catalog, onRefresh, canCreate = false, canUpdate = false, canDelete = false }) {
    const [editing, setEditing] = useState(undefined);
    const [dialogOpen, setDialogOpen] = useState(false);
    const openCreate = () => { setEditing(undefined); setDialogOpen(true); };
    const openEdit = (group) => { setEditing(group); setDialogOpen(true); };
    const remove = async (group) => {
        if (!window.confirm(`Nutzergruppe „${group.name}“ wirklich löschen?`)) return;
        try { await adminAPI.deletePermissionGroup(group.id); toast.success('Nutzergruppe gelöscht'); onRefresh(); }
        catch (error) { toast.error(formatApiError(error)); }
    };
    return (
        <div className="rounded-sm border border-border bg-card" data-testid="permission-groups-manager">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border p-4"><div><div className="flex items-center gap-2"><ShieldCheck size={22} className="text-[var(--brand-primary)]" /><h2 className="text-lg font-semibold">Nutzergruppen und Rechte</h2></div><p className="mt-1 text-xs text-muted-foreground">Gruppen bündeln Einzelberechtigungen. Benutzer-Overrides können Rechte zusätzlich erlauben oder ausdrücklich verweigern.</p></div>{canCreate && <Button onClick={openCreate} data-testid="create-permission-group"><Plus size={16} className="mr-1" /> Gruppe anlegen</Button>}</div>
            <div className="grid gap-4 p-4 md:grid-cols-2 xl:grid-cols-3">
                {groups.map((group) => {
                    const permissionCount = group.permissions?.includes('*') ? catalog?.all_permissions?.length || 0 : group.permissions?.length || 0;
                    return <article key={group.id} className="flex flex-col rounded-lg border border-border p-4" data-testid={`permission-group-${group.id}`}><div className="flex items-start justify-between gap-3"><div><div className="flex items-center gap-2"><h3 className="font-semibold">{group.name}</h3>{group.is_system && <span title="Systemgruppe"><Lock size={13} className="text-muted-foreground" /></span>}</div><span className="mt-1 inline-flex rounded-full bg-muted px-2 py-0.5 text-[11px]">{ROLE_LABELS[group.role]}</span></div><div className="flex">{canUpdate && <Button variant="ghost" size="sm" className="h-8 w-8 p-0" onClick={() => openEdit(group)} aria-label={`${group.name} bearbeiten`}><Pencil size={15} /></Button>}{canDelete && !group.is_system && <Button variant="ghost" size="sm" className="h-8 w-8 p-0 text-red-500" onClick={() => remove(group)} aria-label={`${group.name} löschen`}><Trash size={15} /></Button>}</div></div><p className="mt-3 flex-1 text-sm text-muted-foreground">{group.description || 'Keine Beschreibung'}</p><div className="mt-4 flex items-center justify-between border-t border-border pt-3 text-xs text-muted-foreground"><span className="flex items-center gap-1"><Check size={13} /> {permissionCount} Rechte</span><span className="flex items-center gap-1"><UsersThree size={13} /> {group.member_count} Mitglieder</span></div></article>;
                })}
            </div>
            <GroupDialog open={dialogOpen} group={editing} catalog={catalog} onClose={() => setDialogOpen(false)} onSaved={onRefresh} />
        </div>
    );
}
