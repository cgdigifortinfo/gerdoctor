import { Button } from '../../../components/ui/button';
import { Input } from '../../../components/ui/input';
import { Label } from '../../../components/ui/label';
import { Textarea } from '../../../components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../../components/ui/select';


import { Plus, Trash } from '@phosphor-icons/react';
import { SearchableMultiSelect, SearchableSelect } from '../../../components/admin/EntityPickers';
import { HelpLabel } from '../../../components/ui/help-tooltip';
import { CONDITION_ACTION_OPTIONS, CONDITION_OPERATOR_OPTIONS, conditionActionUpdate, conditionDisplayValue, conditionFieldUpdate, conditionGroupKey, conditionMultiValue, conditionOperatorUpdate, conditionScalarValue, conditionSourceUpdate, conditionValueMode, optionValue, withFallbackOption } from '../stepEditorDomain';

export function ConditionsPanel({ addCondition, addConditionGroup, previousStep, uploadPresetStep, uploadPresetField, choicePresetStep, choicePresetField, sortedReferenceSteps, formData, addConditionPreset, conditionValueOptions, removeCondition, changeConditionGroupType, addConditionChild, findStepByOrder, updateConditionChild, findField, stepOptions, sourceFieldOptions, conditionOperatorOptions, removeConditionChild, updateCondition, changeConditionSource, changeConditionField, changeConditionOperator }) {
    return <div className="space-y-4">
                            <div className="flex items-start justify-between gap-4">
                                <div>
                                    <Label><HelpLabel help="Jede Regel liest einen anderen Step. Mehrere Regeln werden unabhängig ausgewertet; jede zutreffende Aktion kann auf diesen Step wirken.">Regeln für diesen Schritt</HelpLabel></Label>
                                    <p className="mt-1 text-xs text-muted-foreground">Eine Regel liest den Status oder ein Feld eines anderen Schritts und führt bei einem Treffer die gewählte Aktion aus.</p>
                                </div>
                                <div className="flex flex-wrap gap-2">
                                    <Button type="button" variant="outline" size="sm" onClick={addCondition} data-testid="add-condition"><Plus size={14} className="mr-1" /> Einzelregel</Button>
                                    <Button type="button" variant="outline" size="sm" onClick={() => addConditionGroup('all_of')} data-testid="add-condition-all"><Plus size={14} className="mr-1" /> UND-Gruppe</Button>
                                    <Button type="button" variant="outline" size="sm" onClick={() => addConditionGroup('any_of')} data-testid="add-condition-any"><Plus size={14} className="mr-1" /> ODER-Gruppe</Button>
                                </div>
                            </div>

                            {/* Presets */}
                            <div className="rounded-lg border border-[var(--brand-primary)]/20 bg-[var(--brand-primary)]/5 p-4">
                                <p className="mb-2 text-xs font-semibold text-[var(--brand-primary)]">Schnellstart mit sinnvoll vorbelegten Regeln</p>
                                <div className="flex flex-wrap gap-2">
                                    {[
                                        previousStep && { label: 'Vorherigen Schritt voraussetzen', preset: { source_step_order: previousStep.order, field: 'status', operator: 'status_not', value: 'completed', action: 'block', message: `Bitte schließen Sie zuerst „${previousStep.title}“ ab.` } },
                                        uploadPresetStep && uploadPresetField && { label: 'Fehlendes Dokument blockiert', preset: { source_step_order: uploadPresetStep.order, field: uploadPresetField.name, operator: 'missing_upload', value: optionValue(uploadPresetField.options?.[0]) || '', action: 'block', message: 'Bitte laden Sie zuerst das erforderliche Dokument hoch.' } },
                                        choicePresetStep && choicePresetField && { label: 'Mehrere Antworten zulassen', preset: { source_step_order: choicePresetStep.order, field: choicePresetField.name, operator: 'one_of', value: (choicePresetField.options || []).slice(0, 2).map(optionValue), action: 'allow_next', message: '' } },
                                        previousStep && { label: 'Nach Abschluss weiterleiten', preset: { source_step_order: previousStep.order, field: 'status', operator: 'status_is', value: 'completed', action: 'redirect', target_step_order: sortedReferenceSteps.find((candidate) => candidate.order > formData.order)?.order || null, message: '' } },
                                    ].filter(Boolean).map((p, i) => (
                                        <button key={p.label} type="button" onClick={() => addConditionPreset(p.preset)}
                                            className="rounded-md border border-border bg-card px-2.5 py-1.5 text-xs transition-colors hover:border-[var(--brand-primary)] hover:bg-muted" data-testid={`condition-preset-${i}`}>
                                            {p.label}
                                        </button>
                                    ))}
                                </div>
                            </div>

                            {formData.conditions.map((c, i) => {
                                const valueOptions = conditionValueOptions(c);
                                const valueMode = conditionValueMode(c.operator, valueOptions.length > 0);
                                const actionLabel = CONDITION_ACTION_OPTIONS.find((option) => option.value === c.action)?.label || c.action;
                                const compoundKey = conditionGroupKey(c);
                                if (compoundKey) {
                                    const children = c[compoundKey];
                                    return (
                                        <div key={i} className="rounded-lg border border-border bg-card p-4 shadow-sm" data-testid={`condition-card-${i}`}>
                                            <div className="mb-4 flex items-start justify-between gap-3">
                                                <div>
                                                    <p className="text-sm font-semibold">Regel {i + 1} · {compoundKey === 'all_of' ? 'UND-Gruppe' : 'ODER-Gruppe'}</p>
                                                    <p className="mt-0.5 text-xs text-muted-foreground">
                                                        {compoundKey === 'all_of' ? 'Alle Teilbedingungen müssen zutreffen.' : 'Mindestens eine Teilbedingung muss zutreffen.'} Bei Treffer: {actionLabel}
                                                    </p>
                                                </div>
                                                <Button type="button" variant="ghost" size="sm" onClick={() => removeCondition(i)} className="h-8 text-red-500"><Trash size={14} className="mr-1" /> Entfernen</Button>
                                            </div>
                                            <div className="mb-4 flex flex-wrap items-end gap-3 rounded-md bg-muted/30 p-3">
                                                <div className="min-w-48">
                                                    <Label className="text-xs">Gruppierung</Label>
                                                    <Select value={compoundKey} onValueChange={(value) => changeConditionGroupType(i, compoundKey, value)}>
                                                        <SelectTrigger data-testid={`condition-group-type-${i}`}><SelectValue /></SelectTrigger>
                                                        <SelectContent><SelectItem value="all_of">UND – alle müssen zutreffen</SelectItem><SelectItem value="any_of">ODER – eine muss zutreffen</SelectItem></SelectContent>
                                                    </Select>
                                                </div>
                                                <Button type="button" variant="outline" size="sm" onClick={() => addConditionChild(i, compoundKey)} data-testid={`condition-add-child-${i}`}><Plus size={14} className="mr-1" /> Teilbedingung</Button>
                                            </div>
                                            <div className="space-y-2" data-testid={`condition-compound-${i}`}>
                                                {children.map((child, childIndex) => {
                                                    const source = findStepByOrder(child.source_step_order);
                                                    const operator = CONDITION_OPERATOR_OPTIONS.find((option) => option.value === child.operator)?.label || child.operator || '–';
                                                    const value = conditionDisplayValue(child.operator, child.value);
                                                    const childValueOptions = conditionValueOptions(child);
                                                    const childValueMode = conditionValueMode(child.operator, childValueOptions.length > 0);
                                                    const updateChildSource = (sourceValue) => updateConditionChild(i, compoundKey, childIndex, conditionSourceUpdate(sourceValue));
                                                    const updateChildField = (fieldName) => {
                                                        const selectedField = findField(findStepByOrder(child.source_step_order), fieldName);
                                                        updateConditionChild(i, compoundKey, childIndex, conditionFieldUpdate(fieldName, selectedField));
                                                    };
                                                    const updateChildOperator = (nextOperator) => updateConditionChild(i, compoundKey, childIndex, conditionOperatorUpdate(nextOperator, child.value));
                                                    return (
                                                        <details key={childIndex} className="group rounded-md border border-border bg-card" data-testid={`condition-compound-${i}-${childIndex}`} open={childIndex === 0}>
                                                            <summary className="flex cursor-pointer list-none items-center justify-between gap-3 p-3 text-xs hover:bg-muted/40">
                                                                <span><strong>Teilbedingung {childIndex + 1}</strong> · #{child.source_step_order} {source?.title || 'Unbekannt'} · {child.field || 'Status'} · {operator} · {value}</span>
                                                                <span className="text-muted-foreground group-open:rotate-180">⌄</span>
                                                            </summary>
                                                            <div className="grid gap-3 border-t border-border p-3 lg:grid-cols-2">
                                                                <div><Label className="text-xs">1. Quell-Step</Label><SearchableSelect options={withFallbackOption(stepOptions, child.source_step_order, 'Nicht gefundener Schritt')} value={child.source_step_order == null ? '' : String(child.source_step_order)} onChange={updateChildSource} placeholder="Quell-Step auswählen" searchPlaceholder="Step suchen …" testId={`condition-child-source-${i}-${childIndex}`} /></div>
                                                                <div><Label className="text-xs">2. Status oder Feld</Label><SearchableSelect options={sourceFieldOptions(child.source_step_order, child.field)} value={child.field || ''} onChange={updateChildField} placeholder="Feld auswählen" searchPlaceholder="Feld suchen …" testId={`condition-child-field-${i}-${childIndex}`} /></div>
                                                                <div><Label className="text-xs">3. Vergleich</Label><Select value={child.operator} onValueChange={updateChildOperator}><SelectTrigger data-testid={`condition-child-operator-${i}-${childIndex}`}><SelectValue /></SelectTrigger><SelectContent>{conditionOperatorOptions(child).map((option) => <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>)}</SelectContent></Select></div>
                                                                <div><Label className="text-xs">4. Vergleichswert</Label>{childValueMode === 'none' ? <div className="flex min-h-10 items-center rounded-md border border-dashed border-border bg-muted/40 px-3 text-sm text-muted-foreground">Kein Wert erforderlich</div> : childValueMode === 'multi' ? <SearchableMultiSelect options={childValueOptions} values={conditionMultiValue(child.value)} onChange={(values) => updateConditionChild(i, compoundKey, childIndex, { value: values })} placeholder="Werte auswählen" searchPlaceholder="Werte suchen …" testId={`condition-child-values-${i}-${childIndex}`} allowCustom /> : childValueMode === 'select' ? <SearchableSelect options={childValueOptions} value={conditionScalarValue(child.value)} onChange={(nextValue) => updateConditionChild(i, compoundKey, childIndex, { value: nextValue })} placeholder="Wert auswählen" searchPlaceholder="Wert suchen …" testId={`condition-child-value-${i}-${childIndex}`} allowCustom /> : <Input value={conditionScalarValue(child.value)} onChange={(event) => updateConditionChild(i, compoundKey, childIndex, { value: event.target.value })} data-testid={`condition-child-value-input-${i}-${childIndex}`} />}</div>
                                                                <div className="lg:col-span-2 flex justify-end"><Button type="button" variant="ghost" size="sm" disabled={children.length <= 1} onClick={() => removeConditionChild(i, compoundKey, childIndex)} className="text-red-500" data-testid={`condition-remove-child-${i}-${childIndex}`}><Trash size={14} className="mr-1" /> Teilbedingung entfernen</Button></div>
                                                            </div>
                                                        </details>
                                                    );
                                                })}
                                            </div>
                                            <div className="mt-4 grid gap-3 border-t border-border pt-4 lg:grid-cols-2">
                                                <div>
                                                    <Label className="text-xs">Aktion bei Treffer</Label>
                                                    <Select value={c.action} onValueChange={(value) => updateCondition(i, conditionActionUpdate(value, c.target_step_order))}>
                                                        <SelectTrigger className="min-h-10" data-testid={`condition-action-${i}`}><SelectValue /></SelectTrigger>
                                                        <SelectContent>{CONDITION_ACTION_OPTIONS.map((option) => <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>)}</SelectContent>
                                                    </Select>
                                                </div>
                                                <div>
                                                    <Label className="text-xs">Hinweis für Nutzer</Label>
                                                    <Textarea value={c.message || ''} onChange={(event) => updateCondition(i, { message: event.target.value })} className="mt-1 min-h-[68px]" data-testid={`condition-message-${i}`} />
                                                </div>
                                            </div>
                                        </div>
                                    );
                                }
                                return (
                                    <div key={i} className="rounded-lg border border-border bg-card p-4 shadow-sm" data-testid={`condition-card-${i}`}>
                                        <div className="mb-4 flex items-start justify-between gap-3">
                                            <div>
                                                <p className="text-sm font-semibold">Regel {i + 1}</p>
                                                <p className="mt-0.5 text-xs text-muted-foreground">Bei Treffer: {actionLabel}</p>
                                            </div>
                                            <Button type="button" variant="ghost" size="sm" onClick={() => removeCondition(i)} className="h-8 text-red-500"><Trash size={14} className="mr-1" /> Entfernen</Button>
                                        </div>

                                        <div className="grid gap-3 lg:grid-cols-2">
                                            <div>
                                                <Label className="text-xs"><HelpLabel help="Quell-Step, dessen Status oder gespeicherte Felddaten ausgewertet werden.">1. Schritt auswählen</HelpLabel></Label>
                                                <SearchableSelect
                                                    options={withFallbackOption(stepOptions, c.source_step_order, 'Nicht gefundener Schritt')}
                                                    value={c.source_step_order == null ? '' : String(c.source_step_order)}
                                                    onChange={(value) => changeConditionSource(i, value)}
                                                    placeholder="Quell-Schritt auswählen"
                                                    searchPlaceholder="Schritt nach Nummer, Titel oder Typ suchen …"
                                                    testId={`condition-source-step-${i}`}
                                                />
                                            </div>
                                            <div>
                                                <Label className="text-xs"><HelpLabel help="Status prüft pending, in_progress oder completed. Ein Feld prüft den konkreten gespeicherten Nutzerwert.">2. Status oder Feld auswählen</HelpLabel></Label>
                                                <SearchableSelect
                                                    options={sourceFieldOptions(c.source_step_order, c.field)}
                                                    value={c.field || ''}
                                                    onChange={(value) => changeConditionField(i, value)}
                                                    placeholder="Feld auswählen"
                                                    searchPlaceholder="Feld nach Name oder Typ suchen …"
                                                    testId={`condition-source-field-${i}`}
                                                />
                                            </div>
                                            <div>
                                                <Label className="text-xs"><HelpLabel help="Operator für den Vergleich: gleich/ungleich, eine Auswahlmenge, leer/gefüllt oder vorhandener/fehlender Upload.">3. Vergleich</HelpLabel></Label>
                                                <Select value={c.operator} onValueChange={(value) => changeConditionOperator(i, value)}>
                                                    <SelectTrigger className="min-h-10" data-testid={`condition-operator-${i}`}><SelectValue /></SelectTrigger>
                                                    <SelectContent>
                                                        {conditionOperatorOptions(c).map((option) => <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>)}
                                                    </SelectContent>
                                                </Select>
                                            </div>
                                            <div>
                                                <Label className="text-xs"><HelpLabel help="Erwarteter Wert. Bei Status ist dies z. B. completed; bei Auswahlfeldern der technische Optionswert.">4. Vergleichswert</HelpLabel></Label>
                                                {valueMode === 'none' ? (
                                                    <div className="flex min-h-10 items-center rounded-md border border-dashed border-border bg-muted/40 px-3 text-sm text-muted-foreground">Kein Wert erforderlich</div>
                                                ) : valueMode === 'multi' ? (
                                                    <SearchableMultiSelect
                                                        options={valueOptions}
                                                        values={conditionMultiValue(c.value)}
                                                        onChange={(values) => updateCondition(i, { value: values })}
                                                        placeholder="Mehrere Werte auswählen"
                                                        searchPlaceholder="Werte durchsuchen oder eingeben …"
                                                        testId={`condition-values-${i}`}
                                                        allowCustom
                                                    />
                                                ) : valueMode === 'select' ? (
                                                    <SearchableSelect
                                                        options={valueOptions}
                                                        value={conditionScalarValue(c.value)}
                                                        onChange={(value) => updateCondition(i, { value })}
                                                        placeholder="Wert auswählen"
                                                        searchPlaceholder="Wert durchsuchen …"
                                                        testId={`condition-value-${i}`}
                                                        allowCustom
                                                    />
                                                ) : (
                                                    <Input value={conditionScalarValue(c.value)} onChange={(event) => updateCondition(i, { value: event.target.value })} placeholder="Vergleichswert eingeben" data-testid={`condition-value-input-${i}`} />
                                                )}
                                            </div>
                                        </div>

                                        <div className="mt-4 grid gap-3 border-t border-border pt-4 lg:grid-cols-2">
                                            <div>
                                                <Label className="text-xs"><HelpLabel help="Verbergen entfernt den Step aus Journey und Fortschritt; Blockieren zeigt ihn gesperrt; Auto-Abschluss erledigt ihn; Weiterleitung öffnet das Ziel.">5. Aktion bei Treffer</HelpLabel></Label>
                                                <Select value={c.action} onValueChange={(value) => updateCondition(i, conditionActionUpdate(value, c.target_step_order))}>
                                                    <SelectTrigger className="min-h-10" data-testid={`condition-action-${i}`}><SelectValue /></SelectTrigger>
                                                    <SelectContent>
                                                        {CONDITION_ACTION_OPTIONS.map((option) => <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>)}
                                                    </SelectContent>
                                                </Select>
                                            </div>
                                            {c.action === 'redirect' && (
                                                <div>
                                                    <Label className="text-xs"><HelpLabel help="Step, zu dem bei einer zutreffenden Redirect-Regel gewechselt wird.">Ziel-Schritt</HelpLabel></Label>
                                                    <SearchableSelect
                                                        options={withFallbackOption(stepOptions, c.target_step_order, 'Nicht gefundener Schritt')}
                                                        value={c.target_step_order == null ? '' : String(c.target_step_order)}
                                                        onChange={(value) => updateCondition(i, { target_step_order: value ? Number(value) : null })}
                                                        placeholder="Ziel-Schritt auswählen"
                                                        searchPlaceholder="Ziel-Schritt suchen …"
                                                        testId={`condition-target-step-${i}`}
                                                    />
                                                </div>
                                            )}
                                            <div className={c.action === 'redirect' ? 'lg:col-span-2' : ''}>
                                                <Label className="text-xs"><HelpLabel help="Erklärt den Grund der Regel in verständlicher Sprache, besonders bei blockierten Steps.">Hinweis für Nutzer (optional)</HelpLabel></Label>
                                                <Textarea value={c.message || ''} onChange={(event) => updateCondition(i, { message: event.target.value })} className="mt-1 min-h-[68px]" placeholder="Erklärt verständlich, warum der Schritt blockiert, verborgen oder weitergeleitet wird." data-testid={`condition-message-${i}`} />
                                            </div>
                                        </div>
                                    </div>
                                );
                            })}
                            {formData.conditions.length === 0 && <p className="rounded-lg border border-dashed border-border p-6 text-center text-sm text-muted-foreground">Keine Regeln konfiguriert. Dieser Schritt ist ohne zusätzliche Einschränkung erreichbar.</p>}
                        </div>;
}
