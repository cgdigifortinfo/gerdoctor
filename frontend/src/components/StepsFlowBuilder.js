import { useState, useMemo, useCallback, useEffect, useRef } from 'react';
import ReactFlow, {
    Background, Controls, Handle, Position, MiniMap,
    useNodesState, useEdgesState, MarkerType, addEdge,
    ReactFlowProvider, useReactFlow,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { Button } from './ui/button';
import { Plus, Pencil, Trash, LockSimple, EyeSlash, CheckCircle, ArrowsClockwise, CaretRight } from '@phosphor-icons/react';

// ---- Step type → icon + accent color ----
const TYPE_STYLES = {
    form: { label: 'Formular', color: '#114f55', bg: '#114f55' },
    decision: { label: 'Entscheidung', color: '#8b5a00', bg: '#d97706' },
    partner_selection: { label: 'Partner', color: '#2563eb', bg: '#2563eb' },
    partner_multiselection: { label: 'Partner (Multi)', color: '#7c3aed', bg: '#7c3aed' },
    milestone: { label: 'Meilenstein', color: '#059669', bg: '#059669' },
    display: { label: 'Info', color: '#64748b', bg: '#64748b' },
};

const ACTION_LABELS = {
    hide: { label: 'Ausblenden', color: '#94a3b8', icon: EyeSlash },
    block: { label: 'Blockieren', color: '#dc2626', icon: LockSimple },
    auto_complete: { label: 'Auto-Abschluss', color: '#059669', icon: CheckCircle },
    allow_next: { label: 'Weiter', color: '#114f55', icon: CaretRight },
    redirect: { label: 'Weiterleiten', color: '#2563eb', icon: ArrowsClockwise },
};

// ---- Custom step node ----
function StepNode({ data }) {
    const style = TYPE_STYLES[data.step_type] || TYPE_STYLES.form;
    return (
        <div
            className="rounded-sm shadow-md border-2 min-w-[220px] max-w-[260px] bg-white dark:bg-slate-800"
            style={{ borderColor: style.color }}
            data-testid={`flow-node-${data.id}`}
        >
            <Handle type="target" position={Position.Left} id="in" style={{ background: style.color, width: 10, height: 10 }} />
            <div
                className="px-3 py-1.5 flex items-center justify-between text-xs font-semibold text-white"
                style={{ background: style.bg }}
            >
                <span>#{data.order} · {style.label}</span>
                <div className="flex gap-1">
                    <button
                        onClick={(e) => { e.stopPropagation(); data.onEdit(data.raw); }}
                        className="hover:bg-white/20 rounded p-0.5"
                        data-testid={`flow-edit-${data.id}`}
                        title="Bearbeiten"
                    >
                        <Pencil size={12} />
                    </button>
                    <button
                        onClick={(e) => { e.stopPropagation(); data.onDelete(data.raw); }}
                        className="hover:bg-red-500/40 rounded p-0.5"
                        data-testid={`flow-delete-${data.id}`}
                        title="Löschen"
                    >
                        <Trash size={12} />
                    </button>
                </div>
            </div>
            <div className="px-3 py-2.5">
                <p className="text-sm font-semibold text-foreground line-clamp-2">{data.title}</p>
                {data.filter_tag && (
                    <span className="mt-1 inline-block px-1.5 py-0.5 text-[10px] bg-muted text-muted-foreground rounded-sm">
                        tag: {data.filter_tag}
                    </span>
                )}
                {data.duration_value > 0 && (
                    <span className="mt-1 ml-1 inline-block px-1.5 py-0.5 text-[10px] bg-amber-100 text-amber-800 rounded-sm">
                        ⏱ {data.duration_value}{data.duration_unit?.[0]}
                    </span>
                )}
            </div>
            <Handle type="source" position={Position.Right} id="out" style={{ background: style.color, width: 10, height: 10 }} />
        </div>
    );
}

const nodeTypes = { stepNode: StepNode };

function buildGraph(steps, callbacks) {
    const sorted = [...steps].sort((a, b) => a.order - b.order);
    const byOrder = Object.fromEntries(sorted.map(s => [s.order, s]));

    const nodes = sorted.map((s, i) => ({
        id: s.id,
        type: 'stepNode',
        position: { x: i * 280, y: 100 + (i % 2) * 40 },
        data: {
            id: s.id, order: s.order, title: s.title,
            step_type: s.step_type, filter_tag: s.filter_tag,
            duration_value: s.duration_value, duration_unit: s.duration_unit,
            raw: s,
            onEdit: callbacks.onEdit,
            onDelete: callbacks.onDelete,
        },
    }));

    const edges = [];
    sorted.forEach(s => {
        for (const c of (s.conditions || [])) {
            const src = byOrder[c.source_step_order];
            if (!src) continue;
            const action = ACTION_LABELS[c.action] || { label: c.action, color: '#64748b' };
            const valueLabel = c.value ? ` = ${c.value}` : '';
            const fieldLabel = c.field ? `${c.field}` : '(status)';
            edges.push({
                id: `${src.id}-${s.id}-${c.action}`,
                source: src.id, target: s.id,
                label: `${action.label}: ${fieldLabel}${valueLabel}`,
                labelStyle: { fontSize: 10, fill: action.color, fontWeight: 600 },
                labelBgPadding: [4, 2], labelBgBorderRadius: 2,
                labelBgStyle: { fill: 'white', fillOpacity: 0.95 },
                style: { stroke: action.color, strokeWidth: 1.6, strokeDasharray: c.action === 'hide' ? '4 3' : undefined },
                animated: c.action === 'auto_complete',
                markerEnd: { type: MarkerType.ArrowClosed, color: action.color },
            });
        }
    });

    // Sequence arrows between consecutive steps (soft grey)
    for (let i = 0; i < sorted.length - 1; i++) {
        const from = sorted[i], to = sorted[i + 1];
        const hasCondEdge = edges.some(e => e.source === from.id && e.target === to.id);
        if (!hasCondEdge) {
            edges.push({
                id: `seq-${from.id}-${to.id}`,
                source: from.id, target: to.id,
                style: { stroke: '#d4d4d8', strokeWidth: 1, strokeDasharray: '2 4' },
                markerEnd: { type: MarkerType.ArrowClosed, color: '#d4d4d8' },
            });
        }
    }
    return { nodes, edges };
}

// ===== Palette sidebar =====
function Palette() {
    const onDragStart = (event, stepType) => {
        event.dataTransfer.setData('application/gerdoctor-step-type', stepType);
        event.dataTransfer.effectAllowed = 'copy';
    };
    return (
        <div className="w-48 flex-shrink-0 border-r border-border bg-card p-3" data-testid="flow-palette">
            <p className="text-[11px] uppercase tracking-wider text-muted-foreground mb-3 font-semibold">Step-Typen</p>
            <p className="text-[11px] text-muted-foreground mb-3">Ziehen Sie einen Typ auf den Canvas.</p>
            <div className="space-y-2">
                {Object.entries(TYPE_STYLES).map(([k, v]) => (
                    <div
                        key={k}
                        draggable
                        onDragStart={(e) => onDragStart(e, k)}
                        className="px-2.5 py-2 rounded-sm border border-border cursor-grab active:cursor-grabbing text-xs font-medium flex items-center gap-2 hover:shadow-sm transition-all"
                        style={{ borderLeftWidth: 3, borderLeftColor: v.bg }}
                        data-testid={`palette-item-${k}`}
                    >
                        <span className="w-2 h-2 rounded-sm flex-shrink-0" style={{ background: v.bg }} />
                        <span className="truncate">{v.label}</span>
                    </div>
                ))}
            </div>
        </div>
    );
}

// ===== Condition creation modal (for edge-drag) =====
function ConditionModal({ open, source, target, onCancel, onConfirm }) {
    const [form, setForm] = useState({ action: 'hide', field: '', operator: 'equals', value: '' });
    useEffect(() => {
        if (open) setForm({ action: 'hide', field: '', operator: 'equals', value: '' });
    }, [open]);
    if (!open || !source || !target) return null;
    return (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={onCancel}>
            <div className="bg-card border border-border rounded-sm shadow-lg p-6 max-w-md w-full mx-4" onClick={(e) => e.stopPropagation()} data-testid="condition-modal">
                <h3 className="text-lg font-semibold text-foreground mb-1">Neue Condition</h3>
                <p className="text-xs text-muted-foreground mb-4">
                    Von <span className="font-semibold">#{source.order} {source.title}</span> →
                    auf <span className="font-semibold">#{target.order} {target.title}</span>
                </p>
                <div className="space-y-3">
                    <div>
                        <label className="text-xs font-medium text-foreground">Aktion</label>
                        <select
                            value={form.action}
                            onChange={(e) => setForm({ ...form, action: e.target.value })}
                            className="w-full mt-1 px-2 py-1.5 text-sm bg-background border border-border rounded-sm"
                            data-testid="condition-action-select"
                        >
                            <option value="hide">Ausblenden</option>
                            <option value="block">Blockieren</option>
                            <option value="auto_complete">Auto-Abschließen</option>
                            <option value="allow_next">Weiter erlauben</option>
                            <option value="redirect">Weiterleiten</option>
                        </select>
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                        <div>
                            <label className="text-xs font-medium text-foreground">Feld (optional)</label>
                            <input
                                type="text"
                                value={form.field}
                                onChange={(e) => setForm({ ...form, field: e.target.value })}
                                placeholder="decision"
                                className="w-full mt-1 px-2 py-1.5 text-sm bg-background border border-border rounded-sm"
                                data-testid="condition-field-input"
                            />
                        </div>
                        <div>
                            <label className="text-xs font-medium text-foreground">Operator</label>
                            <select
                                value={form.operator}
                                onChange={(e) => setForm({ ...form, operator: e.target.value })}
                                className="w-full mt-1 px-2 py-1.5 text-sm bg-background border border-border rounded-sm"
                                data-testid="condition-operator-select"
                            >
                                <option value="equals">gleich</option>
                                <option value="not_equals">ungleich</option>
                                <option value="contains">enthält</option>
                                <option value="not_empty">nicht leer</option>
                                <option value="empty">leer</option>
                                <option value="status_is">Status ist</option>
                                <option value="status_not">Status ungleich</option>
                            </select>
                        </div>
                    </div>
                    <div>
                        <label className="text-xs font-medium text-foreground">Wert</label>
                        <input
                            type="text"
                            value={form.value}
                            onChange={(e) => setForm({ ...form, value: e.target.value })}
                            placeholder="upload"
                            className="w-full mt-1 px-2 py-1.5 text-sm bg-background border border-border rounded-sm"
                            data-testid="condition-value-input"
                        />
                    </div>
                </div>
                <div className="flex gap-2 justify-end mt-5">
                    <Button variant="outline" size="sm" onClick={onCancel} data-testid="condition-cancel-btn">Abbrechen</Button>
                    <Button size="sm" onClick={() => onConfirm(form)} className="bg-[#114f55] hover:bg-[#0d3d42] text-white" data-testid="condition-confirm-btn">Speichern</Button>
                </div>
            </div>
        </div>
    );
}

// ===== Inner component with ReactFlow hooks =====
function FlowInner({ steps, onEdit, onDelete, onAddStep, onAddStepWithType, onConditionAdd }) {
    const callbacks = useMemo(() => ({ onEdit, onDelete }), [onEdit, onDelete]);
    const initial = useMemo(() => buildGraph(steps, callbacks), [steps, callbacks]);
    const [nodes, setNodes, onNodesChange] = useNodesState(initial.nodes);
    const [edges, setEdges, onEdgesChange] = useEdgesState(initial.edges);
    const [pendingConnection, setPendingConnection] = useState(null);
    const flowWrapper = useRef(null);
    const { project } = useReactFlow();

    useEffect(() => {
        const fresh = buildGraph(steps, callbacks);
        setNodes(fresh.nodes);
        setEdges(fresh.edges);
    }, [steps, callbacks, setNodes, setEdges]);

    // Edge drag → open modal
    const handleConnect = useCallback((params) => {
        const source = steps.find(s => s.id === params.source);
        const target = steps.find(s => s.id === params.target);
        if (!source || !target || source.id === target.id) return;
        setPendingConnection({ source, target });
    }, [steps]);

    // Palette drop → create new step at that position
    const handleDragOver = useCallback((event) => {
        event.preventDefault();
        event.dataTransfer.dropEffect = 'copy';
    }, []);

    const handleDrop = useCallback((event) => {
        event.preventDefault();
        const stepType = event.dataTransfer.getData('application/gerdoctor-step-type');
        if (!stepType) return;
        const bounds = flowWrapper.current.getBoundingClientRect();
        const pos = project({ x: event.clientX - bounds.left, y: event.clientY - bounds.top });
        onAddStepWithType?.(stepType, pos);
    }, [project, onAddStepWithType]);

    return (
        <div className="relative h-[640px] border border-border rounded-sm bg-muted/20 flex" data-testid="steps-flow-builder">
            <Palette />
            <div className="flex-1 relative" ref={flowWrapper} onDragOver={handleDragOver} onDrop={handleDrop}>
                <div className="absolute top-3 left-3 z-10 flex gap-2">
                    <Button size="sm" onClick={() => onAddStep?.()} className="bg-[#114f55] hover:bg-[#0d3d42] text-white shadow" data-testid="flow-add-step-btn">
                        <Plus size={14} className="mr-1" /> Step hinzufügen
                    </Button>
                </div>
                <div className="absolute top-3 right-3 z-10 flex flex-wrap gap-2 max-w-[60%] justify-end">
                    {Object.entries(ACTION_LABELS).map(([k, v]) => (
                        <span key={k} className="inline-flex items-center gap-1 px-2 py-0.5 text-[10px] bg-white dark:bg-slate-800 border border-border rounded-sm shadow-sm">
                            <span className="w-3 h-[1.5px]" style={{ background: v.color }} />
                            {v.label}
                        </span>
                    ))}
                </div>
                <ReactFlow
                    nodes={nodes} edges={edges}
                    onNodesChange={onNodesChange} onEdgesChange={onEdgesChange}
                    onConnect={handleConnect}
                    nodeTypes={nodeTypes}
                    fitView
                    fitViewOptions={{ padding: 0.2 }}
                    proOptions={{ hideAttribution: true }}
                >
                    <Background gap={16} size={1} color="#cbd5e1" />
                    <Controls showInteractive={false} />
                    <MiniMap pannable zoomable nodeColor={n => (TYPE_STYLES[n.data?.step_type]?.bg) || '#94a3b8'} />
                </ReactFlow>
            </div>
            <ConditionModal
                open={!!pendingConnection}
                source={pendingConnection?.source}
                target={pendingConnection?.target}
                onCancel={() => setPendingConnection(null)}
                onConfirm={(form) => {
                    onConditionAdd?.(pendingConnection.source, pendingConnection.target, form);
                    setPendingConnection(null);
                }}
            />
        </div>
    );
}

export default function StepsFlowBuilder(props) {
    return (
        <ReactFlowProvider>
            <FlowInner {...props} />
        </ReactFlowProvider>
    );
}
