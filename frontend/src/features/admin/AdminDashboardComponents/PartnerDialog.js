import { useState, useEffect } from 'react';
import { Button } from '../../../components/ui/button';
import { Input } from '../../../components/ui/input';
import { Label } from '../../../components/ui/label';
import { Textarea } from '../../../components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../../components/ui/select';

import { Checkbox } from '../../../components/ui/checkbox';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../../../components/ui/dialog';
import { asArray } from '../../../lib/valueNormalization';
import { addUniqueTag, allPartnerTags, inheritedStepFee, matchingTags, partnerForm, partnerUserCandidates, removeTag as withoutTag, toggleId, updateStepFee } from '../partnerDialogDomain';





// Stryker disable all: declarative form adapter; partner rules live in partnerDialogDomain.
export function PartnerDialog({ open, onClose, partner, onSave, allUsers, allPartners, surveys, defaultUserFeeCents = 0, t }) {
    const [formData, setFormData] = useState(partnerForm());
    const [tagInput, setTagInput] = useState('');
    const [tagSuggestions, setTagSuggestions] = useState([]);
    const [showTagSuggestions, setShowTagSuggestions] = useState(false);
    const [userSearch, setUserSearch] = useState('');

    // Collect all existing tags from all partners for autocomplete
    const allTags = allPartnerTags(allPartners);

    useEffect(() => {
        setFormData(partnerForm(partner));
        setTagInput('');
        setUserSearch('');
    }, [partner]);

    const handleTagInputChange = (val) => {
        setTagInput(val);
        if (val.trim()) {
            const filtered = matchingTags(allTags, formData.tags, val);
            setTagSuggestions(filtered);
            setShowTagSuggestions(true);
        } else {
            setShowTagSuggestions(false);
        }
    };

    const addTag = (tag) => {
        setFormData(fd => ({ ...fd, tags: addUniqueTag(fd.tags, tag) }));
        setTagInput('');
        setShowTagSuggestions(false);
    };

    const removeTag = (tag) => {
        setFormData(fd => ({ ...fd, tags: withoutTag(fd.tags, tag) }));
    };

    const handleTagKeyDown = (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            if (tagInput.trim()) addTag(tagInput);
        }
    };

    const handleSubmit = (e) => {
        e.preventDefault();
        onSave({ ...formData });
    };

    const toggleUser = (uid) => {
        setFormData(fd => ({
            ...fd,
            linked_user_ids: toggleId(fd.linked_user_ids, uid)
        }));
    };

    const availableUsers = partnerUserCandidates(allUsers, '', formData.linked_user_ids);

    return (
        <Dialog open={open} onOpenChange={onClose}>
            <DialogContent className="max-w-lg max-h-[85vh] overflow-y-auto">
                <DialogHeader>
                    <DialogTitle>{partner ? t('partner_edit') : t('partner_create')}</DialogTitle>
                </DialogHeader>
                <form onSubmit={handleSubmit} className="space-y-4">
                    <div>
                        <Label>Name</Label>
                        <Input value={formData.name} onChange={(e) => setFormData({ ...formData, name: e.target.value })} className="mt-1" required data-testid="partner-name-input" />
                    </div>
                    <div>
                        <Label>Beschreibung</Label>
                        <Textarea value={formData.description} onChange={(e) => setFormData({ ...formData, description: e.target.value })} className="mt-1" required data-testid="partner-description-input" />
                    </div>
                    <div>
                        <Label>Logo URL</Label>
                        <Input value={formData.logo_url} onChange={(e) => setFormData({ ...formData, logo_url: e.target.value })} className="mt-1" placeholder="https://..." data-testid="partner-logo-input" />
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <Label>Website</Label>
                            <Input value={formData.website} onChange={(e) => setFormData({ ...formData, website: e.target.value })} className="mt-1" placeholder="https://..." data-testid="partner-website-input" />
                        </div>
                        <div>
                            <Label>Kontakt-Email</Label>
                            <Input type="email" value={formData.contact_email} onChange={(e) => setFormData({ ...formData, contact_email: e.target.value })} className="mt-1" data-testid="partner-email-input" />
                        </div>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <Label>Kategorie</Label>
                            <Input value={formData.category} onChange={(e) => setFormData({ ...formData, category: e.target.value })} className="mt-1" placeholder="z.B. Antragstellung" data-testid="partner-category-input" />
                        </div>
                    </div>
                    <div>
                        <Label>Tags</Label>
                            <div className="mt-1 flex flex-wrap gap-1.5 p-2 min-h-[38px] border border-border rounded-sm bg-background">
                                {formData.tags.map(tag => (
                                    <span key={tag} className="inline-flex items-center gap-1 px-2 py-0.5 bg-[var(--brand-primary)]/10 text-[var(--brand-primary)] text-xs rounded-sm" data-testid={`tag-badge-${tag}`}>
                                        {tag}
                                        <button type="button" onClick={() => removeTag(tag)} className="hover:text-red-500 font-bold ml-0.5" data-testid={`remove-tag-${tag}`}>&times;</button>
                                    </span>
                                ))}
                                <div className="relative flex-1 min-w-[120px]">
                                    <input
                                        type="text"
                                        value={tagInput}
                                        onChange={(e) => handleTagInputChange(e.target.value)}
                                        onKeyDown={handleTagKeyDown}
                                        onFocus={() => { if (tagInput.trim()) setShowTagSuggestions(true); }}
                                        onBlur={() => setTimeout(() => setShowTagSuggestions(false), 200)}
                                        placeholder={formData.tags.length === 0 ? "Tag eingeben..." : "+"}
                                        className="w-full bg-transparent border-none outline-none text-sm text-foreground placeholder:text-muted-foreground"
                                        data-testid="partner-tags-input"
                                    />
                                    {showTagSuggestions && tagSuggestions.length > 0 && (
                                        <div className="absolute left-0 top-full mt-1 w-56 bg-card border border-border rounded-sm shadow-lg z-50 max-h-40 overflow-y-auto" data-testid="tag-suggestions">
                                            {tagSuggestions.map(s => (
                                                <button key={s} type="button" onMouseDown={() => addTag(s)} className="w-full text-left px-3 py-2 text-sm hover:bg-muted text-foreground">{s}</button>
                                            ))}
                                        </div>
                                    )}
                                    {showTagSuggestions && tagInput.trim() && !allTags.includes(tagInput.trim()) && !formData.tags.includes(tagInput.trim()) && (
                                        <div className="absolute left-0 top-full mt-1 w-56 bg-card border border-border rounded-sm shadow-lg z-50">
                                            {tagSuggestions.map(s => (
                                                <button key={s} type="button" onMouseDown={() => addTag(s)} className="w-full text-left px-3 py-2 text-sm hover:bg-muted text-foreground">{s}</button>
                                            ))}
                                            <button type="button" onMouseDown={() => addTag(tagInput)} className="w-full text-left px-3 py-2 text-sm hover:bg-muted text-[var(--brand-primary)] font-medium border-t border-border" data-testid="create-new-tag">
                                                + Neuen Tag "{tagInput.trim()}" erstellen
                                            </button>
                                        </div>
                                    )}
                                </div>
                            </div>
                    </div>
                    <div>
                        <Label>{t('partner_linked_users')}</Label>
                        <p className="text-xs text-muted-foreground mb-2">{t('partner_linked_users_desc')}</p>
                        <Input placeholder={t('partner_search_users')} value={userSearch} onChange={e => setUserSearch(e.target.value)} className="mb-2 h-8 text-sm" data-testid="partner-user-search" />
                        <div className="max-h-40 overflow-y-auto border border-border rounded-sm">
                            {availableUsers.length === 0 ? (
                                <p className="p-3 text-xs text-muted-foreground">{t('partner_no_users')}</p>
                            ) : (() => {
                                const sorted = partnerUserCandidates(availableUsers, userSearch, formData.linked_user_ids);
                                return sorted.length === 0 ? (
                                    <p className="p-3 text-xs text-muted-foreground">{t('partner_no_results')}</p>
                                ) : sorted.map(u => (
                                    <label key={u.id} className="flex items-center gap-2 px-3 py-2 hover:bg-muted cursor-pointer border-b border-border last:border-0" data-testid={`partner-link-user-${u.id}`}>
                                        <input type="checkbox" checked={formData.linked_user_ids.includes(u.id)} onChange={() => toggleUser(u.id)} className="rounded border-border" />
                                        <span className="text-sm font-medium">{u.name}</span>
                                        <span className="text-xs text-muted-foreground">{u.email}</span>
                                    </label>
                                ));
                            })()}
                        </div>
                    </div>
                    <div>
                        <Label>Survey-Zuordnung</Label>
                        <p className="text-xs text-muted-foreground mb-2">Mindestens eine Zuordnung aktiviert den Partner.</p>
                        <div className="border border-border rounded-sm divide-y divide-border">{asArray(surveys).map(survey => <label key={survey.id} className="flex items-center gap-2 p-3 cursor-pointer"><Checkbox checked={formData.survey_ids.includes(survey.id)} onCheckedChange={() => setFormData(fd => ({...fd, survey_ids: toggleId(fd.survey_ids, survey.id)}))}/><span>{survey.name}</span></label>)}</div>
                    </div>
                    {partner && <div data-testid="partner-step-prices">
                        <Label>Leistungen und Step-Preise</Label>
                        <p className="text-xs text-muted-foreground mb-2">Ein Partnerpreis überschreibt Step-Preis und globalen Standard. Leer übernimmt den jeweils nächstniedrigeren Wert.</p>
                        <div className="space-y-2">{asArray(partner.service_steps).map(serviceStep => {
                            const inherited = inheritedStepFee(serviceStep, defaultUserFeeCents);
                            const ownValue = formData.step_user_fee_cents[serviceStep.id];
                            return <div key={serviceStep.id} className="rounded border border-border p-3"><div className="flex justify-between gap-3"><div><p className="text-sm font-medium">Step {serviceStep.order}: {serviceStep.title}</p><p className="text-xs text-muted-foreground">Tag: {serviceStep.filter_tag || '–'} · geerbt: {(inherited/100).toLocaleString('de-DE',{style:'currency',currency:'EUR'})}</p></div><Input className="w-32" type="number" min="0" value={ownValue ?? ''} placeholder={String(inherited)} onChange={event => setFormData(current => ({ ...current, step_user_fee_cents: updateStepFee(current.step_user_fee_cents, serviceStep.id, event.target.value) }))} data-testid={`partner-step-price-${serviceStep.id}`} /></div></div>;
                        })}{!asArray(partner.service_steps).length && <p className="rounded border border-dashed border-border p-3 text-sm text-muted-foreground">Über Tags und Survey-Zuordnung ist diesem Partner noch kein Partner-Step zugeordnet.</p>}</div>
                    </div>}
                    <div className="border-t border-border pt-4" data-testid="partner-stripe-fields"><Label>Stripe-Verknüpfung</Label><p className="mb-3 text-xs text-muted-foreground">Manuelle Pflege für bestehende Stripe-Konten. IDs müssen zum selben Stripe-Kunden gehören.</p><div className="space-y-3"><div><Label>Customer-ID</Label><Input value={formData.stripe_customer_id} onChange={event => setFormData({...formData,stripe_customer_id:event.target.value.trim()})} placeholder="cus_…" /></div><div><Label>Subscription-ID</Label><Input value={formData.stripe_subscription_id} onChange={event => setFormData({...formData,stripe_subscription_id:event.target.value.trim()})} placeholder="sub_…" /></div><div><Label>Abrechnungsstatus</Label><Select value={formData.billing_status || 'pending'} onValueChange={value => setFormData({...formData,billing_status:value})}><SelectTrigger><SelectValue/></SelectTrigger><SelectContent><SelectItem value="pending">pending</SelectItem><SelectItem value="trialing">trialing</SelectItem><SelectItem value="active">active</SelectItem><SelectItem value="paid">paid</SelectItem><SelectItem value="past_due">past_due</SelectItem><SelectItem value="unpaid">unpaid</SelectItem><SelectItem value="canceled">canceled</SelectItem></SelectContent></Select></div></div></div>
                    <div className="flex justify-end gap-3">
                        <Button type="button" variant="outline" onClick={onClose}>{t('cancel')}</Button>
                        <Button type="submit" className="bg-[var(--brand-primary)] hover:bg-[var(--brand-primary-hover)] text-white" data-testid="save-partner-btn">
                            {partner ? t('save') : t('partner_create')}
                        </Button>
                    </div>
                </form>
            </DialogContent>
        </Dialog>
    );
}
