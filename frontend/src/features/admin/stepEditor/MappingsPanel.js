import { Button } from '../../../components/ui/button';

import { Label } from '../../../components/ui/label';




import { Plus, Trash } from '@phosphor-icons/react';
import {  SearchableSelect } from '../../../components/admin/EntityPickers';
import { HelpLabel } from '../../../components/ui/help-tooltip';
import {       withFallbackOption } from '../stepEditorDomain';

export function MappingsPanel({ addMapping, formData, removeMapping, stepOptions, changeMappingSource, sourceFieldOptions, updateMapping, currentFieldOptions }) {
    return <div className="space-y-4">
                            <div className="flex items-start justify-between gap-4">
                                <div>
                                    <Label><HelpLabel help="Mappings lesen einen gespeicherten Wert aus dem Quell-Step und schreiben ihn als Vorbelegung in das Zielfeld dieses Steps.">Automatische Feldübernahme</HelpLabel></Label>
                                    <p className="mt-1 text-xs text-muted-foreground">Übernimmt einen Wert aus einem anderen Schritt in ein Feld dieses Schritts.</p>
                                </div>
                                <Button type="button" variant="outline" size="sm" onClick={addMapping} data-testid="add-field-mapping"><Plus size={14} className="mr-1" /> Mapping</Button>
                            </div>
                            {formData.field_mappings.map((m, i) => (
                                <div key={i} className="rounded-lg border border-border bg-card p-4" data-testid={`field-mapping-${i}`}>
                                    <div className="mb-3 flex items-center justify-between">
                                        <p className="text-sm font-semibold">Mapping {i + 1}</p>
                                        <Button type="button" variant="ghost" size="sm" onClick={() => removeMapping(i)} className="h-8 text-red-500"><Trash size={14} className="mr-1" /> Entfernen</Button>
                                    </div>
                                    <div className="grid gap-3 lg:grid-cols-3">
                                        <div>
                                            <Label className="text-xs"><HelpLabel help="Step, dessen bereits gespeicherte Nutzerdaten gelesen werden.">Wert aus Schritt</HelpLabel></Label>
                                            <SearchableSelect
                                                options={withFallbackOption(stepOptions, m.source_step_order, 'Nicht gefundener Schritt')}
                                                value={m.source_step_order == null ? '' : String(m.source_step_order)}
                                                onChange={(value) => changeMappingSource(i, value)}
                                                placeholder="Quell-Schritt auswählen"
                                                searchPlaceholder="Schritt suchen …"
                                                testId={`mapping-source-step-${i}`}
                                            />
                                        </div>
                                        <div>
                                            <Label className="text-xs"><HelpLabel help="Technischer Feldname, aus dem der Wert übernommen wird.">Quellfeld</HelpLabel></Label>
                                            <SearchableSelect
                                                options={sourceFieldOptions(m.source_step_order, m.source_field).filter((option) => option.value !== 'status')}
                                                value={m.source_field || ''}
                                                onChange={(value) => updateMapping(i, { source_field: value })}
                                                placeholder="Quellfeld auswählen"
                                                searchPlaceholder="Feld suchen …"
                                                testId={`mapping-source-field-${i}`}
                                            />
                                        </div>
                                        <div>
                                            <Label className="text-xs"><HelpLabel help="Feld dieses Steps, das mit dem gelesenen Wert vorbelegt wird.">Zielfeld in diesem Schritt</HelpLabel></Label>
                                            <SearchableSelect
                                                options={withFallbackOption(currentFieldOptions, m.target_field, 'Nicht gefundenes Feld')}
                                                value={m.target_field || ''}
                                                onChange={(value) => updateMapping(i, { target_field: value })}
                                                placeholder="Zielfeld auswählen"
                                                searchPlaceholder="Zielfeld suchen …"
                                                testId={`mapping-target-field-${i}`}
                                            />
                                        </div>
                                    </div>
                                </div>
                            ))}
                            {formData.field_mappings.length === 0 && <p className="rounded-lg border border-dashed border-border p-6 text-center text-sm text-muted-foreground">Keine Mappings konfiguriert. Mit „Mapping“ können Daten ohne erneute Eingabe übernommen werden.</p>}
                        </div>;
}
