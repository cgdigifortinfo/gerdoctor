import React, { useMemo, memo } from 'react';
import { ArrowRight, Cloud, Users, CheckCircle, ListChecks, Hourglass, ClipboardText } from '@phosphor-icons/react';

/**
 * JourneyProgressIndicator
 * ------------------------
 * Compact banner rendered ABOVE the active step card in the User Dashboard.
 * Shows:
 *   • "Schritt X von Y" — the user's position in the visible timeline.
 *   • A short hint about what the current step is.
 *   • A preview of the next 1–2 steps. For decision steps we split into the
 *     two possible branches (Upload-Pfad + Partner-Pfad) so the user knows
 *     what choosing each option unlocks.
 *
 * Intentionally stateless / read-only — it never mutates steps or progress.
 * All copy in German.
 */

// Map step_type → small icon + short label
const STEP_ICON = {
    decision: ListChecks,
    form: ClipboardText,
    upload: Cloud,
    partner_selection: Users,
    partner_multiselection: Users,
    milestone: Hourglass,
};
const STEP_ICON_COLOR = {
    decision: 'text-sky-600',
    form: 'text-slate-600',
    upload: 'text-amber-600',
    partner_selection: 'text-violet-600',
    partner_multiselection: 'text-violet-600',
    milestone: 'text-emerald-600',
};
const STEP_TYPE_LABEL = {
    decision: 'Entscheidung',
    form: 'Formular',
    upload: 'Upload',
    partner_selection: 'Partnerwahl',
    partner_multiselection: 'Partnerauswahl',
    milestone: 'Meilenstein',
};

// Figure out which step_type a non-decision step really is.
// Many "upload" steps in this app are stored as step_type='form' with an upload
// field — detect that so we can show the Cloud icon.
function resolveStepType(step) {
    if (!step) return 'form';
    if (step.step_type === 'form') {
        const fields = step.fields || [];
        if (fields.some((f) => f.field_type === 'file' || f.field_type === 'upload')) return 'upload';
    }
    return step.step_type || 'form';
}

// ---- Branch preview for decision steps -----------------------------------
// Build the two (or more) branches a user can pick: each branch = {label,
// icon, preview_step_titles[]}. We compute by walking subsequent steps and
// matching `hide` conditions that would apply if decision === option.value.
function computeDecisionBranches(currentStep, allSteps) {
    const decField = (currentStep.fields || []).find((f) => f.field_type === 'decision')
                   || (currentStep.fields || [])[0];
    const options = decField?.options || [];
    if (!options.length) return [];

    const sorted = [...(allSteps || [])].sort((a, b) => a.order - b.order);
    const current_order = currentStep.order;

    return options.map((opt) => {
        // Simulate "what becomes visible if decision === opt.value"
        const simulated = { ...Object.fromEntries(sorted.map((s) => [s.order, { data: {}, status: 'pending' }])) };
        simulated[current_order] = { data: { decision: opt.value }, status: 'completed' };

        const visible = [];
        for (const s of sorted) {
            if (s.order <= current_order) continue;
            if (s.order > current_order + 4) break;  // only peek 4 steps ahead

            // Evaluate hide conditions manually (mirrors stepVisibility.js logic)
            let hidden = false;
            for (const c of s.conditions || []) {
                if (c.action !== 'hide') continue;
                const source = simulated[c.source_step_order];
                if (!source) continue;
                const data = source.data || {};
                const field = c.field;
                const fv = field ? data[field] : source.status;
                const expected = c.value;
                let match = false;
                switch (c.operator) {
                    case 'equals': match = String(fv) === String(expected); break;
                    case 'not_equals': match = String(fv) !== String(expected); break;
                    case 'empty': match = !fv || fv === ''; break;
                    case 'not_empty': match = !!fv && fv !== ''; break;
                    default: match = false;
                }
                if (match) { hidden = true; break; }
            }
            if (!hidden) visible.push(s);
            if (visible.length >= 2) break;
        }

        return {
            value: opt.value,
            label: opt.label || opt.value,
            steps: visible,
        };
    });
}

// Get the next N non-hidden steps in the visible timeline after currentIndex.
function nextVisibleSteps(visibleSteps, currentIndex, n = 2) {
    return (visibleSteps || []).slice(currentIndex + 1, currentIndex + 1 + n);
}

// ---- Component -----------------------------------------------------------
function JourneyProgressIndicatorImpl({ visibleSteps, currentIndex, allSteps }) {
    const currentStep = visibleSteps?.[currentIndex];
    const total = visibleSteps?.length || 0;
    const position = (currentIndex ?? 0) + 1;

    const branches = useMemo(() => {
        if (!currentStep || currentStep.step_type !== 'decision') return [];
        return computeDecisionBranches(currentStep, allSteps);
    }, [currentStep, allSteps]);

    const upcoming = useMemo(
        () => (currentStep?.step_type !== 'decision'
            ? nextVisibleSteps(visibleSteps, currentIndex, 2)
            : []),
        [visibleSteps, currentIndex, currentStep]
    );

    if (!currentStep) return null;

    const currentType = resolveStepType(currentStep);
    const CurrentIcon = STEP_ICON[currentType] || ClipboardText;

    return (
        <div
            className="bg-gradient-to-r from-[#114f55]/5 to-transparent border border-[#114f55]/20 rounded-sm p-4 mb-4"
            data-testid="journey-progress-indicator"
        >
            {/* Counter + current step title */}
            <div className="flex flex-wrap items-center gap-3">
                <span
                    className="text-xs uppercase tracking-wider font-medium bg-[#114f55] text-white px-2 py-1 rounded"
                    data-testid="journey-step-counter"
                >
                    Schritt {position} von {total}
                </span>
                <div className={`flex items-center gap-2 ${STEP_ICON_COLOR[currentType] || 'text-foreground'}`}>
                    <CurrentIcon size={18} weight="duotone" />
                    <span className="font-semibold text-foreground" data-testid="journey-current-title">
                        {currentStep.title}
                    </span>
                </div>
                <span className="text-xs text-muted-foreground bg-muted px-2 py-0.5 rounded">
                    {STEP_TYPE_LABEL[currentType] || 'Schritt'}
                </span>
            </div>

            {/* --- Decision → show both branches --- */}
            {branches.length > 0 && (
                <div
                    className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-3"
                    data-testid="journey-decision-branches"
                >
                    {branches.map((b, idx) => (
                        <div
                            key={b.value}
                            className="bg-background/60 border border-border rounded-sm p-3"
                            data-testid={`journey-branch-${b.value}`}
                        >
                            <div className="flex items-center gap-2 text-xs uppercase tracking-wider text-muted-foreground mb-2">
                                <span className="w-5 h-5 rounded-full bg-[#114f55] text-white flex items-center justify-center text-[10px] font-bold">
                                    {idx === 0 ? 'A' : 'B'}
                                </span>
                                <span>Wenn „{b.label}"</span>
                            </div>
                            {b.steps.length === 0 ? (
                                <p className="text-sm text-muted-foreground">→ direkt zum Meilenstein</p>
                            ) : (
                                <ol className="space-y-1">
                                    {b.steps.map((s) => {
                                        const t = resolveStepType(s);
                                        const Icon = STEP_ICON[t] || ClipboardText;
                                        return (
                                            <li key={s.id || s.step_id} className="flex items-center gap-2 text-sm">
                                                <Icon
                                                    size={14}
                                                    className={STEP_ICON_COLOR[t] || 'text-foreground'}
                                                    weight="duotone"
                                                />
                                                <span className="text-foreground">{s.title}</span>
                                            </li>
                                        );
                                    })}
                                </ol>
                            )}
                        </div>
                    ))}
                </div>
            )}

            {/* --- Non-decision → linear 1-2 step preview --- */}
            {upcoming.length > 0 && (
                <div
                    className="mt-3 flex flex-wrap items-center gap-2 text-sm"
                    data-testid="journey-upcoming"
                >
                    <span className="text-xs uppercase tracking-wider text-muted-foreground">
                        Als Nächstes
                    </span>
                    {upcoming.map((s, idx) => {
                        const t = resolveStepType(s);
                        const Icon = STEP_ICON[t] || ClipboardText;
                        return (
                            <React.Fragment key={s.id || s.step_id}>
                                {idx > 0 && <ArrowRight size={14} className="text-muted-foreground" />}
                                <span className="inline-flex items-center gap-1.5 bg-background/60 border border-border rounded px-2 py-1">
                                    <Icon
                                        size={14}
                                        className={STEP_ICON_COLOR[t] || 'text-foreground'}
                                        weight="duotone"
                                    />
                                    <span className="text-foreground">{s.title}</span>
                                </span>
                            </React.Fragment>
                        );
                    })}
                </div>
            )}

            {/* Milestone-specific hint */}
            {currentType === 'milestone' && (
                <p
                    className="mt-3 text-sm text-muted-foreground flex items-center gap-2"
                    data-testid="journey-milestone-hint"
                >
                    <CheckCircle size={14} className="text-emerald-600" weight="duotone" />
                    Ihr Partner bearbeitet diesen Schritt — sobald freigegeben geht es automatisch weiter.
                </p>
            )}
        </div>
    );
}

export const JourneyProgressIndicator = memo(JourneyProgressIndicatorImpl);
export default JourneyProgressIndicator;