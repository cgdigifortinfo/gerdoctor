

import { Button } from '../../../components/ui/button';







import { TabsContent } from '../../../components/ui/tabs';
import { Plus, Pencil, Trash,       LinkBreak, UserPlus } from '@phosphor-icons/react';




import { PaginationControls } from '../../../components/PaginationControls';
import { SegmentedControl } from '../../../components/collections';
import { StatusBadge, TagBadge } from '../../../components/ui/entity-badges';
import { partnerServiceLabel, pendingPartnerCount, registrationBadge } from '../adminTabViewModels';



// Stryker disable all: declarative adapter; presentation derivations live in adminTabViewModels.
export function PartnersTab(props) {
    const { users, partners, setEditingPartner, setShowPartnerDialog, setShowLinkDialog, partnerView, setPartnerView, partnersPagination, handleDeletePartner, handleUnlinkUser } = props;
    return (
<TabsContent value="partners">
                        <div className="bg-card border border-border rounded-sm">
                            <div className="p-4 border-b border-border flex flex-wrap gap-3 justify-between items-center">
                                <div><h2 className="text-lg font-semibold text-foreground">Partner Management</h2><SegmentedControl className="mt-2" value={partnerView} onChange={setPartnerView} options={[{ value: 'active', label: 'Aktive Partner' }, { value: 'pending', label: `Neue Partner (${pendingPartnerCount(partners)})`, testId: 'pending-partners-view' }]} /></div>
                                <Button onClick={() => { setEditingPartner(null); setShowPartnerDialog(true); }} className="bg-[var(--brand-primary)] hover:bg-[var(--brand-primary-hover)] text-white" data-testid="add-partner-btn">
                                    <Plus size={18} className="mr-2" /> Add Partner
                                </Button>
                            </div>
                            <div className="overflow-x-auto">
                                <table className="w-full">
                                    <thead className="bg-background">
                                        <tr>
                                            <th className="px-4 py-3 text-left text-xs font-bold uppercase tracking-wider text-muted-foreground">Partner</th>
                                            <th className="px-4 py-3 text-left text-xs font-bold uppercase tracking-wider text-muted-foreground">Anmeldungen</th>
                                            <th className="px-4 py-3 text-left text-xs font-bold uppercase tracking-wider text-muted-foreground">Category</th>
                                            <th className="px-4 py-3 text-left text-xs font-bold uppercase tracking-wider text-muted-foreground">Tags</th>
                                            <th className="px-4 py-3 text-left text-xs font-bold uppercase tracking-wider text-muted-foreground">Linked User</th>
                                            <th className="px-4 py-3 text-left text-xs font-bold uppercase tracking-wider text-muted-foreground">Status</th>
                                            <th className="px-4 py-3 text-left text-xs font-bold uppercase tracking-wider text-muted-foreground">Actions</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {partnersPagination.paginatedItems.map((partner) => {
                                            const linkedUser = users.find(u => u.id === partner.user_id);
                                            return (
                                                <tr key={partner.id} className="border-t border-border table-row-hover">
                                                    <td className="px-4 py-3">
                                                        <div className="flex items-center gap-3">
                                                            {partner.logo_url && <img src={partner.logo_url} alt="" className="w-10 h-10 rounded-sm object-cover" />}
                                                            <div>
                                                                <p className="font-medium text-foreground">{partner.name}</p>
                                                                <p className="text-xs text-muted-foreground">{partner.contact_email}</p>
                                                                <p className="mt-1 text-xs text-muted-foreground">Leistungen: {partnerServiceLabel(partner)}</p>
                                                                {partner.registration_source === 'self_service' && <span className="inline-flex mt-1 px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 text-[10px] font-bold">NEU REGISTRIERT</span>}
                                                            </div>
                                                        </div>
                                                    </td>
                                                    <td className="px-4 py-3" data-testid={`partner-pending-registrations-${partner.id}`}>
                                                        {(partner.pending_registrations || 0) > 0 ? (
                                                            <span
                                                                className="inline-flex items-center justify-center min-w-[28px] px-2 py-0.5 text-xs font-bold bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300 rounded-full"
                                                                title={registrationBadge(partner.pending_registrations).title}
                                                            >
                                                                {partner.pending_registrations}
                                                            </span>
                                                        ) : (
                                                            <span className="text-xs text-muted-foreground">0</span>
                                                        )}
                                                    </td>
                                                    <td className="px-4 py-3 text-sm text-muted-foreground">{partner.category || '-'}</td>
                                                    <td className="px-4 py-3">
                                                        <div className="flex flex-wrap gap-1">
                                                            {(partner.tags || []).map(tag => <TagBadge key={tag}>{tag}</TagBadge>)}
                                                            {(!partner.tags || partner.tags.length === 0) && <span className="text-xs text-muted-foreground">-</span>}
                                                        </div>
                                                    </td>
                                                    <td className="px-4 py-3">
                                                        {linkedUser ? (
                                                            <div className="flex items-center gap-2">
                                                                <span className="text-sm text-foreground">{linkedUser.name}</span>
                                                                <Button variant="ghost" size="sm" onClick={() => handleUnlinkUser(partner.id)} className="text-red-500 hover:text-red-700 h-6 px-1" title="Unlink user" data-testid={`unlink-partner-${partner.id}`}>
                                                                    <LinkBreak size={14} />
                                                                </Button>
                                                            </div>
                                                        ) : (
                                                            <Button variant="ghost" size="sm" onClick={() => setShowLinkDialog(partner)} className="text-[var(--brand-primary)] h-7 text-xs" data-testid={`link-partner-${partner.id}`}>
                                                                <UserPlus size={14} className="mr-1" /> Link User
                                                            </Button>
                                                        )}
                                                    </td>
                                                    <td className="px-4 py-3">
                                                        <StatusBadge tone={partner.registration_status === 'pending' ? 'warning' : partner.is_active ? 'success' : 'neutral'}>
                                                            {partner.registration_status === 'pending' ? 'Wartet auf Survey' : 'Aktiv'}
                                                        </StatusBadge>
                                                    </td>
                                                    <td className="px-4 py-3">
                                                        <div className="flex gap-2">
                                                            <Button variant="ghost" size="sm" onClick={() => { setEditingPartner(partner); setShowPartnerDialog(true); }} data-testid={`edit-partner-${partner.id}`}>
                                                                <Pencil size={16} />
                                                            </Button>
                                                            <Button variant="ghost" size="sm" onClick={() => handleDeletePartner(partner.id)} className="text-red-500 hover:text-red-700" data-testid={`delete-partner-${partner.id}`}>
                                                                <Trash size={16} />
                                                            </Button>
                                                        </div>
                                                    </td>
                                                </tr>
                                            );
                                        })}
                                    </tbody>
                                </table>
                            </div>
                            <PaginationControls pagination={partnersPagination} id="admin-partners" />
                        </div>
                    </TabsContent>
    );
}
