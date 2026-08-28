import { Link } from 'react-router-dom';
import { adminAPI, formatApiError } from '../../../lib/api';
import { toast } from 'sonner';
import { Button } from '../../../components/ui/button';



import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../../components/ui/select';



import { TabsContent } from '../../../components/ui/tabs';
import { Plus, Pencil, Trash,             ArrowUp, ArrowDown } from '@phosphor-icons/react';
import StepsFlowBuilder from '../../../components/StepsFlowBuilder';



import { PaginationControls } from '../../../components/PaginationControls';
import { EmptyState, PaginatedCollection, SegmentedControl } from '../../../components/collections';



// Stryker disable all: declarative React adapter over tested step domains, commands and flow builder.
export function StepsTab(props) {
    const { t, steps, surveys, activeSurveyId, setEditingStep, setShowStepDialog, stepTemplates, showTemplatesPanel, setShowTemplatesPanel, stepsView, setStepsView, loadData, sortedSteps, templatesPagination, stepsPagination, handleCreateSurvey, handleSurveyChange, handleDeleteStep, handleMoveStep, handleSaveStepAsTemplate, handleApplyTemplate, handleDeleteTemplate } = props;
    return (
<TabsContent value="steps">
                        <div className="bg-card border border-border rounded-sm">
                            <div className="p-4 border-b border-border flex flex-wrap justify-between items-center gap-2">
                                <div>
                                    <h2 className="text-lg font-semibold text-foreground">Survey & Step Management</h2>
                                    <p className="text-xs text-muted-foreground">Verwalte unterschiedliche Survey-URLs und die dazugehörigen Step-Ketten.</p>
                                </div>
                                <div className="flex flex-wrap gap-2 items-center">
                                    <Select value={activeSurveyId} onValueChange={handleSurveyChange}>
                                        <SelectTrigger className="w-56 h-9" data-testid="admin-survey-select">
                                            <SelectValue placeholder="Survey wählen" />
                                        </SelectTrigger>
                                        <SelectContent>
                                            {surveys.map(s => (
                                                <SelectItem key={s.id} value={s.id}>
                                                    {s.name} /s/{s.slug}
                                                </SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>
                                    {surveys.find(s => s.id === activeSurveyId)?.slug && (
                                        <Link
                                            to={`/s/${encodeURIComponent(surveys.find(s => s.id === activeSurveyId)?.slug)}?preview=1`}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                        >
                                            <Button variant="outline" className="h-9 border-border" data-testid="open-survey-url-btn">
                                                URL öffnen
                                            </Button>
                                        </Link>
                                    )}
                                    <Button variant="outline" onClick={handleCreateSurvey} className="h-9 border-border" data-testid="create-survey-btn">
                                        Survey anlegen
                                    </Button>
                                    <SegmentedControl joined value={stepsView} onChange={setStepsView} testId="steps-view-toggle" options={[
                                        { value: 'flow', label: 'Flow-Ansicht', testId: 'steps-view-flow' },
                                        { value: 'dependency', label: 'Abhängigkeiten', testId: 'steps-view-dependency' },
                                        { value: 'list', label: 'Listen-Ansicht', testId: 'steps-view-list' },
                                    ]} />
                                    <Button
                                        variant="outline"
                                        onClick={() => setShowTemplatesPanel(v => !v)}
                                        className="border-border"
                                        data-testid="toggle-templates-panel-btn"
                                    >
                                        Templates ({stepTemplates.length})
                                    </Button>
                                    <Button onClick={() => { setEditingStep(null); setShowStepDialog(true); }} className="bg-[var(--brand-primary)] hover:bg-[var(--brand-primary-hover)] text-white" data-testid="add-step-btn">
                                        <Plus size={18} className="mr-2" /> Add Step
                                    </Button>
                                </div>
                            </div>

                            {showTemplatesPanel && (
                                <div className="p-4 border-b border-border bg-muted/30" data-testid="step-templates-panel">
                                    <h3 className="text-sm font-semibold text-foreground mb-3">Step-Templates</h3>
                                    {stepTemplates.length === 0 ? (
                                        <p className="text-sm text-muted-foreground">
                                            Noch keine Templates gespeichert. Klicke bei einem Schritt auf „Als Template speichern".
                                        </p>
                                    ) : (
                                        <>
                                        <PaginatedCollection pagination={templatesPagination} id="admin-step-templates" className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3" paginationClassName="-mx-4 -mb-4 mt-4">
                                            {tpl => (
                                                <div key={tpl.id} className="border border-border rounded-sm p-3 bg-card" data-testid={`template-card-${tpl.id}`}>
                                                    <div className="flex items-start justify-between gap-2">
                                                        <div className="min-w-0">
                                                            <p className="text-sm font-semibold text-foreground truncate">{tpl.name}</p>
                                                            <p className="text-xs text-muted-foreground truncate">{tpl.description || tpl.config?.step_type || ''}</p>
                                                        </div>
                                                        <span className="text-[10px] px-1.5 py-0.5 bg-muted text-muted-foreground rounded-sm flex-shrink-0">
                                                            {tpl.config?.step_type || 'form'}
                                                        </span>
                                                    </div>
                                                    <div className="flex gap-2 mt-3">
                                                        <Button size="sm" onClick={() => handleApplyTemplate(tpl)} className="h-7 px-2 text-xs bg-[var(--brand-primary)] hover:bg-[var(--brand-primary-hover)] text-white" data-testid={`apply-template-${tpl.id}`}>
                                                            Einfügen
                                                        </Button>
                                                        <Button size="sm" variant="outline" onClick={() => handleDeleteTemplate(tpl)} className="h-7 px-2 text-xs border-red-200 text-red-500" data-testid={`delete-template-${tpl.id}`}>
                                                            <Trash size={12} />
                                                        </Button>
                                                    </div>
                                                </div>
                                            )}
                                        </PaginatedCollection>
                                        </>
                                    )}
                                </div>
                            )}
                            {stepsView !== 'list' ? (
                                <div className="p-4">
                                    <StepsFlowBuilder
                                        key={activeSurveyId}
                                        layoutMode={stepsView === 'dependency' ? 'dependency' : 'editor'}
                                        steps={steps}
                                        onEdit={(s) => { setEditingStep(s); setShowStepDialog(true); }}
                                        onDelete={(s) => handleDeleteStep(s.id)}
                                        onAddStep={() => { setEditingStep(null); setShowStepDialog(true); }}
                                        onAddStepWithType={(stepType) => {
                                            const maxOrder = steps.length ? Math.max(...steps.map(s => s.order)) : 0;
                                            setEditingStep({
                                                title: '', description: '', step_type: stepType, order: maxOrder + 1,
                                                survey_id: activeSurveyId,
                                                fields: [], required_fields: [], required_uploads: [],
                                                conditions: [], field_mappings: [], duration_value: 0, duration_unit: 'days',
                                                is_active: true,
                                            });
                                            setShowStepDialog(true);
                                        }}
                                        onConditionAdd={async (source, target, form) => {
                                            try {
                                                const newCondition = {
                                                    source_step_order: source.order,
                                                    action: form.action,
                                                    field: form.field || '',
                                                    operator: form.operator,
                                                    value: form.value ?? '',
                                                    target_step_order: form.action === 'redirect' ? target.order : null,
                                                    message: form.message || '',
                                                };
                                                const updatedConditions = [...(target.conditions || []), newCondition];
                                                await adminAPI.updateStep(target.id, { ...target, survey_id: target.survey_id || activeSurveyId, conditions: updatedConditions });
                                                toast.success(`Condition erstellt: ${form.action}`);
                                                loadData();
                                            } catch (error) { toast.error(formatApiError(error)); }
                                        }}
                                        onConditionUpdate={async (stepId, condIndex, updatedCond) => {
                                            try {
                                                const step = steps.find(s => s.id === stepId);
                                                if (!step) return;
                                                const conds = [...step.conditions];
                                                conds[condIndex] = {
                                                    source_step_order: updatedCond.source_step_order ?? conds[condIndex].source_step_order,
                                                    action: updatedCond.action,
                                                    field: updatedCond.field || '',
                                                    operator: updatedCond.operator,
                                                    value: updatedCond.value ?? '',
                                                    target_step_order: updatedCond.action === 'redirect'
                                                        ? (updatedCond.target_step_order ?? conds[condIndex].target_step_order ?? null)
                                                        : null,
                                                    message: updatedCond.message || '',
                                                };
                                                await adminAPI.updateStep(stepId, { ...step, survey_id: step.survey_id || activeSurveyId, conditions: conds });
                                                toast.success('Condition aktualisiert');
                                                loadData();
                                            } catch (error) { toast.error(formatApiError(error)); }
                                        }}
                                        onConditionDelete={async (stepId, condIndex) => {
                                            try {
                                                const step = steps.find(s => s.id === stepId);
                                                if (!step) return;
                                                const conds = step.conditions.filter((_, i) => i !== condIndex);
                                                await adminAPI.updateStep(stepId, { ...step, survey_id: step.survey_id || activeSurveyId, conditions: conds });
                                                toast.success('Condition gelöscht');
                                                loadData();
                                            } catch (error) { toast.error(formatApiError(error)); }
                                        }}
                                        onSaveLayout={async (positions) => {
                                            try {
                                                await adminAPI.saveStepLayout(positions);
                                            } catch (error) { /* silent – non-blocking */ }
                                        }}
                                    />
                                </div>
                            ) : (
                            <div className="p-4 space-y-4">
                                {steps.length === 0 && (
                                    <EmptyState className="rounded-sm border border-dashed border-border p-8" testId="steps-list-empty-state" title="Keine Steps in diesem Survey" description="Erstelle den ersten Step oder wähle ein Template aus." action={<Button
                                            onClick={() => { setEditingStep(null); setShowStepDialog(true); }}
                                            className="bg-[var(--brand-primary)] hover:bg-[var(--brand-primary-hover)] text-white"
                                            data-testid="steps-list-empty-add-step-btn"
                                        >
                                            <Plus size={16} className="mr-2" /> Step erstellen
                                        </Button>} />
                                )}
                                {stepsPagination.paginatedItems.map((step) => (
                                    <div key={step.id} className="border border-border rounded-sm p-4" data-testid={`step-row-order-${step.order}`}>
                                        <div className="flex justify-between items-start">
                                            {/* Reorder arrows */}
                                            <div className="flex flex-col gap-1 mr-3 flex-shrink-0">
                                                <Button
                                                    variant="ghost"
                                                    size="sm"
                                                    onClick={() => handleMoveStep(step.id, 'up')}
                                                    disabled={sortedSteps[0]?.id === step.id}
                                                    className="h-6 w-6 p-0 text-muted-foreground hover:text-foreground disabled:opacity-20"
                                                    data-testid={`step-move-up-${step.id}`}
                                                >
                                                    <ArrowUp size={14} />
                                                </Button>
                                                <Button
                                                    variant="ghost"
                                                    size="sm"
                                                    onClick={() => handleMoveStep(step.id, 'down')}
                                                    disabled={sortedSteps[sortedSteps.length - 1]?.id === step.id}
                                                    className="h-6 w-6 p-0 text-muted-foreground hover:text-foreground disabled:opacity-20"
                                                    data-testid={`step-move-down-${step.id}`}
                                                >
                                                    <ArrowDown size={14} />
                                                </Button>
                                            </div>
                                            <div className="flex-1 min-w-0">
                                                <div className="flex items-center gap-2 flex-wrap">
                                                    <span className="w-8 h-8 rounded-full bg-[var(--brand-primary)] text-white flex items-center justify-center text-sm font-bold flex-shrink-0">
                                                        {step.order}
                                                    </span>
                                                    <h3 className="font-semibold text-foreground">{step.title}</h3>
                                                    <span className={`px-2 py-0.5 text-xs rounded-sm ${step.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-700'}`}>
                                                        {step.is_active ? 'Active' : 'Inactive'}
                                                    </span>
                                                </div>
                                                <p className="text-sm text-muted-foreground mt-1 ml-10">{step.description}</p>
                                                <div className="flex gap-4 mt-2 ml-10 text-xs text-muted-foreground flex-wrap">
                                                    <span>Type: <strong>{step.step_type}</strong></span>
                                                    <span>Fields: <strong>{step.fields?.length || 0}</strong></span>
                                                    <span>Dauer: <strong>{step.duration_value === 0 ? t('step_instant') : `${step.duration_value} ${t('step_' + step.duration_unit)}`}</strong></span>
                                                    {step.email_on_enter && <span className="text-[var(--brand-primary)]">Email on enter</span>}
                                                    {step.email_on_edit && <span className="text-[var(--brand-primary)]">Email on edit</span>}
                                                    {step.email_on_leave && <span className="text-[var(--brand-primary)]">Email on leave</span>}
                                                </div>
                                            </div>
                                            <div className="flex gap-2 flex-shrink-0 ml-4">
                                                <Button variant="outline" size="sm" onClick={() => { setEditingStep(step); setShowStepDialog(true); }} className="border-border text-[var(--brand-primary)] hover:bg-[var(--brand-soft)]" data-testid={`edit-step-${step.id}`}>
                                                    <Pencil size={16} className="mr-1" /> Edit
                                                </Button>
                                                <Button variant="outline" size="sm" onClick={() => handleSaveStepAsTemplate(step)} className="border-border text-muted-foreground hover:text-[var(--brand-primary)]" data-testid={`save-template-${step.id}`} title="Als Template speichern">
                                                    Template
                                                </Button>
                                                <Button variant="outline" size="sm" onClick={() => handleDeleteStep(step.id)} className="border-red-200 text-red-500 hover:bg-red-50" data-testid={`delete-step-${step.id}`}>
                                                    <Trash size={16} className="mr-1" /> Delete
                                                </Button>
                                            </div>
                                        </div>
                                    </div>
                                ))}
                                {steps.length > 0 && (
                                    <PaginationControls pagination={stepsPagination} id="admin-steps" className="-mx-4 -mb-4" />
                                )}
                            </div>
                            )}
                        </div>
                    </TabsContent>
    );
}
