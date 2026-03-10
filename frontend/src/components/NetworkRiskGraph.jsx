import { useEffect, useState, useCallback } from 'react'
import ReactFlow, {
    Background, Controls, MiniMap,
    addEdge, useNodesState, useEdgesState,
} from 'reactflow'
import 'reactflow/dist/style.css'

const NODE_COLORS = {
    subject: { bg: '#1e40af', border: '#3b82f6', text: '#ffffff' },
    buyer: { bg: '#065f46', border: '#10b981', text: '#ffffff' },
    supplier: { bg: '#7c3aed', border: '#a78bfa', text: '#ffffff' },
    director: { bg: '#92400e', border: '#fbbf24', text: '#ffffff' },
    lender: { bg: '#991b1b', border: '#ef4444', text: '#ffffff' },
    related_party: { bg: '#374151', border: '#6b7280', text: '#d1d5db' },
}

const EDGE_COLORS = {
    SUPPLIES_TO: '#10b981',
    BUYS_FROM: '#a78bfa',
    DIRECTOR_OF: '#fbbf24',
    BORROWS_FROM: '#ef4444',
    OWNS: '#6b7280',
}

function buildReactFlowData(graphData) {
    if (!graphData?.nodes) return { nodes: [], edges: [] }

    const nodeMap = {}
    graphData.nodes.forEach((n, i) => {
        const colors = NODE_COLORS[n.type] || NODE_COLORS.related_party
        const angle = (i / graphData.nodes.length) * 2 * Math.PI
        const r = n.is_subject ? 0 : 280
        nodeMap[n.id] = {
            id: n.id,
            data: { label: n.name || n.id, type: n.type },
            position: {
                x: 400 + r * Math.cos(angle),
                y: 300 + r * Math.sin(angle),
            },
            style: {
                background: colors.bg,
                border: `2px solid ${colors.border}`,
                color: colors.text,
                borderRadius: 8,
                padding: '6px 10px',
                fontSize: 11,
                fontWeight: n.is_subject ? 700 : 400,
                minWidth: n.is_subject ? 120 : 80,
                textAlign: 'center',
                boxShadow: n.is_subject ? `0 0 20px ${colors.border}66` : 'none',
            },
        }
    })

    const edges = (graphData.edges || []).map((e, i) => ({
        id: `e-${i}`,
        source: e.source,
        target: e.target,
        label: e.type,
        labelStyle: { fill: '#94a3b8', fontSize: 9 },
        style: {
            stroke: EDGE_COLORS[e.type] || '#475569',
            strokeWidth: 1.5,
            opacity: 0.7,
        },
        markerEnd: { type: 'arrowclosed', color: EDGE_COLORS[e.type] || '#475569' },
        animated: e.type === 'BORROWS_FROM',
    }))

    return { nodes: Object.values(nodeMap), edges }
}

export default function NetworkRiskGraph({ graphData, networkScores }) {
    const flowData = buildReactFlowData(graphData)
    const [nodes, setNodes, onNodesChange] = useNodesState(flowData.nodes)
    const [edges, setEdges, onEdgesChange] = useEdgesState(flowData.edges)

    useEffect(() => {
        const d = buildReactFlowData(graphData)
        setNodes(d.nodes)
        setEdges(d.edges)
    }, [graphData])

    if (!graphData?.nodes?.length) {
        return (
            <div className="card p-8 text-center text-slate-500">
                <p>No corporate relationship graph available.</p>
                <p className="text-xs mt-1">Graph requires GST data with buyer/supplier lists.</p>
            </div>
        )
    }

    return (
        <div className="card overflow-hidden">
            {/* Scores */}
            {networkScores && (
                <div className="grid grid-cols-4 gap-3 p-4 border-b border-slate-800">
                    {[
                        { label: 'Network Risk', value: networkScores.network_risk_score, warn: true },
                        { label: 'Supplier Risk', value: networkScores.supplier_default_risk, warn: true },
                        { label: 'Promoter Risk', value: networkScores.promoter_network_risk, warn: true },
                        { label: 'Group Risk', value: networkScores.group_company_default_risk, warn: true },
                    ].map(({ label, value, warn }) => {
                        const v = parseFloat(value || 0)
                        const color = v > 7 ? 'text-red-400' : v > 4 ? 'text-amber-400' : 'text-emerald-400'
                        return (
                            <div key={label} className="text-center">
                                <div className={`text-2xl font-black ${color}`}>{v.toFixed(1)}<span className="text-slate-500 text-sm">/10</span></div>
                                <div className="text-xs text-slate-400">{label}</div>
                            </div>
                        )
                    })}
                </div>
            )}

            {/* Legend */}
            <div className="flex flex-wrap gap-3 px-4 py-2 border-b border-slate-800">
                {Object.entries(NODE_COLORS).map(([type, colors]) => (
                    <span key={type} className="flex items-center gap-1 text-xs text-slate-400">
                        <span className="w-3 h-3 rounded-sm" style={{ background: colors.bg, border: `1px solid ${colors.border}` }} />
                        {type.replace('_', ' ')}
                    </span>
                ))}
            </div>

            {/* Graph */}
            <div style={{ height: 480 }}>
                <ReactFlow
                    nodes={nodes} edges={edges}
                    onNodesChange={onNodesChange}
                    onEdgesChange={onEdgesChange}
                    fitView
                    attributionPosition="bottom-right"
                >
                    <Background color="#1e293b" gap={20} />
                    <Controls style={{ background: '#0f172a', border: '1px solid #1e293b' }} />
                    <MiniMap
                        nodeColor={n => NODE_COLORS[n.data?.type]?.bg || '#374151'}
                        style={{ background: '#0f172a', border: '1px solid #1e293b' }}
                    />
                </ReactFlow>
            </div>
        </div>
    )
}
