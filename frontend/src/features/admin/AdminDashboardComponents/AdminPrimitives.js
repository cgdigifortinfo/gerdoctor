





import { Switch } from '../../../components/ui/switch';
import { auditActionPresentation } from '../adminPrimitiveDomain';



// Stryker disable all: declarative primitives; badge mapping lives in adminPrimitiveDomain.
export function StatCard({ label, value }) {
    return (
        <div className="bg-card border border-border rounded-sm p-6">
            <p className="text-sm text-muted-foreground mb-1">{label}</p>
            <p className="text-3xl font-black text-foreground">{value}</p>
        </div>
    );
}



export function AuditActionBadge({ action }) {
    const { label, colors } = auditActionPresentation(action);
    return (
        <span className={`px-2 py-1 text-xs font-medium rounded-sm capitalize ${colors}`}>
            {label}
        </span>
    );
}

// ---------------------------------------------------------------------------
// ElementToggle — compact row with a name, description and right-side Switch.
// Used in Settings → UI-Elemente. Intentionally styled to fit later into a
// larger "Rechte­system" screen (user-group matrix rows will reuse this).
// ---------------------------------------------------------------------------
export function ElementToggle({ id, label, description, checked, onChange }) {
    return (
        <div className="flex items-start justify-between gap-4 border border-border rounded-md p-3 bg-background/50">
            <div className="flex-1 min-w-0">
                <label htmlFor={id} className="font-medium text-foreground cursor-pointer block">
                    {label}
                </label>
                {description && (
                    <p className="text-xs text-muted-foreground mt-0.5">{description}</p>
                )}
            </div>
            <Switch
                id={id}
                checked={checked}
                onCheckedChange={onChange}
                data-testid={`element-toggle-${id}`}
                className="shrink-0"
            />
        </div>
    );
}
