

import { Button } from '../../../components/ui/button';
import { Input } from '../../../components/ui/input';
import { Label } from '../../../components/ui/label';


import { Switch } from '../../../components/ui/switch';


import { TabsContent } from '../../../components/ui/tabs';







import { ElementToggle } from '../AdminDashboardComponents/AdminPrimitives';

// Stryker disable all: declarative React adapter over tested billing/settings commands and state.
export function SettingsTab(props) {
    const { t, adminBilling, stripeAudit, stripeAuditLoading, siteSettings, setSiteSettings, settingsSaving, handleSaveSettings, auditStripeConnections, repairStripeConnection, repairAllStripeConnections } = props;
    return (
<TabsContent value="settings">
                        <div className="space-y-6">
                            <div className="bg-card border border-border rounded-sm p-6">
                                <h2 className="text-lg font-semibold text-foreground mb-6">{t('admin_site_settings')}</h2>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                    <div className="space-y-2">
                                        <Label>Site Title</Label>
                                        <Input value={siteSettings.site_title || ''} onChange={e => setSiteSettings(s => ({ ...s, site_title: e.target.value }))} placeholder="IHCA" data-testid="settings-site-title" />
                                    </div>
                                    <div className="space-y-2">
                                        <Label>Meta Description</Label>
                                        <Input value={siteSettings.meta_description || ''} onChange={e => setSiteSettings(s => ({ ...s, meta_description: e.target.value }))} placeholder="Praktizieren in Deutschland" data-testid="settings-meta-desc" />
                                    </div>
                                </div>
                            </div>

                            <div className="bg-card border border-border rounded-sm p-6">
                                <h2 className="text-lg font-semibold text-foreground mb-2">{t('admin_logo_config')}</h2>
                                <p className="text-sm text-muted-foreground mb-6">The logo is displayed as a wordmark: the bold part followed by the light part.</p>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                    <div className="space-y-2">
                                        <Label>Bold Part (e.g. "GER")</Label>
                                        <Input value={siteSettings.logo_bold_part || ''} onChange={e => setSiteSettings(s => ({ ...s, logo_bold_part: e.target.value }))} placeholder="GER" data-testid="settings-logo-bold" />
                                    </div>
                                    <div className="space-y-2">
                                        <Label>Light Part (e.g. "doctor")</Label>
                                        <Input value={siteSettings.logo_light_part || ''} onChange={e => setSiteSettings(s => ({ ...s, logo_light_part: e.target.value }))} placeholder="doctor" data-testid="settings-logo-light" />
                                    </div>
                                </div>
                                <div className="mt-4 p-4 bg-muted rounded-sm">
                                    <Label className="text-xs text-muted-foreground mb-2 block">Preview</Label>
                                    <div className="flex items-baseline">
                                        <span className="font-black text-2xl text-foreground" style={{ fontFamily: "'Varela Round', sans-serif", letterSpacing: 0 }}>{siteSettings.logo_bold_part || 'GER'}</span>
                                        <span className="font-light text-2xl text-foreground" style={{ fontFamily: "'Varela Round', sans-serif", letterSpacing: 0 }}>{siteSettings.logo_light_part || 'doctor'}</span>
                                    </div>
                                </div>
                            </div>

                            <div className="bg-card border border-border rounded-sm p-6">
                                <h2 className="text-lg font-semibold text-foreground mb-6">{t('admin_general')}</h2>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                    <div className="space-y-2">
                                        <Label>Contact Email</Label>
                                        <Input value={siteSettings.contact_email || ''} onChange={e => setSiteSettings(s => ({ ...s, contact_email: e.target.value }))} placeholder="info@chrizz1001.de" data-testid="settings-contact-email" />
                                    </div>
                                    <div className="space-y-2">
                                        <Label>Primary Color</Label>
                                        <div className="flex items-center gap-3">
                                            <input type="color" value={siteSettings.primary_color || 'var(--brand-primary)'} onChange={e => setSiteSettings(s => ({ ...s, primary_color: e.target.value }))} className="w-10 h-10 rounded cursor-pointer border border-border" data-testid="settings-primary-color" />
                                            <Input value={siteSettings.primary_color || ''} onChange={e => setSiteSettings(s => ({ ...s, primary_color: e.target.value }))} placeholder="var(--brand-primary)" className="flex-1" />
                                        </div>
                                    </div>
                                    <div className="space-y-2 md:col-span-2">
                                        <Label>Footer Text</Label>
                                        <Input value={siteSettings.footer_text || ''} onChange={e => setSiteSettings(s => ({ ...s, footer_text: e.target.value }))} placeholder="Optional footer text" data-testid="settings-footer-text" />
                                    </div>
                                </div>
                            </div>

                            {/* ============ UI-ELEMENTE (Feature Toggles) ============ */}
                            <div className="bg-card border border-border rounded-lg p-6" data-testid="settings-elements-section">
                                <h3 className="text-lg font-semibold text-foreground mb-1">UI-Elemente</h3>
                                <p className="text-sm text-muted-foreground mb-4">
                                    Ein-/Ausschalten globaler UI-Komponenten im User-Dashboard. Spätere
                                    Version: Diese Toggles werden Teil eines umfassenden Rechtesystems
                                    (Benutzergruppen + individuelle Rechte).
                                </p>
                                <div className="space-y-3">
                                    <ElementToggle
                                        id="ui_show_journey_indicator"
                                        label="Journey-Progress-Indikator"
                                        description={'Zeigt den Banner „Schritt X von Y" mit Pfad-Vorschau (Decision) bzw. nächsten Schritten über dem aktiven Step-Card.'}
                                        checked={siteSettings.ui_show_journey_indicator !== false}
                                        onChange={(val) => setSiteSettings(s => ({ ...s, ui_show_journey_indicator: val }))}
                                    />
                                    <ElementToggle
                                        id="ui_show_eta_header"
                                        label="Voraussichtliches Abschluss-Datum"
                                        description="Zeigt das errechnete ETA-Datum in der Kopfzeile neben dem Logo."
                                        checked={siteSettings.ui_show_eta_header !== false}
                                        onChange={(val) => setSiteSettings(s => ({ ...s, ui_show_eta_header: val }))}
                                    />
                                    <ElementToggle
                                        id="ui_show_progress_percentage"
                                        label="Fortschritts-Prozent-Badge"
                                        description={'Zeigt den Prozent-Badge (z.B. „17 %") in der Kopfzeile.'}
                                        checked={siteSettings.ui_show_progress_percentage !== false}
                                        onChange={(val) => setSiteSettings(s => ({ ...s, ui_show_progress_percentage: val }))}
                                    />
                                </div>
                            </div>

                            <div className="bg-card border border-border rounded-lg p-6" data-testid="settings-stripe-section">
                                <h3 className="text-lg font-semibold">Stripe Checkout & Billing</h3>
                                <p className="text-sm text-muted-foreground mt-1 mb-5">Partner bezahlen Ihren Business-Account als Stripe-Kunden. Sandbox nutzt ausschließlich Testschlüssel; Secrets werden nie öffentlich ausgeliefert.</p>
                                <div className="flex items-center justify-between border border-border rounded-md p-4 mb-5"><div><Label>Sandbox-Modus</Label><p className="text-xs text-muted-foreground">Testzahlungen ohne echten Geldfluss</p></div><Switch checked={siteSettings.stripe_sandbox_mode !== false} onCheckedChange={v => setSiteSettings(s => ({...s, stripe_sandbox_mode:v}))}/></div>
                                <div className="grid md:grid-cols-2 gap-4">
                                    {[
                                        ['stripe_test_publishable_key','Test Publishable Key','text'], ['stripe_test_secret_key','Test Secret Key','password'],
                                        ['stripe_test_webhook_secret','Test Webhook Secret','password'], ['stripe_live_publishable_key','Live Publishable Key','text'],
                                        ['stripe_live_secret_key','Live Secret Key','password'], ['stripe_live_webhook_secret','Live Webhook Secret','password']
                                    ].map(([key,label,type]) => <div key={key}><Label>{label}</Label><Input type={type} value={siteSettings[key] || ''} onChange={e => setSiteSettings(s => ({...s,[key]:e.target.value}))} autoComplete="off"/></div>)}
                                </div>
                                <div className="grid md:grid-cols-2 gap-4 mt-5 pt-5 border-t border-border">
                                    <div><Label>Partner Price ID</Label><Input placeholder="price_…" value={siteSettings.stripe_partner_price_id || ''} onChange={e => setSiteSettings(s => ({...s,stripe_partner_price_id:e.target.value}))}/><p className="text-xs text-muted-foreground mt-1">Preis im Stripe-Produktkatalog; für Abos muss er wiederkehrend sein.</p></div>
                                    <div><Label>Zahlungsmodell</Label><Input value="Monatliches Abonnement" disabled/><p className="text-xs text-muted-foreground mt-1">Die Grundgebühr wird ausschließlich als wiederkehrendes Stripe-Abonnement angelegt.</p></div>
                                    <div><Label>Globaler Standardpreis je Nutzer in Cent</Label><Input type="number" min="0" value={siteSettings.stripe_partner_user_fee_cents ?? 0} onChange={e => setSiteSettings(s => ({...s,stripe_partner_user_fee_cents:Number(e.target.value)||0}))}/><p className="text-xs text-muted-foreground mt-1">Default beim ersten Partner-Dokument je Nutzer und Leistungs-Step. Step- und Partnerpreise können ihn überschreiben.</p></div>
                                    <div><Label>Währung der Nutzergebühr</Label><Input maxLength={3} value={siteSettings.stripe_partner_user_fee_currency || 'eur'} onChange={e => setSiteSettings(s => ({...s,stripe_partner_user_fee_currency:e.target.value.toLowerCase()}))}/></div>
                                    <label className="flex items-center gap-3"><Switch checked={siteSettings.stripe_automatic_tax === true} onCheckedChange={v=>setSiteSettings(s=>({...s,stripe_automatic_tax:v}))}/><span><span className="block text-sm font-medium">Stripe Tax automatisch</span><span className="block text-xs text-muted-foreground">Erfordert aktiviertes Stripe Tax.</span></span></label>
                                    <label className="flex items-center gap-3"><Switch checked={siteSettings.stripe_allow_promotion_codes === true} onCheckedChange={v=>setSiteSettings(s=>({...s,stripe_allow_promotion_codes:v}))}/><span className="text-sm font-medium">Aktionscodes erlauben</span></label>
                                </div>
                                <div className="mt-6 border-t border-border pt-5" data-testid="stripe-connection-audit">
                                    <div className="flex flex-wrap items-center justify-between gap-3"><div><h4 className="font-semibold">Stripe-Verbindungen prüfen</h4><p className="text-sm text-muted-foreground">Findet fehlende oder widersprüchliche Customer-, Subscription- und Status-Verknüpfungen.</p></div><div className="flex gap-2"><Button type="button" variant="outline" onClick={auditStripeConnections} disabled={stripeAuditLoading}>{stripeAuditLoading ? 'Prüft…' : 'Verbindungen prüfen'}</Button>{stripeAudit?.repairable > 0 && <Button type="button" onClick={repairAllStripeConnections} disabled={stripeAuditLoading}>Alle reparierbaren Einträge reparieren</Button>}</div></div>
                                    {stripeAudit && <div className="mt-4"><p className="text-sm mb-3">{stripeAudit.defective} auffällig · {stripeAudit.repairable} automatisch reparierbar</p><div className="space-y-3">{(stripeAudit.entries || []).map(entry => <div key={entry.partner_id} className="rounded border border-border p-4" data-testid={`stripe-audit-${entry.partner_id}`}><div className="flex flex-wrap justify-between gap-3"><div><p className="font-medium">{entry.partner_name}</p><p className="text-xs text-muted-foreground">{entry.emails.join(', ') || 'keine E-Mail'} · Customer: {entry.current_customer_id || 'fehlt'} · Abo: {entry.current_subscription_id || 'fehlt'}</p><ul className="mt-2 list-disc pl-5 text-sm text-amber-700">{entry.issues.map(issue => <li key={issue}>{issue}</li>)}</ul>{entry.repairable && <p className="mt-2 text-xs text-muted-foreground">Vorschlag: {entry.proposed_customer_id} / {entry.proposed_subscription_id} / {entry.proposed_billing_status}</p>}</div>{entry.repairable ? <Button type="button" size="sm" onClick={() => repairStripeConnection(entry.partner_id)}>Eintrag reparieren</Button> : <span className="h-fit rounded bg-amber-100 px-2 py-1 text-xs text-amber-800">Manuelle Prüfung nötig</span>}</div></div>)}{!stripeAudit.entries?.length && <p className="rounded border border-green-200 bg-green-50 p-3 text-sm text-green-800">Keine fehlerhaften Stripe-Verbindungen gefunden.</p>}</div></div>}
                                </div>
                                <div className="mt-6 border-t border-border pt-5" data-testid="admin-billing-summary">
                                    <h4 className="font-semibold">Abrechnungsübersicht</h4>
                                    <div className="mt-3 grid grid-cols-2 md:grid-cols-4 gap-3">
                                        <div className="rounded border border-border p-3"><p className="text-xs text-muted-foreground">Offene Nutzer</p><p className="text-xl font-bold">{adminBilling.totals?.pending_users || 0}</p></div>
                                        <div className="rounded border border-border p-3"><p className="text-xs text-muted-foreground">Offener Betrag</p><p className="text-xl font-bold">{((adminBilling.totals?.pending_amount || 0)/100).toLocaleString('de-DE',{style:'currency',currency:(siteSettings.stripe_partner_user_fee_currency||'EUR').toUpperCase()})}</p></div>
                                        <div className="rounded border border-border p-3"><p className="text-xs text-muted-foreground">Abgerechnete Nutzer</p><p className="text-xl font-bold">{adminBilling.totals?.billed_users || 0}</p></div>
                                        <div className="rounded border border-border p-3"><p className="text-xs text-muted-foreground">Abgerechneter Betrag</p><p className="text-xl font-bold">{((adminBilling.totals?.billed_amount || 0)/100).toLocaleString('de-DE',{style:'currency',currency:(siteSettings.stripe_partner_user_fee_currency||'EUR').toUpperCase()})}</p></div>
                                    </div>
                                    <div className="mt-4 space-y-3">{(adminBilling.partners || []).map(item => <details key={item.partner_id} className="rounded border border-border"><summary className="cursor-pointer p-3 font-medium">{item.partner_name} · {item.usage.pending_users} offen · {item.invoices.length} Rechnungen</summary><div className="border-t border-border p-3 space-y-2">{item.invoices.map(invoice => <div key={invoice.id} className="flex justify-between gap-3 text-sm"><span>{invoice.number || invoice.id} · {invoice.status} · {((invoice.amount_due||0)/100).toLocaleString('de-DE',{style:'currency',currency:(invoice.currency||'eur').toUpperCase()})}</span><span className="flex gap-2">{invoice.hosted_invoice_url && <a className="text-[var(--brand-primary)] underline" href={invoice.hosted_invoice_url} target="_blank" rel="noreferrer">Ansehen</a>}{invoice.invoice_pdf && <a className="text-[var(--brand-primary)] underline" href={invoice.invoice_pdf} target="_blank" rel="noreferrer" download>PDF</a>}</span></div>)}{!item.invoices.length && <p className="text-sm text-muted-foreground">Noch keine Rechnungen.</p>}</div></details>)}</div>
                                </div>
                            </div>

                            <div className="flex justify-end">
                                <Button onClick={handleSaveSettings} disabled={settingsSaving} className="bg-[var(--brand-primary)] hover:bg-[var(--brand-primary-hover)] text-white" data-testid="save-settings-btn">
                                    {settingsSaving ? t('admin_saving') : t('admin_save_settings')}
                                </Button>
                            </div>
                        </div>
                    </TabsContent>
    );
}
