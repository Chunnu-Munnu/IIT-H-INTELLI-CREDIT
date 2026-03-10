import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../services/api'

const SC = {
    created:    { label: 'CREATED',    color: '#555',    bg: '#111',    dot: '#333' },
    uploading:  { label: 'UPLOADING',  color: '#888',    bg: '#111',    dot: '#666' },
    processing: { label: 'PROCESSING', color: '#aaa',    bg: '#141414', dot: '#888' },
    completed:  { label: 'COMPLETED',  color: '#f0f0f0', bg: '#141414', dot: '#f0f0f0' },
    failed:     { label: 'FAILED',     color: '#ff4444', bg: '#140000', dot: '#ff4444' },
}

const fmt = iso => iso ? new Date(iso).toLocaleString('en-IN', { day:'2-digit', month:'short', year:'numeric', hour:'2-digit', minute:'2-digit' }) : '—'

export default function CasesPage() {
    const navigate = useNavigate()
    const [cases,   setCases]   = useState([])
    const [loading, setLoading] = useState(true)
    const [filter,  setFilter]  = useState('ALL')

    useEffect(() => {
        const load = () =>
            api.get('/cases/')
               .then(r => setCases(r.data.cases || []))
               .catch(() => {})
               .finally(() => setLoading(false))
        load()
        const iv = setInterval(load, 10000)
        return () => clearInterval(iv)
    }, [])

    const statuses = ['ALL', 'processing', 'completed', 'failed']
    const filtered = filter === 'ALL' ? cases : cases.filter(c => c.status === filter)
    const goToCase = c => navigate(
        c.status === 'completed' ? `/cases/${c.case_id}/results` : `/cases/${c.case_id}/processing`
    )

    return (
        <div style={{ maxWidth: '1100px', margin: '0 auto', padding: '30px 32px' }}>

            {/* ── Page header ── */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginBottom: '28px', paddingBottom: '20px', borderBottom: '1px solid #1c1c1c' }}>
                <div>
                    <p style={{ fontSize: '0.5rem', color: '#444', letterSpacing: '3px', marginBottom: '6px', textTransform: 'uppercase' }}>Case Management</p>
                    <h1 style={{ margin: 0 }}>ARCHIVE</h1>
                </div>
                <button className="btn-primary" onClick={() => navigate('/cases/new')} style={{ padding: '11px 24px', fontSize: '0.62rem' }}>
                    + NEW APPRAISAL
                </button>
            </div>

            {/* ── Filter bar ── */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '0', borderBottom: '1px solid #1c1c1c', marginBottom: '24px' }}>
                {statuses.map(s => {
                    const active = filter === s
                    const count = s === 'ALL' ? cases.length : cases.filter(c => c.status === s).length
                    return (
                        <button key={s} onClick={() => setFilter(s)} style={{
                            padding: '10px 20px',
                            fontSize: '0.56rem',
                            letterSpacing: '1.5px',
                            background: active ? '#f0f0f0' : 'transparent',
                            color: active ? '#000' : '#444',
                            border: 'none',
                            borderBottom: active ? '2px solid #f0f0f0' : '2px solid transparent',
                            fontWeight: active ? 800 : 400,
                            cursor: 'pointer',
                        }}>
                            {s.toUpperCase()} <span style={{ opacity: 0.5, fontSize: '0.48rem' }}>({count})</span>
                        </button>
                    )
                })}
                <span style={{ marginLeft: 'auto', fontSize: '0.52rem', color: '#333', paddingRight: '4px' }}>
                    {filtered.length} CASE{filtered.length !== 1 ? 'S' : ''}
                </span>
            </div>

            {/* ── Content ── */}
            {loading ? (
                <div style={{ textAlign: 'center', padding: '80px', color: '#333', fontSize: '0.7rem' }}>
                    FETCHING CASE ARCHIVE...
                </div>
            ) : filtered.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '80px', background: '#0d0d0d', border: '1px solid #1c1c1c' }}>
                    <p style={{ color: '#444', fontSize: '0.8rem', marginBottom: '20px', textTransform: 'uppercase', letterSpacing: '3px' }}>
                        {filter === 'ALL' ? 'No cases in archive' : `No ${filter} cases`}
                    </p>
                    <button className="btn-primary" onClick={() => navigate('/cases/new')} style={{ padding: '11px 28px' }}>
                        + INITIATE FIRST APPRAISAL
                    </button>
                </div>
            ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    {filtered.map((c, i) => {
                        const cfg    = SC[c.status] || SC.created
                        const pip    = c.pipeline_status || {}
                        const done   = Object.values(pip).filter(v => v === 'done').length
                        const total  = Object.keys(pip).length || 5
                        const pct    = Math.round((done / total) * 100)

                        return (
                            <div
                                key={c.case_id}
                                onClick={() => goToCase(c)}
                                style={{
                                    background: '#0d0d0d',
                                    border: '1px solid #1e1e1e',
                                    padding: '16px 20px',
                                    display: 'grid',
                                    gridTemplateColumns: '8px 1fr 90px 90px 90px 100px 90px',
                                    gap: '16px',
                                    alignItems: 'center',
                                    cursor: 'pointer',
                                    transition: 'background 0.1s, border-color 0.1s',
                                }}
                                onMouseEnter={e => { e.currentTarget.style.background = '#141414'; e.currentTarget.style.borderColor = '#2d2d2d' }}
                                onMouseLeave={e => { e.currentTarget.style.background = '#0d0d0d'; e.currentTarget.style.borderColor = '#1e1e1e' }}
                            >
                                {/* Status dot */}
                                <div style={{ width: '6px', height: '6px', background: cfg.dot, flexShrink: 0, alignSelf: 'center' }} />

                                {/* Company + ID */}
                                <div style={{ minWidth: 0 }}>
                                    <div style={{ fontSize: '0.78rem', fontWeight: 600, color: '#ddd', marginBottom: '3px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                        {c.company_name || 'UNNAMED ENTITY'}
                                    </div>
                                    <div style={{ fontSize: '0.5rem', color: '#3a3a3a', fontFamily: 'monospace' }}>
                                        {c.case_id.slice(0, 12).toUpperCase()} {c.company_cin ? `· ${c.company_cin}` : ''}
                                    </div>
                                </div>

                                {/* Sector */}
                                <div style={{ textAlign: 'center' }}>
                                    <div style={{ fontSize: '0.48rem', color: '#3a3a3a', marginBottom: '2px', letterSpacing: '1px' }}>SECTOR</div>
                                    <div style={{ fontSize: '0.6rem', color: '#777' }}>{c.sector || '—'}</div>
                                </div>

                                {/* Loan amount */}
                                <div style={{ textAlign: 'center' }}>
                                    <div style={{ fontSize: '0.48rem', color: '#3a3a3a', marginBottom: '2px', letterSpacing: '1px' }}>LOAN</div>
                                    <div style={{ fontSize: '0.65rem', fontWeight: 700, color: '#aaa' }}>{c.loan_amount_cr ? `₹${c.loan_amount_cr}Cr` : '—'}</div>
                                </div>

                                {/* Pipeline */}
                                <div>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                                        <span style={{ fontSize: '0.46rem', color: '#333' }}>PIPELINE</span>
                                        <span style={{ fontSize: '0.46rem', color: '#444' }}>{pct}%</span>
                                    </div>
                                    <div className="progress-track">
                                        <div className="progress-fill" style={{ width: `${pct}%`, background: cfg.dot }} />
                                    </div>
                                </div>

                                {/* Date */}
                                <div style={{ textAlign: 'right' }}>
                                    <div style={{ fontSize: '0.52rem', color: '#3a3a3a' }}>{fmt(c.created_at)}</div>
                                </div>

                                {/* Status badge */}
                                <div style={{ textAlign: 'center' }}>
                                    <span style={{
                                        fontSize: '0.5rem',
                                        letterSpacing: '0.5px',
                                        border: `1px solid ${cfg.color}30`,
                                        color: cfg.color,
                                        padding: '3px 8px',
                                        background: `${cfg.color}0a`,
                                        display: 'inline-block',
                                    }}>
                                        {cfg.label}
                                    </span>
                                </div>
                            </div>
                        )
                    })}
                </div>
            )}
        </div>
    )
}
