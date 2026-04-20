import { Play } from '@phosphor-icons/react';
import { SIMULATOR_PROFILES } from '../lib/stepVisibility';

const LEGEND = [
    { key: 'visible', label: 'sichtbar', color: '#2dd4bf' },
    { key: 'hidden', label: 'versteckt', color: '#94a3b8' },
    { key: 'blocked', label: 'blockiert', color: '#dc2626' },
    { key: 'auto_complete', label: 'auto-abgeschlossen', color: '#10b981' },
];

/**
 * Simulator control: drop-down that selects one of the SIMULATOR_PROFILES.
 * Rendering of node tints happens in the FlowBuilder — this component only
 * exposes the selected profile key.
 */
export default function FlowSimulatorPanel({ value, onChange }) {
    const active = value && value !== 'none';
    return (
        <div
            className="inline-flex items-center gap-2 bg-card border border-border rounded-sm shadow px-2 py-1"
            data-testid="flow-simulator-panel"
        >
            <Play size={14} className={active ? 'text-emerald-600' : 'text-[#114f55]'} weight={active ? 'fill' : 'regular'} />
            <label className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
                Simulator
            </label>
            <select
                value={value || 'none'}
                onChange={(e) => onChange(e.target.value)}
                className="text-xs bg-background border border-border rounded-sm px-1.5 py-1"
                data-testid="flow-simulator-select"
            >
                {Object.entries(SIMULATOR_PROFILES).map(([key, p]) => (
                    <option key={key} value={key}>{p.label}</option>
                ))}
            </select>
            {active && (
                <div className="hidden md:flex items-center gap-2 ml-1 pl-2 border-l border-border">
                    {LEGEND.map((l) => (
                        <span key={l.key} className="inline-flex items-center gap-1 text-[10px] text-muted-foreground">
                            <span className="w-2 h-2 rounded-sm" style={{ background: l.color }} />
                            {l.label}
                        </span>
                    ))}
                </div>
            )}
        </div>
    );
}
