import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../services/api'

const STATUS_COLOR  = { completed: 'var(--text-bright)', processing: 'var(--text-sub)', failed: 'var(--danger)', created: 'var(--border-hi)' }
const PIPELINE_DEFS = [
    { key: 'perception',       label: 'L1 · PERCEPTION',        desc: 'Classification & OCR' },
    { key: 'extraction',       label: 'L2 · EXTRACTION',        desc: 'Table parsing & NER' },
    { key: 'normalization',    label: 'L3 · NORMALIZATION',     desc: 'Ratio computation' },
    { key: 'cross_validation', label: 'L4 · CROSS-VALIDATION',  desc: 'GST ↔ Bank reconcile' },
    { key: 'fraud_detection',  label: 'L5 · FRAUD + EWS',       desc: 'Circular trading · 15 flags' },
]

export default function DashboardPage() {
    const navigate  = useNavigate()
    const [cases,   setCases]   = useState([])
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        api.get('/cases/')
            .then(r => setCases(r.data.cases || []))
            .catch(() => {})
            .finally(() => setLoading(false))
    }, [])

    const totalCases  = cases.length
    const completed   = cases.filter(c => c.status === 'completed').length
    const processing  = cases.filter(c => c.status === 'processing' || c.status === 'uploading').length
    const failed      = cases.filter(c => c.status === 'failed').length
    const recentCases = cases.slice(0, 7)

    return (
        <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '32px' }}>

            {/* ── Page title ── */}
            <div style={{ marginBottom: '40px', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', borderBottom: '1px solid var(--border-dim)', paddingBottom: '32px' }}>
                <div>
                    <p style={{ fontSize: '0.65rem', letterSpacing: '4px', color: 'var(--text-muted)', marginBottom: '12px', textTransform: 'uppercase', fontWeight: 600 }}>Corporate Credit Appraisal Engine</p>
                    <h1 style={{ fontSize: '2.4rem', margin: 0 }}>COMMAND CENTER</h1>
                </div>
                <button
                    className="btn-primary"
                    onClick={() => navigate('/cases/new')}
                    style={{ padding: '15px 36px', fontSize: '0.8rem' }}
                >
                    + NEW APPRAISAL
                </button>
            </div>

            {/* ── KPI band ── */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '8px', marginBottom: '28px' }}>
                {[
                    { label: 'Total Cases',     value: totalCases, sub: 'all time' },
                    { label: 'Completed',        value: completed,  sub: 'analysed', color: completed > 0 ? '#f0f0f0' : '#333' },
                    { label: 'In Pipeline',      value: processing, sub: 'running now', color: processing > 0 ? '#888' : '#333' },
                    { label: 'Failed / Error',   value: failed,     sub: 'need review', color: failed > 0 ? '#ff4444' : '#333' },
                ].map((k, i) => (
                    <div key={i} className="kpi-cell" style={{ padding: '28px' }}>
                        <p style={{ fontSize: '0.65rem', color: 'var(--text-muted)', letterSpacing: '3px', textTransform: 'uppercase', marginBottom: '16px', fontWeight: 600 }}>{k.label}</p>
                        <p style={{ fontSize: '2.5rem', fontWeight: 900, lineHeight: 1, color: k.color || 'var(--text-bright)', marginBottom: '8px' }}>{k.value}</p>
                        <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 500 }}>{k.sub}</p>
                    </div>
                ))}
            </div>

            {/* ── Main grid ── */}
            <div style={{ display: 'grid', gridTemplateColumns: '1.7fr 1fr', gap: '20px' }}>

                {/* ── Recent cases (left) ── */}
                <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
                    <div style={{ padding: '18px 24px', borderBottom: '1px solid var(--border-dim)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'var(--bg-nav)' }}>
                        <span className="overline" style={{ fontSize: '0.8rem', color: 'var(--text-main)' }}>Recent Appraisals</span>
                        <button
                            onClick={() => navigate('/cases')}
                            style={{ fontSize: '0.68rem', padding: '6px 16px' }}
                            className="btn-ghost"
                        >
                            ALL CASES →
                        </button>
                    </div>

                    {loading ? (
                        <div style={{ padding: '80px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.9rem', letterSpacing: '1px' }}>
                            SCRUTINIZING DATA PIPELINES...
                        </div>
                    ) : recentCases.length === 0 ? (
                        <div style={{ padding: '100px 30px', textAlign: 'center' }}>
                            <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginBottom: '24px', textTransform: 'uppercase', letterSpacing: '2px' }}>No cases identified</p>
                            <button className="btn-primary" onClick={() => navigate('/cases/new')} style={{ padding: '15px 32px' }}>
                                START FIRST APPRAISAL
                            </button>
                        </div>
                    ) : recentCases.map((c, i) => {
                        const pipeline = c.pipeline_status || {}
                        const done  = Object.values(pipeline).filter(v => v === 'done').length
                        const total = Object.keys(pipeline).length || 5
                        const sc    = STATUS_COLOR[c.status] || 'var(--border-hi)'
                        const pct   = Math.round((done / total) * 100)
                        return (
                            <div
                                key={i}
                                onClick={() => navigate(
                                    c.status === 'completed'
                                        ? `/cases/${c.case_id}/results`
                                        : `/cases/${c.case_id}/processing`
                                )}
                                style={{
                                    padding: '24px 28px',
                                    borderBottom: '1px solid var(--border-dim)',
                                    cursor: 'pointer',
                                    display: 'grid',
                                    gridTemplateColumns: '1.6fr 90px 110px',
                                    gap: '20px',
                                    alignItems: 'center',
                                    transition: 'background 0.15s',
                                }}
                                onMouseEnter={e => e.currentTarget.style.background = 'var(--bg-raised)'}
                                onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                            >
                                {/* Name + meta */}
                                <div>
                                    <div style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--text-bright)', marginBottom: '6px' }}>
                                        {c.company_name || 'UNNAMED ENTITY'}
                                    </div>
                                    <div style={{ fontSize: '0.75rem', color: 'var(--text-sub)', letterSpacing: '0.5px', fontWeight: 500 }}>
                                        {c.sector ? `${c.sector.toUpperCase()} · ` : ''}{c.case_id.slice(0, 8).toUpperCase()}
                                        {c.loan_amount_cr ? ` · ₹${c.loan_amount_cr}CR` : ''}
                                    </div>
                                </div>
                                {/* Pipeline progress */}
                                <div>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                                        <span style={{ fontSize: '0.65rem', color: 'var(--text-muted)', fontWeight: 700, letterSpacing: '1px' }}>FLOW</span>
                                        <span style={{ fontSize: '0.65rem', color: 'var(--text-sub)', fontWeight: 700 }}>{pct}%</span>
                                    </div>
                                    <div className="progress-track" style={{ height: '6px' }}>
                                        <div className="progress-fill" style={{ width: `${pct}%`, background: sc }} />
                                    </div>
                                </div>
                                {/* Status badge */}
                                <div style={{ textAlign: 'right' }}>
                                    <span className={`badge ${c.status === 'completed' ? 'badge-success' : c.status === 'failed' ? 'badge-danger' : 'badge-muted'}`} style={{ fontSize: '0.68rem', padding: '6px 14px' }}>
                                        {c.status.toUpperCase()}
                                    </span>
                                </div>
                            </div>
                        )
                    })}
                </div>

                {/* ── Right column ── */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>

                    {/* Quick actions */}
                    <div className="card" style={{ padding: 0 }}>
                        <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border-dim)', background: 'var(--bg-nav)' }}>
                            <span className="overline" style={{ fontSize: '0.75rem', color: 'var(--text-main)' }}>Direct Access</span>
                        </div>
                        <div style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                            <button className="btn-primary" onClick={() => navigate('/cases/new')} style={{ width: '100%', padding: '16px', fontSize: '0.85rem' }}>
                                + NEW CREDIT APPRAISAL
                            </button>
                            <button className="btn-ghost" onClick={() => navigate('/cases')} style={{ width: '100%', padding: '14px', fontSize: '0.78rem' }}>
                                VIEW FULL ARCHIVE
                            </button>
                        </div>
                    </div>

                    {/* Pipeline architecture */}
                    <div className="card" style={{ padding: 0 }}>
                        <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border-dim)', background: 'var(--bg-nav)' }}>
                            <span className="overline" style={{ fontSize: '0.75rem', color: 'var(--text-main)' }}>Intelligence Stack</span>
                        </div>
                        <div style={{ padding: '12px 0' }}>
                            {PIPELINE_DEFS.map((step, i) => (
                                <div key={i} style={{ padding: '16px 22px', borderBottom: i < 4 ? '1px solid var(--border-dim)' : 'none', display: 'flex', alignItems: 'center', gap: '16px' }}>
                                    <div style={{ width: '8px', height: '8px', background: 'var(--border-hi)', flexShrink: 0 }} />
                                    <div>
                                        <div style={{ fontSize: '0.82rem', fontWeight: 700, letterSpacing: '0.5px', color: 'var(--text-main)', marginBottom: '4px' }}>{step.label}</div>
                                        <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 500 }}>{step.desc}</div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* Hackathon criteria */}
                    <div className="card" style={{ padding: 0 }}>
                        <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border-dim)', background: 'var(--bg-nav)' }}>
                            <span className="overline" style={{ fontSize: '0.75rem', color: 'var(--text-main)' }}>Hackathon Compliance</span>
                        </div>
                        <div style={{ padding: '10px 0' }}>
                            {[
                                'Extraction Accuracy',
                                'Research Depth',
                                'Explainability (SHAP)',
                                'Indian Context Sensitivity',
                                'Operational Excellence',
                            ].map((label, i) => (
                                <div key={i} style={{ padding: '14px 22px', borderBottom: i < 4 ? '1px solid var(--border-dim)' : 'none', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                    <span style={{ fontSize: '0.78rem', color: 'var(--text-sub)', fontWeight: 500 }}>{label}</span>
                                    <span style={{ fontSize: '0.7rem', color: 'var(--success)', fontWeight: 800, letterSpacing: '0.5px', background: 'rgba(63, 222, 127, 0.1)', padding: '4px 10px', border: '1px solid rgba(63, 222, 127, 0.2)' }}>COVERED</span>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    )
}
