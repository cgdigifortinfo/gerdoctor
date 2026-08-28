
import { Input } from '../../../components/ui/input';
import { Label } from '../../../components/ui/label';
import { Textarea } from '../../../components/ui/textarea';








export function TranslationsPanel({ translations, setTrans, formData }) {
    return <div className="space-y-4">
                            <div className="flex items-center gap-2 p-3 bg-blue-50 dark:bg-blue-950/30 rounded-sm border border-blue-200 dark:border-blue-800">
                                <span className="text-xs font-bold text-blue-700 dark:text-blue-300 bg-blue-200 dark:bg-blue-800 px-1.5 py-0.5 rounded">EN</span>
                                <span className="text-sm text-blue-700 dark:text-blue-300">English Translation</span>
                            </div>
                            <div className="space-y-3">
                                <div>
                                    <Label className="text-xs">Title (EN)</Label>
                                    <Input value={translations.en?.title || ''} onChange={(e) => setTrans('en', 'title', e.target.value)} className="h-8 text-sm mt-1" placeholder={formData.title} data-testid="trans-en-title" />
                                </div>
                                <div>
                                    <Label className="text-xs">Description (EN)</Label>
                                    <Textarea value={translations.en?.description || ''} onChange={(e) => setTrans('en', 'description', e.target.value)} className="text-sm mt-1 min-h-[60px]" placeholder={formData.description} data-testid="trans-en-description" />
                                </div>
                                {(formData.step_type === 'display' || formData.step_type === 'milestone') && (
                                    <>
                                        <div>
                                            <Label className="text-xs">Pending Message (EN)</Label>
                                            <Input value={translations.en?.pending_message || ''} onChange={(e) => setTrans('en', 'pending_message', e.target.value)} className="h-8 text-sm mt-1" placeholder={formData.pending_message} />
                                        </div>
                                        <div>
                                            <Label className="text-xs">Action Label (EN)</Label>
                                            <Input value={translations.en?.action_label || ''} onChange={(e) => setTrans('en', 'action_label', e.target.value)} className="h-8 text-sm mt-1" placeholder={formData.action_label} />
                                        </div>
                                    </>
                                )}
                                {formData.skippable && (
                                    <div>
                                        <Label className="text-xs">Skip Label (EN)</Label>
                                        <Input value={translations.en?.skip_label || ''} onChange={(e) => setTrans('en', 'skip_label', e.target.value)} className="h-8 text-sm mt-1" placeholder={formData.skip_label} />
                                    </div>
                                )}
                            </div>
                            <p className="text-xs text-muted-foreground">Deutsche Texte (DE) werden im Tab "Basis" gepflegt. Hier nur die englische Uebersetzung eingeben.</p>
                        </div>;
}
