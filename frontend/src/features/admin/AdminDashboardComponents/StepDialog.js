import { useState, useEffect,  useMemo } from 'react';
import { Button } from '../../../components/ui/button';
import { Input } from '../../../components/ui/input';
import { Label } from '../../../components/ui/label';
import { Textarea } from '../../../components/ui/textarea';



import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../../../components/ui/dialog';

import {  SearchableSelect } from '../../../components/admin/EntityPickers';
import SurveyFormBuilder from '../../../components/admin/SurveyFormBuilder';
import { HelpLabel, HelpTooltip } from '../../../components/ui/help-tooltip';
import { BasicPanel } from '../stepEditor/BasicPanel';
import { RequirementsPanel } from '../stepEditor/RequirementsPanel';
import { MappingsPanel } from '../stepEditor/MappingsPanel';
import { ConditionsPanel } from '../stepEditor/ConditionsPanel';
import { NotificationsPanel } from '../stepEditor/NotificationsPanel';
import { TranslationsPanel } from '../stepEditor/TranslationsPanel';
import { withFallbackOption } from '../stepEditorDomain';
import { addConditionChildState, addConditionGroupState, addConditionPresetState, addConditionState, addMappingState, buildConditionOperatorOptions, buildConditionValueOptions, buildCurrentFieldOptions, buildDocumentTypeOptions, buildPartnerTagOptions, buildSourceFieldOptions, buildStepOptions, buildSurveyOptions, changeConditionFieldState, changeConditionGroupTypeState, changeConditionOperatorState, changeConditionSourceState, changeMappingSourceState, conditionPresets, createStepFormData, defaultConditionLeaf, findStepByOrder as findReferenceStepByOrder, findStepField, partnerFeeFromInput, removeConditionChildState, removeConditionState, removeMappingState, selectStepSurvey, shouldNotifySurveyChange, sortReferenceSteps, stepDialogTitle, updateConditionChildState, updateConditionState, updateMappingState, updateStepFields, updateStepTranslation, validStepSection } from '../stepDialogDomain';

// Stryker disable all: declarative React adapter; state transitions and decisions live in stepDialogDomain.
// Step Dialog Component
// Stryker disable next-line ArrayDeclaration: non-empty default-array mutants are indistinguishable after option normalization.
export function StepDialog({ open, onClose, step, onSave, existingSteps, surveys = [], partners = [], activeSurveyId = '', onSurveyChange, t }) {
    const [formData, setFormData] = useState(() => createStepFormData(step, existingSteps.length, activeSurveyId));
    const [translations, setTranslations] = useState({});
    const [activeSection, setActiveSection] = useState('basic');

    useEffect(() => {
        setFormData(createStepFormData(step, existingSteps.length, activeSurveyId));
        setTranslations(step?.translations || {});
    // Stryker disable next-line ArrayDeclaration: React synchronization metadata is covered by prop-rerender tests.
    }, [step, existingSteps.length, activeSurveyId]);

    const handleSubmit = (e) => { e.preventDefault(); onSave({ ...formData, translations }); };

    const handleStepSurveyChange = (surveyId) => {
        setFormData(selectStepSurvey(formData, surveyId));
        if (shouldNotifySurveyChange(surveyId, activeSurveyId)) {
            onSurveyChange?.(surveyId);
        }
    };

    const setTrans = (lang, field, value) => {
        setTranslations(prev => updateStepTranslation(prev, lang, field, value));
    };
    const handleFieldsChange = (fields) => {
        setFormData((current) => updateStepFields(current, fields));
    };

    const sortedReferenceSteps = useMemo(
        () => sortReferenceSteps(existingSteps),
        // Stryker disable next-line ArrayDeclaration: React memo metadata is covered by reference-step rerenders.
        [existingSteps],
    );
    // Stryker disable ArrayDeclaration: React memo dependency metadata is covered by panel prop integration tests.
    const stepOptions = useMemo(() => buildStepOptions(sortedReferenceSteps, step?.id), [sortedReferenceSteps, step?.id]);
    const surveyOptions = useMemo(() => buildSurveyOptions(surveys), [surveys]);
    const partnerTagOptions = useMemo(() => buildPartnerTagOptions(partners), [partners]);
    const currentFieldOptions = useMemo(() => buildCurrentFieldOptions(formData.fields), [formData.fields]);
    const documentTypeOptions = useMemo(() => buildDocumentTypeOptions(formData.required_uploads, sortedReferenceSteps, formData.fields), [formData.fields, formData.required_uploads, sortedReferenceSteps]);
    // Stryker restore ArrayDeclaration

    const findStepByOrder = (order) => findReferenceStepByOrder(sortedReferenceSteps, order);
    const findField = findStepField;
    const sourceFieldOptions = (sourceOrder, currentValue) => buildSourceFieldOptions(sortedReferenceSteps, sourceOrder, currentValue);
    const conditionValueOptions = (condition) => buildConditionValueOptions(condition, sortedReferenceSteps, documentTypeOptions);
    const conditionOperatorOptions = (condition) => buildConditionOperatorOptions(condition, sortedReferenceSteps);

    // Mapping helpers
    const addMapping = () => setFormData(current => addMappingState(current, sortedReferenceSteps, step?.id));
    const removeMapping = (i) => setFormData(current => removeMappingState(current, i));
    const updateMapping = (i, patch) => setFormData(current => updateMappingState(current, i, patch));
    const changeMappingSource = (i, value) => {
        const source = findStepByOrder(value);
        setFormData(current => changeMappingSourceState(current, i, value, source));
    };

    // Condition helpers
    const makeConditionLeaf = () => defaultConditionLeaf(sortedReferenceSteps, formData.order, step?.id);
    const addCondition = () => setFormData(current => addConditionState(current, makeConditionLeaf()));
    const addConditionGroup = (groupKey) => setFormData(current => addConditionGroupState(current, groupKey, makeConditionLeaf()));
    const removeCondition = (i) => setFormData(current => removeConditionState(current, i));
    const updateCondition = (i, patch) => setFormData(current => updateConditionState(current, i, patch));
    const changeConditionSource = (i, value) => setFormData(current => changeConditionSourceState(current, i, value));
    const changeConditionField = (i, fieldName) => {
        const condition = formData.conditions[i];
        const selectedField = findField(findStepByOrder(condition.source_step_order), fieldName);
        setFormData(current => changeConditionFieldState(current, i, fieldName, selectedField));
    };
    const changeConditionOperator = (i, operator) => setFormData(current => changeConditionOperatorState(current, i, operator));
    const updateConditionChild = (conditionIndex, groupKey, childIndex, patch) => setFormData(current => updateConditionChildState(current, conditionIndex, groupKey, childIndex, patch));
    const addConditionChild = (conditionIndex, groupKey) => setFormData(current => addConditionChildState(current, conditionIndex, groupKey, makeConditionLeaf()));
    const removeConditionChild = (conditionIndex, groupKey, childIndex) => setFormData(current => removeConditionChildState(current, conditionIndex, groupKey, childIndex));
    const changeConditionGroupType = (conditionIndex, oldKey, newKey) => setFormData(current => changeConditionGroupTypeState(current, conditionIndex, oldKey, newKey));

    const sectionMeta = [
        { id: 'basic', label: t('step_basic'), description: 'Identität, Typ und Dauer', help: 'Legt Survey, sichtbare Texte, Position und Step-Typ fest. Der Step-Typ bestimmt die grundlegende Darstellung und Verarbeitung.' },
        ...((['partner_selection', 'partner_multiselection', 'milestone', 'display'].includes(formData.step_type))
            ? [{ id: 'type', label: t('step_type_settings'), description: 'Verhalten dieses Schritttyps', help: 'Enthält nur Einstellungen des aktuell gewählten Step-Typs, etwa Partnerfilter oder Statusmeldungen eines Meilensteins.' }]
            : []),
        ...(['form', 'decision'].includes(formData.step_type) ? [{ id: 'fields', label: t('step_fields'), description: 'Formular visuell aufbauen', count: formData.fields.length, help: 'Fügt Eingaben, Auswahlen, Uploads und Inhaltselemente hinzu. Reihenfolge und Breite bestimmen die spätere Nutzeransicht.' }] : []),
        { id: 'requirements', label: t('step_requirements'), description: 'Pflichtangaben und Dokumente', count: formData.required_fields.length + formData.required_uploads.length, help: 'Definiert serverseitig geprüfte Voraussetzungen für den Abschluss: ausgefüllte Felder und vorhandene Dokumenttypen.' },
        { id: 'mappings', label: t('step_mappings'), description: 'Daten automatisch übernehmen', count: formData.field_mappings.length, help: 'Kopiert einen Wert aus einem früheren Step in ein Feld dieses Steps und vermeidet dadurch Doppeleingaben.' },
        { id: 'conditions', label: t('step_conditions'), description: 'Sichtbarkeit und Zugriff steuern', count: formData.conditions.length, help: 'Wertet Status oder Feldwerte anderer Steps aus. Treffer können den Step verbergen, blockieren, automatisch abschließen oder umleiten.' },
        { id: 'notifications', label: t('step_notifications'), description: 'E-Mail-Auslöser und Inhalte', help: 'Versendet E-Mails beim Eintritt, bei Bearbeitung oder Abschluss. Ohne individuellen Text greift die globale Standardvorlage.' },
        { id: 'translations', label: 'Englisch', description: 'Übersetzte Texte pflegen', help: 'Hinterlegt englische Varianten sichtbarer Texte. Leere Werte fallen auf den deutschen Originaltext zurück.' },
    ];
    const currentSection = sectionMeta.find((section) => section.id === activeSection) || sectionMeta[0];
    const { previousStep, uploadPresetStep, uploadPresetField, choicePresetStep, choicePresetField } = conditionPresets(sortedReferenceSteps, formData.order);

    const addConditionPreset = (preset) => setFormData(current => addConditionPresetState(current, preset));

    useEffect(() => {
        const validSection = validStepSection(activeSection, formData.step_type);
        // Stryker disable next-line ConditionalExpression: forcing the guard true only repeats the identical React state.
        if (validSection !== activeSection) setActiveSection(validSection);
    // Stryker disable next-line ArrayDeclaration: section correction is verified through type changes.
    }, [activeSection, formData.step_type]);

    return (
        <Dialog open={open} onOpenChange={onClose}>
            <DialogContent
                className="flex h-[94vh] max-h-[980px] max-w-[96vw] flex-col gap-0 overflow-hidden p-0 xl:max-w-[1500px]"
                data-testid="step-editor-dialog"
                onEscapeKeyDown={(event) => {
                    if (document.querySelector('[data-entity-picker-open="true"], [role="tooltip"]')) event.preventDefault();
                }}
            >
                <DialogHeader className="border-b border-border px-6 py-5 pr-16">
                    <DialogTitle className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
                        <span>{step ? t('step_edit') : t('step_create')}</span>
                        <span className="text-[var(--brand-primary)]" data-testid="step-editor-title">
                            {stepDialogTitle(formData, Boolean(step))}
                        </span>
                    </DialogTitle>
                    <div className="flex flex-wrap items-center gap-2 pt-1 text-xs text-muted-foreground">
                        <span>Position {formData.order}</span>
                        <span aria-hidden="true">·</span>
                        <span>{formData.step_type}</span>
                    </div>
                </DialogHeader>

                <form onSubmit={handleSubmit} className="flex min-h-0 flex-1 flex-col">
                    <div className="grid min-h-0 flex-1 md:grid-cols-[240px_minmax(0,1fr)]">
                        <aside className="border-b border-border bg-muted/35 p-3 md:border-b-0 md:border-r" aria-label="Editor-Bereiche">
                            <nav className="grid grid-cols-2 gap-1 md:grid-cols-1">
                                {sectionMeta.map((section) => (
                                    <button
                                        key={section.id}
                                        type="button"
                                        onClick={() => setActiveSection(section.id)}
                                        className={`rounded-lg border px-3 py-2.5 text-left transition-colors ${activeSection === section.id ? 'border-[var(--brand-primary)] bg-card text-foreground shadow-sm' : 'border-transparent text-muted-foreground hover:bg-card hover:text-foreground'}`}
                                        data-testid={`step-section-${section.id}`}
                                    >
                                        <span className="flex items-center justify-between gap-2 text-sm font-semibold">
                                            <span className="inline-flex items-center gap-1.5">{section.label}<HelpTooltip content={section.help} side="right" testId={`step-section-help-${section.id}`} /></span>
                                            {section.count > 0 && <span className="rounded-full bg-[var(--brand-primary)]/10 px-2 py-0.5 text-[11px] text-[var(--brand-primary)]">{section.count}</span>}
                                        </span>
                                        <span className="mt-0.5 hidden text-[11px] leading-4 text-muted-foreground md:block">{section.description}</span>
                                    </button>
                                ))}
                            </nav>
                        </aside>
                        <section className="min-h-0 overflow-y-auto px-5 py-5 md:px-7" data-testid={`step-section-panel-${activeSection}`}>
                            <div className="mb-5">
                                <h3 className="inline-flex items-center gap-2 text-lg font-semibold text-foreground">{currentSection.label}<HelpTooltip content={currentSection.help} testId={`step-panel-help-${currentSection.id}`} /></h3>
                                <p className="mt-1 text-sm text-muted-foreground">{currentSection.description}</p>
                            </div>
                    {/* BASIC */}
                    {activeSection === 'basic' && (
                        <BasicPanel surveyOptions={surveyOptions} formData={formData} activeSurveyId={activeSurveyId} handleStepSurveyChange={handleStepSurveyChange} t={t} setFormData={setFormData} />
                    )}

                    {/* TYPE SETTINGS */}
                    {activeSection === 'type' && (
                        <div className="space-y-4">
                            {(formData.step_type === 'partner_selection' || formData.step_type === 'partner_multiselection') && (
                                <div className="space-y-4">
                                  <div>
                                    <Label><HelpLabel help="Zeigt nur aktive Partner mit exakt diesem Tag. Bei Mehrfachauswahl können mehrere passende Partner gewählt werden.">{t('step_filter_tag')}</HelpLabel></Label>
                                    <p className="mb-2 mt-1 text-xs text-muted-foreground">Nur Partner mit diesem Tag werden angeboten. Neue Tags können direkt angelegt werden.</p>
                                    <SearchableSelect
                                        options={withFallbackOption(partnerTagOptions, formData.filter_tag)}
                                        value={formData.filter_tag}
                                        onChange={(value) => setFormData({ ...formData, filter_tag: value })}
                                        placeholder="Partner-Tag auswählen"
                                        searchPlaceholder="Partner-Tags durchsuchen …"
                                        testId="step-filter-tag"
                                        allowCustom
                                    />
                                  </div>
                                  <div>
                                    <Label>Nutzergebühr für diesen Step in Cent</Label>
                                    <Input type="number" min="0" value={formData.partner_user_fee_cents ?? ''} onChange={(event) => setFormData({...formData, partner_user_fee_cents: partnerFeeFromInput(event.target.value)})} placeholder="Globalen Standard verwenden" data-testid="step-user-fee-cents" />
                                    <p className="mt-1 text-xs text-muted-foreground">Leer übernimmt den globalen Standard. Auch 0 Cent ist eine explizite Überschreibung.</p>
                                  </div>
                                </div>
                            )}
                            {(formData.step_type === 'display' || formData.step_type === 'milestone') && (
                                <>
                                    <div><Label><HelpLabel help="Text, solange der Meilenstein noch offen oder die Anzeige noch nicht erledigt ist.">{t('step_pending_msg')}</HelpLabel></Label><Textarea value={formData.pending_message} onChange={(e) => setFormData({ ...formData, pending_message: e.target.value })} className="mt-1" /></div>
                                    <div><Label><HelpLabel help="Text, nachdem der Meilenstein oder Anzeigeschritt abgeschlossen wurde.">{t('step_complete_msg')}</HelpLabel></Label><Textarea value={formData.complete_message} onChange={(e) => setFormData({ ...formData, complete_message: e.target.value })} className="mt-1" /></div>
                                </>
                            )}
                            {formData.step_type === 'display' && <div><Label>{t('step_action_label')}</Label><Input value={formData.action_label} onChange={(e) => setFormData({ ...formData, action_label: e.target.value })} className="mt-1" /></div>}
                        </div>
                    )}

                    {/* FIELDS */}
                    {activeSection === 'fields' && ['form', 'decision'].includes(formData.step_type) && (
                        <SurveyFormBuilder fields={formData.fields} onChange={handleFieldsChange} />
                    )}

                    {/* REQUIREMENTS */}
                    {activeSection === 'requirements' && (
                        <RequirementsPanel formData={formData} currentFieldOptions={currentFieldOptions} setFormData={setFormData} documentTypeOptions={documentTypeOptions} />
                    )}

                    {/* MAPPINGS */}
                    {activeSection === 'mappings' && (
                        <MappingsPanel addMapping={addMapping} formData={formData} removeMapping={removeMapping} stepOptions={stepOptions} changeMappingSource={changeMappingSource} sourceFieldOptions={sourceFieldOptions} updateMapping={updateMapping} currentFieldOptions={currentFieldOptions} />
                    )}

                    {/* CONDITIONS */}
                    {activeSection === 'conditions' && (
                        <ConditionsPanel addCondition={addCondition} addConditionGroup={addConditionGroup} previousStep={previousStep} uploadPresetStep={uploadPresetStep} uploadPresetField={uploadPresetField} choicePresetStep={choicePresetStep} choicePresetField={choicePresetField} sortedReferenceSteps={sortedReferenceSteps} formData={formData} addConditionPreset={addConditionPreset} conditionValueOptions={conditionValueOptions} removeCondition={removeCondition} changeConditionGroupType={changeConditionGroupType} addConditionChild={addConditionChild} findStepByOrder={findStepByOrder} updateConditionChild={updateConditionChild} findField={findField} stepOptions={stepOptions} sourceFieldOptions={sourceFieldOptions} conditionOperatorOptions={conditionOperatorOptions} removeConditionChild={removeConditionChild} updateCondition={updateCondition} changeConditionSource={changeConditionSource} changeConditionField={changeConditionField} changeConditionOperator={changeConditionOperator} />
                    )}

                    {/* NOTIFICATIONS + EMAIL TEMPLATES */}
                    {activeSection === 'notifications' && (
                        <NotificationsPanel formData={formData} setFormData={setFormData} />
                    )}

                    {activeSection === 'translations' && (
                        <TranslationsPanel translations={translations} setTrans={setTrans} formData={formData} />
                    )}


                        </section>
                    </div>

                    <div className="flex items-center justify-between gap-3 border-t border-border bg-card px-6 py-4">
                        <p className="hidden text-xs text-muted-foreground sm:block">Änderungen werden erst mit „Speichern“ übernommen.</p>
                        <div className="ml-auto flex gap-3">
                        <Button type="button" variant="outline" onClick={onClose}>{t('cancel')}</Button>
                        <Button type="submit" className="bg-[var(--brand-primary)] hover:bg-[var(--brand-primary-hover)] text-white" data-testid="save-step-btn">{step ? t('save') : t('create_user_submit')}</Button>
                        </div>
                    </div>
                </form>
            </DialogContent>
        </Dialog>
    );
}
