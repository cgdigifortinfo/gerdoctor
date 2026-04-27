import { useState, useMemo, useCallback, useEffect, useRef } from 'react';
import ReactFlow, {
    Background, Controls, Handle, Position, MiniMap,
    useNodesState, useEdgesState, MarkerType, addEdge,
    ReactFlowProvider, useReactFlow,
} from 'reactflow';
import 'reactflow/dist/style.css';
import dagre from 'dagre';
import { Button } from './ui/button';
import { Plus, Pencil, Trash, LockSimple, EyeSlash, CheckCircle, ArrowsClockwise, CaretRight, Graph, ArrowsOut, ArrowsIn, ArrowUUpLeft, ArrowUUpRight, Play, Stop } from '@phosphor-icons/react';
import { simulateJourney, SIMULATOR_PROFILES } from '../lib/stepVisibility';
import { useFlowHistory } from '../hooks/useFlowHistory';
import FlowSimulatorPanel from './FlowSimulatorPanel';

// ---- Duration helpers (for animated playback ETA) ----
function durationToDays(value, unit) {
    const n = Number(value) || 0;
    switch (unit) {
        case 'hours': return n / 24;
        case 'days': return n;
        case 'weeks': return n * 7;
        case 'months': return n * 30;
        case 'years': return n * 365;
        default: return n;
    }
}
function formatDays(days) {
    const d = Math.round(days);
    if (d < 1) return '0d';
    if (d < 14) return `${d}d`;
    if (d < 60) return `${Math.round(d / 7)}w`;
    return `${Math.round(d / 30)}M`;
}

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
    const sim = data.simState;
    const isPlayback = data.isPlayback;
    let overlay = null, ring = '', extraClass = '';
    if (sim === 'hidden') { overlay = 'versteckt'; ring = 'ring-2 ring-slate-400'; extraClass = 'opacity-40 grayscale'; }
    else if (sim === 'blocked') { overlay = 'blockiert'; ring = 'ring-2 ring-red-500'; }
    else if (sim === 'auto_complete') { overlay = 'auto-abgeschlossen'; ring = 'ring-2 ring-emerald-500'; }
    else if (sim === 'visible') { ring = 'ring-2 ring-teal-400'; }
    if (isPlayback) { ring = 'ring-4 ring-amber-400'; extraClass = `${extraClass} animate-pulse`.trim(); }

    return (
        <div
            className={`rounded-sm shadow-md border-2 min-w-[220px] max-w-[260px] bg-white dark:bg-slate-800 relative ${ring} ${extraClass}`}
            style={{ borderColor: isPlayback ? '#f59e0b' : style.color }}
            data-testid={`flow-node-${data.id}`}
            data-sim-state={sim || 'none'}
            data-playback={isPlayback ? 'true' : 'false'}
        >
            {overlay && (
                <span className="absolute -top-2.5 left-1/2 -translate-x-1/2 px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider bg-slate-800 text-white rounded-sm shadow z-10"
                      data-testid={`sim-badge-${data.id}`}>
                    {overlay}
                </span>
            )}
            <Handle type="target" position={Position.Left} id="in" style={{ background: style.color, width: 10, height: 10 }} />
            <div className="px-3 py-1.5 flex items-center justify-between text-xs font-semibold text-white" style={{ background: style.bg }}>
                <span>#{data.order} · {style.label}</span>
                <div className="flex gap-1">
                    <button onClick={(e) => { e.stopPropagation(); data.onEdit(data.raw); }} className="hover:bg-white/20 rounded p-0.5" data-testid={`flow-edit-${data.id}`} title="Bearbeiten">
                        <Pencil size={12} />
                    </button>
                    <button onClick={(e) => { e.stopPropagation(); data.onDelete(data.raw); }} className="hover:bg-red-500/40 rounded p-0.5" data-testid={`flow-delete-${data.id}`} title="Löschen">
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

// ---- Dagre-based auto layout (fallback, for non-linear graphs) ----
const NODE_W = 240, NODE_H = 88;

function dagreLayout(steps, edges) {
    const g = new dagre.graphlib.Graph();
    g.setGraph({ rankdir: 'LR', nodesep: 60, ranksep: 90, marginx: 20, marginy: 20 });
    g.setDefaultEdgeLabel(() => ({}));
    steps.forEach(s => g.setNode(s.id, { width: NODE_W, height: NODE_H }));
    edges.forEach(e => { if (e.source && e.target && g.hasNode(e.source) && g.hasNode(e.target)) g.setEdge(e.source, e.target); });
    dagre.layout(g);
    const positions = {};
    steps.forEach(s => {
        const n = g.node(s.id);
        if (n) positions[s.id] = { x: n.x - NODE_W / 2, y: n.y - NODE_H / 2 };
    });
    return positions;
}

// ---- Linear layout that respects step.order and renders branch alternatives in parallel lanes ----
// For our Survey v2 pattern:  decision → (upload | partner) → milestone
// Consecutive steps whose hide-condition references the same decision step are
// stacked vertically at the same X column (parallel), then we resume single-line.
function linearLayout(steps) {
    const sorted = [...steps].sort((a, b) => a.order - b.order);
    const positions = {};
    const X_STEP = 280;       // column width
    const Y_CENTER = 140;     // vertical baseline
    const LANE_GAP = 160;     // vertical spacing between parallel lanes
    let x = 20;
    let i = 0;

    while (i < sorted.length) {
        const s = sorted[i];
        // Is this step a conditional alternative branch?
        // Heuristic: it has action='hide' referencing a decision step (field='decision')
        const hideCond = (s.conditions || []).find(
            c => c.action === 'hide' && (c.field === 'decision' || c.operator === 'not_equals' || c.operator === 'equals')
        );

        if (hideCond) {
            const decOrder = hideCond.source_step_order;
            // Group all consecutive steps with a hide-condition referencing the same decision
            const group = [];
            while (i < sorted.length) {
                const cand = sorted[i];
                const candHide = (cand.conditions || []).find(
                    c => c.action === 'hide' && c.source_step_order === decOrder
                );
                if (candHide) {
                    group.push({ step: cand, decision_value: candHide.value || '' });
                    i++;
                } else {
                    break;
                }
            }
            // Sort so 'upload' path stays above 'partner' path consistently
            group.sort((a, b) => (a.decision_value || '').localeCompare(b.decision_value || ''));
            const n = group.length;
            group.forEach((g, idx) => {
                // lanes: idx=0 → top, idx=n-1 → bottom; symmetric around Y_CENTER
                const laneOffset = (idx - (n - 1) / 2) * LANE_GAP;
                positions[g.step.id] = { x, y: Y_CENTER + laneOffset };
            });
            x += X_STEP;
        } else {
            positions[s.id] = { x, y: Y_CENTER };
            x += X_STEP;
            i++;
        }
    }
    return positions;
}

function buildGraph(steps, callbacks) {
    const sorted = [...steps].sort((a, b) => a.order - b.order);
    const byOrder = Object.fromEntries(sorted.map(s => [s.order, s]));

    // First compute raw edges (so dagre can consider them)
    const edges = [];
    sorted.forEach(s => {
        (s.conditions || []).forEach((c, idx) => {
            const src = byOrder[c.source_step_order];
            if (!src) return;
            const action = ACTION_LABELS[c.action] || { label: c.action, color: '#64748b' };
            const valueLabel = c.value ? ` = ${c.value}` : '';
            const fieldLabel = c.field ? `${c.field}` : '(status)';
            edges.push({
                id: `cond-${s.id}-${idx}`,
                source: src.id, target: s.id,
                label: `${action.label}: ${fieldLabel}${valueLabel}`,
                labelStyle: { fontSize: 10, fill: action.color, fontWeight: 600, cursor: 'pointer' },
                labelBgPadding: [4, 2], labelBgBorderRadius: 2,
                labelBgStyle: { fill: 'white', fillOpacity: 0.95, cursor: 'pointer' },
                style: { stroke: action.color, strokeWidth: 1.6, strokeDasharray: c.action === 'hide' ? '4 3' : undefined, cursor: 'pointer' },
                animated: c.action === 'auto_complete',
                markerEnd: { type: MarkerType.ArrowClosed, color: action.color },
                data: { stepId: s.id, condIndex: idx, condition: c, isCondition: true },
            });
        });
    });

    // Positions: use saved flow_position if present; otherwise use the linear (order-based) layout
    const anyWithPosition = sorted.some(s => s.flow_position && typeof s.flow_position.x === 'number');
    let positions = {};
    if (anyWithPosition) {
        sorted.forEach((s, i) => {
            positions[s.id] = s.flow_position || { x: i * 280, y: 140 };
        });
    } else {
        try {
            positions = linearLayout(sorted);
        } catch {
            sorted.forEach((s, i) => { positions[s.id] = { x: i * 280, y: 140 }; });
        }
    }

    const nodes = sorted.map(s => ({
        id: s.id,
        type: 'stepNode',
        position: positions[s.id] || { x: 0, y: 0 },
        data: {
            id: s.id, order: s.order, title: s.title,
            step_type: s.step_type, filter_tag: s.filter_tag,
            duration_value: s.duration_value, duration_unit: s.duration_unit,
            raw: s,
            onEdit: callbacks.onEdit,
            onDelete: callbacks.onDelete,
        },
    }));

    // Sequence arrows between consecutive steps (soft grey, not clickable)
    for (let i = 0; i < sorted.length - 1; i++) {
        const from = sorted[i], to = sorted[i + 1];
        const hasCondEdge = edges.some(e => e.source === from.id && e.target === to.id);
        if (!hasCondEdge) {
            edges.push({
                id: `seq-${from.id}-${to.id}`,
                source: from.id, target: to.id,
                style: { stroke: '#d4d4d8', strokeWidth: 1, strokeDasharray: '2 4' },
                markerEnd: { type: MarkerType.ArrowClosed, color: '#d4d4d8' },
                data: { isCondition: false },
            });
        }
    }
    return { nodes, edges };
}

// ===== Palette sidebar =====
function Palette() {
    const onDragStart = (event, stepType) => {
        event.dataTransfer.setData('application/ihca-step-type', stepType);
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

// ===== Condition creation/edit modal =====
function ConditionModal({ open, mode, source, target, initial, onCancel, onConfirm, onDelete }) {
    const [form, setForm] = useState({ action: 'hide', field: '', operator: 'equals', value: '' });
    useEffect(() => {
        if (open) {
            setForm(initial ? { ...{ action: 'hide', field: '', operator: 'equals', value: '' }, ...initial } : { action: 'hide', field: '', operator: 'equals', value: '' });
        }
    }, [open, initial]);
    if (!open || !source || !target) return null;
    return (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={onCancel}>
            <div className="bg-card border border-border rounded-sm shadow-lg p-6 max-w-md w-full mx-4" onClick={(e) => e.stopPropagation()} data-testid="condition-modal">
                <h3 className="text-lg font-semibold text-foreground mb-1">
                    {mode === 'edit' ? 'Condition bearbeiten' : 'Neue Condition'}
                </h3>
                <p className="text-xs text-muted-foreground mb-4">
                    Von <span className="font-semibold">#{source.order} {source.title}</span> →
                    auf <span className="font-semibold">#{target.order} {target.title}</span>
                </p>
                <div className="space-y-3">
                    <div>
                        <label className="text-xs font-medium text-foreground">Aktion</label>
                        <select value={form.action} onChange={(e) => setForm({ ...form, action: e.target.value })} className="w-full mt-1 px-2 py-1.5 text-sm bg-background border border-border rounded-sm" data-testid="condition-action-select">
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
                            <input type="text" value={form.field} onChange={(e) => setForm({ ...form, field: e.target.value })} placeholder="decision" className="w-full mt-1 px-2 py-1.5 text-sm bg-background border border-border rounded-sm" data-testid="condition-field-input" />
                        </div>
                        <div>
                            <label className="text-xs font-medium text-foreground">Operator</label>
                            <select value={form.operator} onChange={(e) => setForm({ ...form, operator: e.target.value })} className="w-full mt-1 px-2 py-1.5 text-sm bg-background border border-border rounded-sm" data-testid="condition-operator-select">
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
                        <input type="text" value={form.value} onChange={(e) => setForm({ ...form, value: e.target.value })} placeholder="upload" className="w-full mt-1 px-2 py-1.5 text-sm bg-background border border-border rounded-sm" data-testid="condition-value-input" />
                    </div>
                </div>
                <div className="flex gap-2 justify-between mt-5">
                    <div>
                        {mode === 'edit' && (
                            <Button variant="outline" size="sm" onClick={onDelete} className="border-red-200 text-red-600 hover:bg-red-50" data-testid="condition-delete-btn">
                                <Trash size={14} className="mr-1" /> Löschen
                            </Button>
                        )}
                    </div>
                    <div className="flex gap-2">
                        <Button variant="outline" size="sm" onClick={onCancel} data-testid="condition-cancel-btn">Abbrechen</Button>
                        <Button size="sm" onClick={() => onConfirm(form)} className="bg-[#114f55] hover:bg-[#0d3d42] text-white" data-testid="condition-confirm-btn">Speichern</Button>
                    </div>
                </div>
            </div>
        </div>
    );
}

// ===== Inner component with ReactFlow hooks =====
function FlowInner({ steps, onEdit, onDelete, onAddStep, onAddStepWithType, onConditionAdd, onConditionUpdate, onConditionDelete, onSaveLayout }) {
    const callbacks = useMemo(() => ({ onEdit, onDelete }), [onEdit, onDelete]);
    const initial = useMemo(() => buildGraph(steps, callbacks), [steps, callbacks]);
    const [nodes, setNodes, onNodesChange] = useNodesState(initial.nodes);
    const [edges, setEdges, onEdgesChange] = useEdgesState(initial.edges);
    const [modalState, setModalState] = useState(null);
    const [isFullscreen, setIsFullscreen] = useState(false);
    const [simulatorKey, setSimulatorKey] = useState('none');
    const [playbackIndex, setPlaybackIndex] = useState(-1);
    const [playbackStepIds, setPlaybackStepIds] = useState([]);
    const [playbackEtaDays, setPlaybackEtaDays] = useState(0);
    const history = useFlowHistory();
    const flowWrapper = useRef(null);
    const rootRef = useRef(null);
    const { project } = useReactFlow();

    // Snapshot helper — captures current node positions as {id: {x, y}}
    const nodesToSnapshot = useCallback((nds) => {
        const out = {};
        nds.forEach((n) => {
            if (n.position) out[n.id] = { x: n.position.x, y: n.position.y };
        });
        return out;
    }, []);

    // Compute simulator states whenever profile or steps change and decorate nodes
    const simStates = useMemo(() => {
        const profile = SIMULATOR_PROFILES[simulatorKey]?.profile;
        if (!profile) return null;
        const { hidden, blocked, autoComplete } = simulateJourney(steps, profile);
        const map = {};
        steps.forEach((s) => {
            const sid = s.id || s.step_id;
            if (hidden.has(sid)) map[sid] = 'hidden';
            else if (blocked.has(sid)) map[sid] = 'blocked';
            else if (autoComplete.has(sid)) map[sid] = 'auto_complete';
            else map[sid] = 'visible';
        });
        return map;
    }, [simulatorKey, steps]);

    // Track fullscreen state (works for both user-pressed F11-like exit and programmatic)
    useEffect(() => {
        const onFsChange = () => {
            setIsFullscreen(!!document.fullscreenElement);
        };
        document.addEventListener('fullscreenchange', onFsChange);
        return () => document.removeEventListener('fullscreenchange', onFsChange);
    }, []);

    const toggleFullscreen = useCallback(() => {
        const el = rootRef.current;
        if (!el) return;
        if (document.fullscreenElement) {
            document.exitFullscreen?.();
        } else {
            el.requestFullscreen?.().catch(() => { /* browser may block */ });
        }
    }, []);

    useEffect(() => {
        const fresh = buildGraph(steps, callbacks);
        const simMap = simStates;
        const currentPlaybackId = playbackIndex >= 0 ? playbackStepIds[playbackIndex] : null;
        setNodes(fresh.nodes.map((n) => {
            const data = { ...n.data };
            if (simMap) data.simState = simMap[n.id];
            if (currentPlaybackId && n.id === currentPlaybackId) data.isPlayback = true;
            return { ...n, data };
        }));
        setEdges(fresh.edges);
    }, [steps, callbacks, simStates, playbackIndex, playbackStepIds, setNodes, setEdges]);

    // Playback timer — advances one step every 1500ms, accumulating ETA
    useEffect(() => {
        if (playbackIndex < 0 || playbackIndex >= playbackStepIds.length) return undefined;
        const stepId = playbackStepIds[playbackIndex];
        const step = steps.find((s) => (s.id || s.step_id) === stepId);
        const days = step ? durationToDays(step.duration_value, step.duration_unit) : 0;
        const t = setTimeout(() => {
            setPlaybackEtaDays((e) => e + days);
            if (playbackIndex + 1 >= playbackStepIds.length) {
                setPlaybackIndex(-1);
            } else {
                setPlaybackIndex((i) => i + 1);
            }
        }, 1500);
        return () => clearTimeout(t);
    }, [playbackIndex, playbackStepIds, steps]);

    const startPlayback = useCallback(() => {
        const profile = SIMULATOR_PROFILES[simulatorKey]?.profile;
        const simRes = profile ? simulateJourney(steps, profile) : { hidden: new Set() };
        const sorted = [...steps].sort((a, b) => a.order - b.order);
        const visibleIds = sorted
            .filter((s) => !simRes.hidden.has(s.id || s.step_id))
            .map((s) => s.id || s.step_id);
        if (visibleIds.length === 0) return;
        setPlaybackStepIds(visibleIds);
        setPlaybackEtaDays(0);
        setPlaybackIndex(0);
    }, [steps, simulatorKey]);

    const stopPlayback = useCallback(() => {
        setPlaybackIndex(-1);
        setPlaybackStepIds([]);
        setPlaybackEtaDays(0);
    }, []);

    // Reset undo/redo history whenever the underlying step set changes upstream
    useEffect(() => {
        history.clear();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [steps]);

    // Edge drag → open modal (create)
    const handleConnect = useCallback((params) => {
        const source = steps.find(s => s.id === params.source);
        const target = steps.find(s => s.id === params.target);
        if (!source || !target || source.id === target.id) return;
        setModalState({ mode: 'create', source, target, initial: null });
    }, [steps]);

    // Edge click → edit existing condition
    const handleEdgeClick = useCallback((event, edge) => {
        if (!edge?.data?.isCondition) return;
        const source = steps.find(s => s.id === edge.source);
        const target = steps.find(s => s.id === edge.target);
        if (!source || !target) return;
        setModalState({
            mode: 'edit', source, target,
            initial: edge.data.condition,
            edgeData: { stepId: edge.data.stepId, condIndex: edge.data.condIndex },
        });
    }, [steps]);

    // Palette drop → create new step at that position
    const handleDragOver = useCallback((event) => {
        event.preventDefault();
        event.dataTransfer.dropEffect = 'copy';
    }, []);

    const handleDrop = useCallback((event) => {
        event.preventDefault();
        const stepType = event.dataTransfer.getData('application/ihca-step-type');
        if (!stepType) return;
        const bounds = flowWrapper.current.getBoundingClientRect();
        const pos = project({ x: event.clientX - bounds.left, y: event.clientY - bounds.top });
        onAddStepWithType?.(stepType, pos);
    }, [project, onAddStepWithType]);

    // Persist a single node's position when user stops dragging it
    const handleNodeDragStart = useCallback(() => {
        // Snapshot BEFORE the drag mutates positions
        history.push(nodesToSnapshot(nodes));
    }, [history, nodes, nodesToSnapshot]);

    const handleNodeDragStop = useCallback((_event, node) => {
        if (!node?.id || !node.position) return;
        onSaveLayout?.({ [node.id]: { x: node.position.x, y: node.position.y } });
    }, [onSaveLayout]);

    // Apply automatic layout (order-respecting, parallel alternatives) + persist
    const runAutoLayout = useCallback(() => {
        try {
            history.push(nodesToSnapshot(nodes));
            const positions = linearLayout(steps);
            setNodes(nds => nds.map(n => positions[n.id] ? { ...n, position: positions[n.id] } : n));
            onSaveLayout?.(positions);
        } catch (e) { console.warn('Auto-layout failed:', e); }
    }, [steps, setNodes, onSaveLayout, history, nodes, nodesToSnapshot]);

    // ----- Undo / Redo -----
    const applySnapshot = useCallback((snapshot) => {
        if (!snapshot) return;
        setNodes((nds) => nds.map((n) => snapshot[n.id] ? { ...n, position: snapshot[n.id] } : n));
        onSaveLayout?.(snapshot);
    }, [setNodes, onSaveLayout]);

    const handleUndo = useCallback(() => {
        const prev = history.undo(nodesToSnapshot(nodes));
        applySnapshot(prev);
    }, [history, nodes, nodesToSnapshot, applySnapshot]);

    const handleRedo = useCallback(() => {
        const next = history.redo(nodesToSnapshot(nodes));
        applySnapshot(next);
    }, [history, nodes, nodesToSnapshot, applySnapshot]);

    // Keyboard shortcuts: Ctrl/Cmd+Z (undo), Ctrl/Cmd+Shift+Z or Ctrl+Y (redo)
    useEffect(() => {
        const onKey = (e) => {
            const mod = e.ctrlKey || e.metaKey;
            if (!mod) return;
            // Ignore when focus is in an input / textarea / contenteditable
            const tag = (e.target?.tagName || '').toUpperCase();
            if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || e.target?.isContentEditable) return;
            if (e.key === 'z' && !e.shiftKey) { e.preventDefault(); handleUndo(); }
            else if ((e.key === 'z' && e.shiftKey) || e.key === 'y') { e.preventDefault(); handleRedo(); }
        };
        window.addEventListener('keydown', onKey);
        return () => window.removeEventListener('keydown', onKey);
    }, [handleUndo, handleRedo]);

    return (
        <div
            ref={rootRef}
            className={`relative border border-border rounded-sm bg-muted/20 flex ${isFullscreen ? 'h-screen w-screen' : 'h-[640px]'}`}
            data-testid="steps-flow-builder"
        >
            <Palette />
            <div className="flex-1 relative" ref={flowWrapper} onDragOver={handleDragOver} onDrop={handleDrop}>
                <div className="absolute top-3 left-3 z-10 flex gap-2 flex-wrap items-center">
                    <Button size="sm" onClick={() => onAddStep?.()} className="bg-[#114f55] hover:bg-[#0d3d42] text-white shadow" data-testid="flow-add-step-btn">
                        <Plus size={14} className="mr-1" /> Step
                    </Button>
                    <Button size="sm" variant="outline" onClick={runAutoLayout} className="bg-card border-border shadow" data-testid="flow-auto-layout-btn">
                        <Graph size={14} className="mr-1" /> Auto-Layout
                    </Button>
                    <Button size="sm" variant="outline" onClick={toggleFullscreen} className="bg-card border-border shadow" data-testid="flow-fullscreen-btn" title={isFullscreen ? 'Vollbild beenden' : 'Vollbild'}>
                        {isFullscreen ? <ArrowsIn size={14} className="mr-1" /> : <ArrowsOut size={14} className="mr-1" />}
                        {isFullscreen ? 'Vollbild beenden' : 'Vollbild'}
                    </Button>
                    <div className="inline-flex rounded-sm shadow bg-card border border-border overflow-hidden">
                        <button
                            type="button"
                            onClick={handleUndo}
                            disabled={!history.canUndo}
                            title="Rückgängig (Strg+Z)"
                            data-testid="flow-undo-btn"
                            className="px-2 py-1.5 text-xs text-foreground hover:bg-muted disabled:opacity-40 disabled:cursor-not-allowed border-r border-border flex items-center gap-1"
                        >
                            <ArrowUUpLeft size={14} /> Undo
                        </button>
                        <button
                            type="button"
                            onClick={handleRedo}
                            disabled={!history.canRedo}
                            title="Wiederherstellen (Strg+Shift+Z)"
                            data-testid="flow-redo-btn"
                            className="px-2 py-1.5 text-xs text-foreground hover:bg-muted disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1"
                        >
                            <ArrowUUpRight size={14} /> Redo
                        </button>
                    </div>
                    <FlowSimulatorPanel value={simulatorKey} onChange={setSimulatorKey} />
                    <Button
                        size="sm"
                        variant="outline"
                        onClick={playbackIndex >= 0 ? stopPlayback : startPlayback}
                        className={`shadow ${playbackIndex >= 0 ? 'bg-amber-50 border-amber-300 text-amber-900 hover:bg-amber-100' : 'bg-card border-border'}`}
                        data-testid="flow-playback-btn"
                        title={playbackIndex >= 0 ? 'Abspielen stoppen' : 'Animierten Durchlauf starten'}
                    >
                        {playbackIndex >= 0
                            ? (<><Stop size={14} className="mr-1" weight="fill" /> Stop</>)
                            : (<><Play size={14} className="mr-1" weight="fill" /> Abspielen</>)}
                    </Button>
                </div>
                {playbackIndex >= 0 && (
                    <div
                        className="absolute bottom-14 left-1/2 -translate-x-1/2 z-10 bg-amber-50 dark:bg-amber-900/70 border border-amber-300 dark:border-amber-700 rounded-sm shadow-lg px-4 py-2 text-xs flex items-center gap-4"
                        data-testid="flow-playback-status"
                    >
                        <span className="font-semibold text-amber-900 dark:text-amber-100">
                            ▶ Step {playbackIndex + 1} / {playbackStepIds.length}
                        </span>
                        <span className="text-amber-800 dark:text-amber-200">
                            ETA: <span className="font-semibold" data-testid="flow-playback-eta">{formatDays(playbackEtaDays)}</span>
                        </span>
                        <button
                            type="button"
                            onClick={stopPlayback}
                            className="text-[11px] text-amber-900 dark:text-amber-100 underline hover:no-underline"
                            data-testid="flow-playback-stop-btn"
                        >
                            Stoppen
                        </button>
                    </div>
                )}
                <div className="absolute top-3 right-3 z-10 flex flex-wrap gap-2 max-w-[60%] justify-end pointer-events-none">
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
                    onEdgeClick={handleEdgeClick}
                    onNodeDragStart={handleNodeDragStart}
                    onNodeDragStop={handleNodeDragStop}
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
                open={!!modalState}
                mode={modalState?.mode}
                source={modalState?.source}
                target={modalState?.target}
                initial={modalState?.initial}
                onCancel={() => setModalState(null)}
                onConfirm={(form) => {
                    if (modalState.mode === 'edit') {
                        onConditionUpdate?.(modalState.edgeData.stepId, modalState.edgeData.condIndex, { ...modalState.initial, ...form });
                    } else {
                        onConditionAdd?.(modalState.source, modalState.target, form);
                    }
                    setModalState(null);
                }}
                onDelete={() => {
                    onConditionDelete?.(modalState.edgeData.stepId, modalState.edgeData.condIndex);
                    setModalState(null);
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
