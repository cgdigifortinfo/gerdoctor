
import { Input } from '../../../components/ui/input';
import { Label } from '../../../components/ui/label';
import { Textarea } from '../../../components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../../components/ui/select';
import { Switch } from '../../../components/ui/switch';


import {  SearchableSelect } from '../../../components/admin/EntityPickers';
import { HelpLabel } from '../../../components/ui/help-tooltip';


export function BasicPanel({ surveyOptions, formData, activeSurveyId, handleStepSurveyChange, t, setFormData }) {
    return <div className="space-y-4">
                            <div>
                                <Label><HelpLabel help="Ordnet den Step einem Survey zu. Reihenfolge, Progress und Conditions gelten nur innerhalb dieses Surveys.">Survey</HelpLabel></Label>
                                <div className="mt-1">
                                    <SearchableSelect
                                        options={surveyOptions}
                                        value={formData.survey_id || activeSurveyId}
                                        onChange={handleStepSurveyChange}
                                        placeholder="Survey wählen"
                                        searchPlaceholder="Survey nach Name oder URL suchen …"
                                        testId="step-survey-select"
                                    />
                                </div>
                            </div>
                            <div><Label><HelpLabel help="Sichtbarer Name in Journey, Navigation, Adminansicht und E-Mails.">{t('step_title')}</HelpLabel></Label><Input value={formData.title} onChange={(e) => setFormData({ ...formData, title: e.target.value })} className="mt-1" required data-testid="step-title-input" /></div>
                            <div><Label><HelpLabel help="Erklärt Nutzern Ziel und Inhalt des Steps. Die Beschreibung kann auch in Benachrichtigungen verwendet werden.">{t('step_description')}</HelpLabel></Label><Textarea value={formData.description} onChange={(e) => setFormData({ ...formData, description: e.target.value })} className="mt-1" required data-testid="step-description-input" /></div>
                            <div className="grid grid-cols-2 gap-4">
                                <div><Label><HelpLabel help="Position innerhalb des aktiven Surveys. Conditions referenzieren Steps über diese Nummer.">{t('step_order')}</HelpLabel></Label><Input type="number" min="1" value={formData.order} onChange={(e) => setFormData({ ...formData, order: parseInt(e.target.value) })} className="mt-1" required /></div>
                                <div><Label><HelpLabel help="Formular sammelt Daten; Entscheidung zeigt Auswahlkarten; Partner-Typen vermitteln Partner; Meilenstein bildet Status ab; Anzeige zeigt Information.">{t('step_type')}</HelpLabel></Label><Select value={formData.step_type} onValueChange={(val) => setFormData({ ...formData, step_type: val })}><SelectTrigger className="mt-1" data-testid="step-type-select"><SelectValue /></SelectTrigger><SelectContent><SelectItem value="form">{t('step_type_form')}</SelectItem><SelectItem value="decision">Entscheidung (2 Buttons)</SelectItem><SelectItem value="partner_selection">{t('step_type_partner')}</SelectItem><SelectItem value="partner_multiselection">{t('step_type_partner_multi')}</SelectItem><SelectItem value="milestone">{t('step_type_milestone')}</SelectItem><SelectItem value="display">{t('step_type_display')}</SelectItem></SelectContent></Select></div>
                            </div>
                            <div className="flex items-center justify-between"><Label><HelpLabel help="Inaktive Steps werden nicht ausgeliefert und zählen nicht zum Fortschritt.">{t('step_active')}</HelpLabel></Label><Switch checked={formData.is_active} onCheckedChange={(val) => setFormData({ ...formData, is_active: val })} /></div>
                            <div className="flex items-center justify-between"><Label><HelpLabel help="Erlaubt Nutzern, den Step ohne reguläre Eingaben als übersprungen abzuschließen.">{t('step_skippable')}</HelpLabel></Label><Switch checked={formData.skippable} onCheckedChange={(val) => setFormData({ ...formData, skippable: val })} /></div>
                            {formData.skippable && <div><Label>{t('step_skip_label')}</Label><Input value={formData.skip_label} onChange={(e) => setFormData({ ...formData, skip_label: e.target.value })} className="mt-1" placeholder="Vorerst überspringen" /></div>}
                            <div className="border-t border-border pt-4 mt-2">
                                <Label className="text-sm font-semibold"><HelpLabel help="Schätzwert für die ETA-Berechnung. Freischaltungen werden ausschließlich über Conditions gesteuert.">{t('step_duration')}</HelpLabel></Label>
                                <p className="text-xs text-muted-foreground mb-2">{t('step_duration_desc')}</p>
                                <div className="grid grid-cols-2 gap-4">
                                    <div><Label>{t('step_duration_value')}</Label><Input type="number" min="0" value={formData.duration_value} onChange={(e) => setFormData({ ...formData, duration_value: parseInt(e.target.value) || 0 })} className="mt-1" data-testid="step-duration-value" /></div>
                                    <div><Label>{t('step_duration_unit')}</Label><Select value={formData.duration_unit} onValueChange={(val) => setFormData({ ...formData, duration_unit: val })}><SelectTrigger className="mt-1" data-testid="step-duration-unit"><SelectValue /></SelectTrigger><SelectContent><SelectItem value="days">{t('step_days')}</SelectItem><SelectItem value="weeks">{t('step_weeks')}</SelectItem><SelectItem value="months">{t('step_months')}</SelectItem><SelectItem value="years">{t('step_years')}</SelectItem></SelectContent></Select></div>
                                </div>
                            </div>
                        </div>;
}
