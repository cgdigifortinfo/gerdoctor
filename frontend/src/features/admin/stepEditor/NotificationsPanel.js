
import { Input } from '../../../components/ui/input';
import { Label } from '../../../components/ui/label';
import { Textarea } from '../../../components/ui/textarea';

import { Switch } from '../../../components/ui/switch';



import { HelpLabel } from '../../../components/ui/help-tooltip';


export function NotificationsPanel({ formData, setFormData }) {
    return <div className="space-y-4">
                            <div className="space-y-3">
                                {[['email_on_enter', 'Bei Schritt-Eintritt'], ['email_on_edit', 'Bei Bearbeitung'], ['email_on_leave', 'Bei Schritt-Abschluss']].map(([key, label]) => (
                                    <div key={key} className="flex items-center justify-between"><HelpLabel className="text-sm" help={{ email_on_enter: 'Sendet beim ersten Öffnen beziehungsweise Starten dieses Steps.', email_on_edit: 'Sendet bei späteren Änderungen gespeicherter Step-Daten, sofern Nutzer dies erlaubt haben.', email_on_leave: 'Sendet unmittelbar beim erfolgreichen Abschluss dieses Steps.' }[key]}>{label}</HelpLabel><Switch checked={formData[key]} onCheckedChange={(val) => setFormData({ ...formData, [key]: val })} /></div>
                                ))}
                            </div>
                            
                            <div className="p-3 bg-muted rounded-sm">
                                <p className="text-xs text-muted-foreground mb-1">Verfügbare Variablen für E-Mail-Vorlagen:</p>
                                <div className="flex flex-wrap gap-1">
                                    {['{{user_name}}', '{{user_email}}', '{{step_title}}', '{{step_order}}', '{{step_description}}'].map(v => (
                                        <code key={v} className="px-1.5 py-0.5 text-[10px] bg-card border border-border rounded">{v}</code>
                                    ))}
                                </div>
                            </div>

                            {formData.email_on_enter && (
                                <div className="p-3 border border-border rounded-sm space-y-2">
                                    <p className="text-xs font-semibold text-muted-foreground uppercase">E-Mail bei Eintritt</p>
                                    <div><Label className="text-xs">Betreff</Label><Input value={formData.email_subject_enter || ''} onChange={(e) => setFormData({ ...formData, email_subject_enter: e.target.value })} className="h-8 text-sm mt-1" placeholder="Schritt gestartet: {{step_title}}" data-testid="email-subject-enter" /></div>
                                    <div><Label className="text-xs">Inhalt (HTML)</Label><Textarea value={formData.email_body_enter || ''} onChange={(e) => setFormData({ ...formData, email_body_enter: e.target.value })} className="text-sm mt-1 min-h-[60px]" placeholder="<p>Hallo {{user_name}}, Sie haben {{step_title}} begonnen.</p>" data-testid="email-body-enter" /></div>
                                </div>
                            )}

                            {formData.email_on_edit && (
                                <div className="p-3 border border-border rounded-sm space-y-2">
                                    <p className="text-xs font-semibold text-muted-foreground uppercase">E-Mail bei Bearbeitung</p>
                                    <div><Label className="text-xs">Betreff</Label><Input value={formData.email_subject_edit || ''} onChange={(e) => setFormData({ ...formData, email_subject_edit: e.target.value })} className="h-8 text-sm mt-1" placeholder="Schritt aktualisiert: {{step_title}}" data-testid="email-subject-edit" /></div>
                                    <div><Label className="text-xs">Inhalt (HTML)</Label><Textarea value={formData.email_body_edit || ''} onChange={(e) => setFormData({ ...formData, email_body_edit: e.target.value })} className="text-sm mt-1 min-h-[60px]" placeholder="<p>Hallo {{user_name}}, {{step_title}} wurde aktualisiert.</p>" data-testid="email-body-edit" /></div>
                                </div>
                            )}

                            {formData.email_on_leave && (
                                <div className="p-3 border border-border rounded-sm space-y-2">
                                    <p className="text-xs font-semibold text-muted-foreground uppercase">E-Mail bei Abschluss</p>
                                    <div><Label className="text-xs">Betreff</Label><Input value={formData.email_subject_leave || ''} onChange={(e) => setFormData({ ...formData, email_subject_leave: e.target.value })} className="h-8 text-sm mt-1" placeholder="Schritt abgeschlossen: {{step_title}}" data-testid="email-subject-leave" /></div>
                                    <div><Label className="text-xs">Inhalt (HTML)</Label><Textarea value={formData.email_body_leave || ''} onChange={(e) => setFormData({ ...formData, email_body_leave: e.target.value })} className="text-sm mt-1 min-h-[60px]" placeholder="<p>Hallo {{user_name}}, herzlichen Glückwunsch! {{step_title}} ist abgeschlossen.</p>" data-testid="email-body-leave" /></div>
                                </div>
                            )}
                        </div>;
}
