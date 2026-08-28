

import { Label } from '../../../components/ui/label';





import { SearchableMultiSelect } from '../../../components/admin/EntityPickers';
import { CONTENT_FIELD_TYPES } from '../../../components/admin/surveyFormDomain';
import { HelpLabel } from '../../../components/ui/help-tooltip';
import {       withFallbackOption } from '../stepEditorDomain';

export function RequirementsPanel({ formData, currentFieldOptions, setFormData, documentTypeOptions }) {
    return <div className="space-y-4">
                            <div className="rounded-lg border border-border p-4">
                                <Label className="block"><HelpLabel help="Diese internen Feldnamen werden beim Abschluss serverseitig geprüft. Leere Werte verhindern den Abschluss.">Pflichtfelder</HelpLabel></Label>
                                <p className="mb-3 mt-1 text-xs text-muted-foreground">Mehrere Formularfelder durchsuchen und auswählen. Nutzer können den Schritt erst abschließen, wenn alle ausgewählten Felder ausgefüllt sind.</p>
                                <SearchableMultiSelect
                                    options={formData.required_fields.reduce((options, value) => withFallbackOption(options, value), currentFieldOptions)}
                                    values={formData.required_fields}
                                    onChange={(values) => setFormData((current) => ({
                                        ...current,
                                        required_fields: values,
                                        fields: current.fields.map((field) => CONTENT_FIELD_TYPES.has(field.field_type) || field.field_type === 'multiupload'
                                            ? field
                                            : { ...field, required: values.includes(field.name) }),
                                    }))}
                                    placeholder={formData.fields.length > 0 ? 'Pflichtfelder auswählen' : 'Noch keine Formularfelder definiert'}
                                    searchPlaceholder="Formularfelder durchsuchen …"
                                    testId="step-required-fields"
                                />
                            </div>
                            <div className="rounded-lg border border-border p-4">
                                <Label className="block"><HelpLabel help="Prüft Dokumentlisten auf Uploads mit passendem document_type. Alle ausgewählten Typen müssen vorhanden sein.">Erforderliche Dokumenttypen</HelpLabel></Label>
                                <p className="mb-3 mt-1 text-xs text-muted-foreground">Dokumenttypen aus Upload-Feldern auswählen oder einen neuen Namen eingeben. Mehrfachauswahl ist möglich.</p>
                                <SearchableMultiSelect
                                    options={documentTypeOptions}
                                    values={formData.required_uploads}
                                    onChange={(values) => setFormData({ ...formData, required_uploads: values })}
                                    placeholder="Dokumenttypen auswählen"
                                    searchPlaceholder="Dokumenttyp suchen oder neu eingeben …"
                                    testId="step-required-uploads"
                                    allowCustom
                                />
                            </div>
                        </div>;
}
