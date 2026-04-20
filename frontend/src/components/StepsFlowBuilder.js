import { useState, useMemo, useCallback, useEffect } from 'react';
import ReactFlow, {
    Background, Controls, Handle, Position, MiniMap,
    useNodesState, useEdgesState, MarkerType,
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
            <Handle type="target" position={Position.Left} style={{ background: style.color }} />
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
            <Handle type="source" position={Position.Right} style={{ background: style.color }} />
        </div>
    );
}

const nodeTypes = { stepNode: StepNode };

function buildGraph(steps, callbacks) {
    const sorted = [...steps].sort((a, b) => a.order - b.order);
    const byOrder = Object.fromEntries(sorted.map(s => [s.order, s]));

    // Nodes – horizontally laid out by order, vertically shifted for same block
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

    // Edges – conditions point from source_step_order → this step
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
                labelBgPadding: [4, 2],
                labelBgBorderRadius: 2,
                labelBgStyle: { fill: 'white', fillOpacity: 0.95 },
                style: { stroke: action.color, strokeWidth: 1.6, strokeDasharray: c.action === 'hide' ? '4 3' : undefined },
                animated: c.action === 'auto_complete',
                markerEnd: { type: MarkerType.ArrowClosed, color: action.color },
            });
        }
    });

    // Also draw soft sequence arrows between consecutive visible steps (no condition)
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

export default function StepsFlowBuilder({ steps, onEdit, onDelete, onAddStep }) {
    const callbacks = useMemo(() => ({ onEdit, onDelete }), [onEdit, onDelete]);
    const initial = useMemo(() => buildGraph(steps, callbacks), [steps, callbacks]);
    const [nodes, setNodes, onNodesChange] = useNodesState(initial.nodes);
    const [edges, setEdges, onEdgesChange] = useEdgesState(initial.edges);

    // Rebuild on steps change
    useEffect(() => {
        const fresh = buildGraph(steps, callbacks);
        setNodes(fresh.nodes);
        setEdges(fresh.edges);
    }, [steps, callbacks, setNodes, setEdges]);

    return (
        <div className="relative h-[640px] border border-border rounded-sm bg-muted/20" data-testid="steps-flow-builder">
            <div className="absolute top-3 left-3 z-10 flex gap-2">
                <Button size="sm" onClick={() => onAddStep?.()} className="bg-[#114f55] hover:bg-[#0d3d42] text-white shadow" data-testid="flow-add-step-btn">
                    <Plus size={14} className="mr-1" /> Step hinzufügen
                </Button>
            </div>
            <div className="absolute top-3 right-3 z-10 flex flex-wrap gap-2 max-w-[60%] justify-end">
                {Object.entries(TYPE_STYLES).map(([k, v]) => (
                    <span key={k} className="inline-flex items-center gap-1 px-2 py-0.5 text-[10px] bg-white dark:bg-slate-800 border border-border rounded-sm shadow-sm">
                        <span className="w-2 h-2 rounded-sm" style={{ background: v.bg }} />
                        {v.label}
                    </span>
                ))}
            </div>
            <ReactFlow
                nodes={nodes} edges={edges}
                onNodesChange={onNodesChange} onEdgesChange={onEdgesChange}
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
    );
}
