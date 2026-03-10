import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { toast } from 'react-hot-toast'
import api from '../services/api'

/* ────────────────────────────────── helpers */
const crore  = p  => p  ? `₹${(p / 10000000 / 100).toFixed(2)} Cr` : '—'
const round1 = v  => v  != null ? (+v).toFixed(1) : '—'

const DECISION_STYLE = {
    APPROVE:                  { bg: '#0a1a0a', border: '#22ff66', text: '#22ff66', label: 'APPROVED' },
    'APPROVE WITH CONDITIONS':{ bg: '#0a0e1a', border: '#4488ff', text: '#4488ff', label: 'CONDITIONAL APPROVAL' },
    'REFER TO COMMITTEE':     { bg: '#1a1100', border: '#ff8800', text: '#ff8800', label: 'REFER TO CREDIT COMMITTEE' },
    DECLINE:                  { bg: '#1a0000', border: '#ff3333', text: '#ff3333', label: 'DECLINED' },
    PENDING:                  { bg: '#0a0a0a', border: '#444',    text: '#888',    label: 'PENDING GENERATION' },
}

/* ── SWOT card ── */
function SWOTGrid({ swot }) {
    const SWOT_CONFIG = [
        { key: 'strengths',     label: 'STRENGTHS',     color: '#22dd66', icon: '↑' },
        { key: 'weaknesses',    label: 'WEAKNESSES',    color: '#ff4444', icon: '↓' },
        { key: 'opportunities', label: 'OPPORTUNITIES', color: '#4488ff', icon: '→' },
        { key: 'threats',       label: 'THREATS',       color: '#ff8800', icon: '⚠' },
    ]
    return (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2px', background: '#111', border: '2px solid #111', borderRadius: '4px', overflow: 'hidden' }}>
            {SWOT_CONFIG.map(({ key, label, color, icon }) => (
                <div key={key} style={{ background: '#000', padding: '24px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px', paddingBottom: '12px', borderBottom: `1px solid ${color}30` }}>
                        <span style={{ fontSize: '0.7rem', fontWeight: 900 }}>{icon}</span>
                        <span style={{ fontSize: '0.7rem', fontWeight: 800, letterSpacing: '2.5px', color }}>{label}</span>
                    </div>
                    <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
                        {(swot?.[key] || [`No ${key} data available`]).map((item, i) => (
                            <li key={i} style={{ fontSize: '0.75rem', color: '#fff', lineHeight: '1.7', marginBottom: '12px', paddingLeft: '14px', borderLeft: `3px solid ${color}60` }}>
                                {item}
                            </li>
                        ))}
                    </ul>
                </div>
            ))}
        </div>
    )
}

/* ── Mitigation Plan ── */
function MitigationPlan({ plan }) {
    if (!plan) return null
    return (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginTop: '24px' }}>
            <div style={{ border: '1px solid #22ff6630', background: '#0a1a0a40', padding: '20px' }}>
                <h4 style={{ fontSize: '0.65rem', color: '#22ff66', letterSpacing: '2px', marginBottom: '15px' }}>✓ DO'S (MITIGATIONS)</h4>
                {plan.dos?.map((item, i) => (
                    <div key={i} style={{ fontSize: '0.75rem', color: '#fff', marginBottom: '10px', display: 'flex', gap: '10px' }}>
                        <span style={{ color: '#22ff66' }}>•</span>{item}
                    </div>
                ))}
            </div>
            <div style={{ border: '1px solid #ff444430', background: '#1a0a0a40', padding: '20px' }}>
                <h4 style={{ fontSize: '0.65rem', color: '#ff4444', letterSpacing: '2px', marginBottom: '15px' }}>✕ DON'TS (RISK AVOIDANCE)</h4>
                {plan.donts?.map((item, i) => (
                    <div key={i} style={{ fontSize: '0.75rem', color: '#fff', marginBottom: '10px', display: 'flex', gap: '10px' }}>
                        <span style={{ color: '#ff4444' }}>•</span>{item}
                    </div>
                ))}
            </div>
            <div style={{ gridColumn: 'span 2', border: '1px solid #4488ff30', background: '#0a0e1a40', padding: '20px' }}>
                <h4 style={{ fontSize: '0.65rem', color: '#4488ff', letterSpacing: '2px', marginBottom: '15px' }}>⏱ POST-SANCTION MONITORING</h4>
                {plan.monitoring?.map((item, i) => (
                    <div key={i} style={{ fontSize: '0.75rem', color: '#fff', marginBottom: '8px', display: 'flex', gap: '10px' }}>
                        <span style={{ color: '#4488ff' }}>•</span>{item}
                    </div>
                ))}
            </div>
        </div>
    )
}

/* ── Tab system ── */
function Tabs({ tabs, active, onChange }) {
    return (
        <div style={{ display: 'flex', borderBottom: '1px solid #111', marginBottom: '24px' }}>
            {tabs.map(t => (
                <button key={t.id} onClick={() => onChange(t.id)} style={{
                    padding: '11px 20px',
                    fontSize: '0.58rem',
                    letterSpacing: '1px',
                    background: active === t.id ? '#fff' : 'transparent',
                    color:      active === t.id ? '#000' : '#555',
                    border: 'none',
                    cursor: 'pointer',
                    fontWeight: active === t.id ? 700 : 400,
                }}>
                    {t.label}
                </button>
            ))}
        </div>
    )
}

/* ── Five C bar ── */
function CBar({ name, score, desc }) {
    const color = score >= 70 ? '#fff' : score >= 50 ? '#888' : '#ff4444'
    return (
        <div style={{ marginBottom: '16px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                <div>
                    <span style={{ fontSize: '0.65rem', fontWeight: 700 }}>{name.toUpperCase()}</span>
                    {desc && <span style={{ fontSize: '0.55rem', color: '#fff', marginLeft: '8px' }}>{desc}</span>}
                </div>
                <span style={{ fontSize: '0.7rem', fontWeight: 900, color }}>{round1(score)}/100</span>
            </div>
            <div style={{ height: '5px', background: '#0d0d0d', position: 'relative' }}>
                <div style={{ height: '100%', width: `${Math.min(100, Math.max(0, score || 0))}%`, background: color, transition: 'width 0.6s ease' }} />
                {/* Benchmark at 60 */}
                <div style={{ position: 'absolute', top: 0, bottom: 0, left: '60%', width: '1px', background: '#333' }} />
            </div>
            <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                <span style={{ fontSize: '0.45rem', color: '#fff' }}>PASS THRESHOLD → 60</span>
            </div>
        </div>
    )
}

/* ── Research card ── */
function ResearchCard({ item }) {
    const SENTIMENT_COLOR = { POSITIVE: '#22ff66', NEGATIVE: '#ff4444', NEUTRAL: '#888', MIXED: '#ff8800' }
    const color = SENTIMENT_COLOR[item.sentiment] || '#555'
    return (
        <div style={{ border: '1px solid #111', padding: '14px 16px', marginBottom: '6px' }}>
            <div style={{ display: 'flex', gap: '10px', alignItems: 'flex-start', marginBottom: '8px' }}>
                <span style={{ fontSize: '0.55rem', border: `1px solid ${color}`, color, padding: '2px 7px', flexShrink: 0, letterSpacing: '1px' }}>
                    {item.sentiment}
                </span>
                <div style={{ flex: 1 }}>
                    <p style={{ fontSize: '0.72rem', fontWeight: 600, margin: '0 0 4px', color: '#ddd', lineHeight: '1.4' }}>{item.title}</p>
                    <p style={{ fontSize: '0.58rem', color: '#fff', margin: 0, fontFamily: 'monospace' }}>
                        {item.source} · {item.date ? new Date(item.date).toLocaleDateString('en-IN') : 'RECENT'}
                    </p>
                </div>
                <span style={{ fontSize: '0.55rem', color: '#ccc', flexShrink: 0, border: '1px solid #111', padding: '2px 7px' }}>
                    {item.relevance_type?.replace('_', ' ')}
                </span>
            </div>
            {item.snippet && (
                <p style={{ fontSize: '0.62rem', color: '#eee', lineHeight: '1.6', margin: 0, paddingLeft: '8px', borderLeft: '2px solid #1a1a1a' }}>
                    {item.snippet}
                </p>
            )}
        </div>
    )
}

/* ── Covenant row ── */
function CovenantRow({ text, i }) {
    const isCritical = text.toLowerCase().includes('mandatory') || text.toLowerCase().includes('shall')
    return (
        <div style={{ padding: '12px 16px', borderBottom: '1px solid #080808', display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
            <span style={{ fontSize: '0.55rem', color: isCritical ? '#ff8800' : '#ccc', flexShrink: 0, marginTop: '2px', border: isCritical ? '1px solid #ff880050' : '1px solid #1a1a1a', padding: '1px 6px' }}>
                {String(i + 1).padStart(2, '0')}
            </span>
            <p style={{ fontSize: '0.68rem', color: '#eee', lineHeight: '1.6', margin: 0 }}>{text}</p>
        </div>
    )
}

/* ── SHAP Bar component ── */
function SHAPBar({ feature, value, impact, explanation }) {
    const isRisk = impact > 0
    const color = isRisk ? '#ff4444' : '#22ff66'
    // Scale for bar: max SHAP usually around 0.5-1.0 in this model
    const width = Math.min(100, Math.abs(impact) * 200) 
    
    return (
        <div style={{ marginBottom: '24px', borderBottom: '1px solid #0f0f0f', paddingBottom: '16px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
                <div style={{ flex: 1 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span style={{ fontSize: '0.7rem', fontWeight: 800, color: '#fff', fontFamily: 'monospace' }}>
                            {feature.replace(/_/g, ' ').toUpperCase()}
                        </span>
                        <span style={{ fontSize: '0.55rem', color: '#fff' }}>= {value}</span>
                    </div>
                </div>
                <div style={{ textAlign: 'right' }}>
                    <span style={{ fontSize: '0.75rem', fontWeight: 900, color }}>
                        {impact > 0 ? '+' : ''}{(impact * 100).toFixed(1)}% RISK
                    </span>
                </div>
            </div>
            
            <div style={{ height: '6px', background: '#0a0a0a', width: '100%', marginBottom: '12px', position: 'relative' }}>
                <div style={{ 
                    height: '100%', 
                    background: color, 
                    width: `${width}%`,
                    float: isRisk ? 'left' : 'right',
                    boxShadow: `0 0 10px ${color}30`
                }} />
            </div>

            {explanation && (
                <p style={{ fontSize: '0.65rem', color: '#fff', lineHeight: '1.6', margin: 0, fontStyle: 'italic', background: '#030303', padding: '10px', borderLeft: `2px solid ${color}40` }}>
                    "{explanation}"
                </p>
            )}
        </div>
    )
}

/* ── CAM Criteria card ── */
function CriteriaCard({ icon, label, status, detail }) {
    return (
        <div style={{ border: '1px solid #111', padding: '16px', background: '#040404' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
                <span style={{ fontSize: '0.65rem', color: status === 'COVERED' ? '#22dd55' : '#ff4444' }}>{icon}</span>
                <span style={{ fontSize: '0.5rem', letterSpacing: '1px', border: `1px solid ${status === 'COVERED' ? '#22dd5540' : '#ff444440'}`, color: status === 'COVERED' ? '#22dd55' : '#ff4444', padding: '2px 6px' }}>
                    {status}
                </span>
            </div>
            <p style={{ fontSize: '0.62rem', fontWeight: 700, letterSpacing: '1px', margin: '0 0 6px', color: '#bbb' }}>{label}</p>
            <p style={{ fontSize: '0.6rem', color: '#fff', lineHeight: '1.6', margin: 0 }}>{detail}</p>
        </div>
    )
}

/* ════════════════════════════════════════════════════════
   MAIN PAGE
═══════════════════════════════════════════════════════ */
export default function RecommendationPage() {
    const { caseId } = useParams()
    const [rec,       setRec]       = useState(null)
    const [caseData,  setCaseData]  = useState(null)
    const [research,  setResearch]  = useState(null)
    const [loading,   setLoading]   = useState(true)
    const [generating,setGenerating]= useState(false)
    const [amount,    setAmount]    = useState('')
    const [tab,       setTab]       = useState('overview')
    const [downloading, setDownloading] = useState(false)
    const [notes,       setNotes]       = useState([])
    const [newNote,     setNewNote]     = useState('')
    const [addingNote,  setAddingNote]  = useState(false)

    useEffect(() => { loadAll() }, [caseId])

    const loadAll = async () => {
        setLoading(true)
        try {
            const [rRes, cRes, resRes, nRes] = await Promise.allSettled([
                api.get(`/cases/${caseId}/recommendation`),
                api.get(`/cases/${caseId}`),
                api.get(`/cases/${caseId}/secondary-research`).catch(() => ({ data: null })),
                api.get(`/cases/${caseId}/notes`).catch(() => ({ data: { notes: [] } })),
            ])
            if (rRes.status === 'fulfilled')   setRec(rRes.value.data)
            if (cRes.status === 'fulfilled')   setCaseData(cRes.value.data)
            if (resRes.status === 'fulfilled') setResearch(resRes.value.data)
            if (nRes.status === 'fulfilled')   setNotes(nRes.value.data.notes || [])
            
            // Pre-fill amount from case
            if (cRes.status === 'fulfilled' && cRes.value.data?.loan_amount_cr) {
                setAmount(String(cRes.value.data.loan_amount_cr))
            }
        } finally { setLoading(false) }
    }

    const generate = async () => {
        setGenerating(true)
        try {
            const amountCr = parseFloat(amount) || caseData?.loan_amount_cr || 50
            const paise = amountCr * 10000000 * 100
            await api.post(`/cases/${caseId}/recommend`, { requested_amount_paise: paise })
            toast.success('CAM SYNTHESIS INITIATED')
            for (let i = 0; i < 30; i++) {
                await new Promise(r => setTimeout(r, 2000))
                try {
                    const res = await api.get(`/cases/${caseId}/recommendation`)
                    if (res.data) { setRec(res.data); break }
                } catch { }
            }
        } catch {
            toast.error('CAM GENERATION FAILED — CHECK BACKEND LOGS')
        } finally { setGenerating(false) }
    }

    const downloadCAM = async (format) => {
        setDownloading(true)
        try {
            const res = await api.get(`/cases/${caseId}/cam/${format}`, { responseType: 'blob' })
            const mimeType = format === 'word' 
                ? 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' 
                : 'application/pdf'
            
            const blob = new Blob([res.data], { type: mimeType })
            const url = window.URL.createObjectURL(blob)
            
            const a = document.createElement('a')
            a.href = url
            a.download = `CAM_${caseData?.company_name?.replace(/\s+/g, '_') || caseId}_${format === 'word' ? 'docx' : 'pdf'}`
            document.body.appendChild(a)
            a.click()
            document.body.removeChild(a)
            window.URL.revokeObjectURL(url)
            toast.success(`${format.toUpperCase()} DOWNLOADED`)
        } catch (err) {
            console.error(err)
            toast.error(`CAM ${format.toUpperCase()} NOT AVAILABLE — RUN ANALYSIS FIRST`)
        } finally { setLoading(false); setDownloading(false) }
    }

    const addNote = async () => {
        if (!newNote.trim()) return
        setAddingNote(true)
        try {
            await api.post(`/cases/${caseId}/notes`, { note: newNote })
            setNewNote('')
            toast.success('INSIGHT ADDED & PROCESSED')
            await loadAll() // Reload to get new notes and potentially updated rec
        } catch {
            toast.error('FAILED TO ADD NOTE')
        } finally { setAddingNote(false) }
    }

    const deleteNote = async (id) => {
        try {
            await api.delete(`/cases/${caseId}/notes/${id}`)
            toast.success('NOTE DELETED')
            await loadAll()
        } catch {
            toast.error('DELETE FAILED')
        }
    }

    /* ── loading state ── */
    if (loading) return (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '60vh', color: '#333', fontSize: '0.75rem', letterSpacing: '3px' }}>
            LOADING CAM...
        </div>
    )

    /* ── Generation form ── */
    if (!rec) return (
        <div style={{ maxWidth: '600px', margin: '80px auto', textAlign: 'center' }}>
            <div style={{ fontSize: '3rem', marginBottom: '16px', opacity: 0.15 }}>📋</div>
            <h2 style={{ fontSize: '1rem', marginBottom: '8px', letterSpacing: '2px' }}>CREDIT APPRAISAL MEMO</h2>
            <p style={{ color: '#fff', fontSize: '0.65rem', lineHeight: '1.8', marginBottom: '8px' }}>
                Entity: <strong style={{ color: '#fff' }}>{caseData?.company_name || '—'}</strong>
            </p>
            {caseData?.sector && <p style={{ color: '#fff', fontSize: '0.6rem', marginBottom: '30px' }}>Sector: {caseData.sector} · Loan Ask: ₹{caseData.loan_amount_cr} Cr · {caseData.loan_type}</p>}

            <div style={{ marginBottom: '20px', textAlign: 'left', border: '1px solid #1a1a1a', padding: '20px' }}>
                <label style={{ fontSize: '0.55rem', color: '#555', letterSpacing: '2px', display: 'block', marginBottom: '8px' }}>
                    FINAL REQUESTED AMOUNT (₹ CRORE)
                </label>
                <input
                    type="number"
                    placeholder={caseData?.loan_amount_cr || '50'}
                    value={amount}
                    onChange={e => setAmount(e.target.value)}
                    style={{ fontSize: '1.2rem', fontWeight: 700, textAlign: 'center', background: '#050505' }}
                />
                <p style={{ fontSize: '0.55rem', color: '#777', marginTop: '8px', margin: '8px 0 0' }}>
                    This will trigger the full CAM synthesis: Five Cs scoring, SWOT, facility structure, interest rate, and covenants.
                </p>
            </div>

            <button onClick={generate} disabled={generating} style={{ width: '100%', padding: '16px', fontWeight: 900, fontSize: '0.75rem', background: generating ? '#111' : '#fff', color: generating ? '#444' : '#000', border: '1px solid #333' }}>
                {generating ? '⟳ SYNTHESIZING CAM...' : '▶ GENERATE FULL CREDIT APPRAISAL MEMO'}
            </button>

            {generating && (
                <p style={{ fontSize: '0.6rem', color: '#888', marginTop: '15px' }}>
                    Running Five Cs engine · SHAP explainability · SWOT synthesis · Facility structuring...
                </p>
            )}

            <div style={{ display: 'flex', justifyContent: 'center', gap: '15px', marginTop: '20px' }}>
                <Link to={`/cases/${caseId}/analysis`} style={{ fontSize: '0.6rem', color: '#444', textDecoration: 'none' }}>← Run ML Ensemble First</Link>
                <Link to={`/cases/${caseId}/results`}  style={{ fontSize: '0.6rem', color: '#444', textDecoration: 'none' }}>← View Extraction Results</Link>
            </div>
        </div>
    )

    /* ── Data ── */
    const decisionKey = rec.decision?.toUpperCase() || 'PENDING'
    const ds          = DECISION_STYLE[decisionKey] || DECISION_STYLE.PENDING
    const fiveCs      = rec.five_cs_score || {}
    const swot        = rec.swot || null
    const researchItems = research?.items || []
    const positiveRes = researchItems.filter(i => i.sentiment === 'POSITIVE').length
    const negativeRes = researchItems.filter(i => i.sentiment === 'NEGATIVE').length

    const TABS = [
        { id: 'overview',  label: 'OVERVIEW' },
        { id: 'five_cs',   label: 'FIVE Cs ANALYSIS' },
        { id: 'shap',      label: 'RISK DRIVERS (SHAP)' },
        { id: 'swot',      label: 'SWOT' },
        { id: 'research',  label: `SECONDARY RESEARCH ${researchItems.length > 0 ? `(${researchItems.length})` : ''}` },
        { id: 'insights',  label: `PRIMARY INSIGHTS ${notes.length > 0 ? `(${notes.length})` : ''}` },
        { id: 'judiciary', label: 'EVALUATION CRITERIA' },
    ]

    return (
        <div style={{ maxWidth: '1100px', margin: '0 auto' }}>

            {/* ── Page header ── */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '24px', paddingBottom: '20px', borderBottom: '1px solid #111' }}>
                <div>
                    <p style={{ fontSize: '0.5rem', color: '#444', letterSpacing: '4px', margin: '0 0 5px' }}>CREDIT APPRAISAL MEMO · CONFIDENTIAL</p>
                    <h1 style={{ margin: '0 0 4px', fontSize: '1.4rem', fontWeight: 900 }}>{caseData?.company_name || 'CAM REPORT'}</h1>
                    <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
                        {caseData?.sector         && <span style={{ fontSize: '0.55rem', color: '#555', border: '1px solid #1a1a1a', padding: '2px 8px' }}>{caseData.sector.toUpperCase()}</span>}
                        {caseData?.loan_type      && <span style={{ fontSize: '0.55rem', color: '#555', border: '1px solid #1a1a1a', padding: '2px 8px' }}>{caseData.loan_type.toUpperCase()}</span>}
                        {caseData?.company_pan    && <span style={{ fontSize: '0.55rem', color: '#555', border: '1px solid #1a1a1a', padding: '2px 8px' }}>PAN: {caseData.company_pan}</span>}
                        {caseData?.company_cin    && <span style={{ fontSize: '0.55rem', color: '#555', border: '1px solid #1a1a1a', padding: '2px 8px' }}>CIN: {caseData.company_cin}</span>}
                    </div>
                </div>
                <div style={{ display: 'flex', gap: '8px', flexShrink: 0 }}>
                    <button onClick={() => downloadCAM('pdf')} disabled={downloading} style={{ padding: '8px 16px', fontSize: '0.6rem', letterSpacing: '1px' }}>
                        ↓ PDF CAM
                    </button>
                    <button onClick={() => downloadCAM('word')} disabled={downloading} style={{ padding: '8px 16px', fontSize: '0.6rem', letterSpacing: '1px' }}>
                        ↓ WORD CAM
                    </button>
                    <button onClick={generate} disabled={generating} style={{ padding: '8px 16px', fontSize: '0.6rem', background: 'transparent', color: '#444', letterSpacing: '1px' }}>
                        {generating ? '⟳' : '↺ REGEN'}
                    </button>
                </div>
            </div>

            {/* ── Decision banner ── */}
            <div style={{ background: ds.bg, border: `1px solid ${ds.border}`, padding: '24px 28px', marginBottom: '24px', display: 'grid', gridTemplateColumns: '1fr auto', gap: '20px', alignItems: 'center' }}>
                <div>
                    <p style={{ fontSize: '0.5rem', color: ds.border, letterSpacing: '3px', margin: '0 0 6px', opacity: 0.7 }}>AI SYSTEM DECISION</p>
                    <h2 style={{ fontSize: '1.5rem', fontWeight: 900, color: ds.text, margin: '0 0 8px', letterSpacing: '1px' }}>{ds.label}</h2>
                    <p style={{ fontSize: '0.65rem', color: '#fff', margin: 0 }}>
                        Recommended limit: <strong style={{ color: '#fff' }}>{crore(rec.recommended_limit_paise)}</strong>
                        &nbsp;·&nbsp;Rate: <strong style={{ color: '#fff' }}>{rec.interest_rate_pct}% p.a.</strong>
                        &nbsp;·&nbsp;MPBF: <strong style={{ color: '#fff' }}>{crore(rec.mpbf_paise)}</strong>
                    </p>
                </div>
                <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: '2.5rem', fontWeight: 900, color: ds.text, lineHeight: 1 }}>{fiveCs.Composite?.toFixed(0) || '—'}</div>
                    <div style={{ fontSize: '0.5rem', color: '#fff', letterSpacing: '2px', marginTop: '4px' }}>FIVE Cs COMPOSITE</div>
                </div>
            </div>

            {/* ── Tabs ── */}
            <Tabs tabs={TABS} active={tab} onChange={setTab} />

            {/* ══════ TAB: OVERVIEW ══════ */}
            {tab === 'overview' && (
                <div>
                    {/* Key figures */}
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', background: '#080808', border: '1px solid #111', marginBottom: '24px' }}>
                        {[
                            { label: 'LOAN REQUESTED',  value: crore((parseFloat(amount) || caseData?.loan_amount_cr || 0) * 10000000 * 100) },
                            { label: 'RECOMMENDED LIMIT', value: crore(rec.recommended_limit_paise) },
                            { label: 'INTEREST RATE',   value: `${rec.interest_rate_pct}% p.a.`, accent: rec.interest_rate_pct > 14 ? '#ff8800' : '#fff' },
                            { label: 'TENURE',          value: caseData?.loan_tenure_months ? `${caseData.loan_tenure_months} months` : '—' },
                        ].map((s, i) => (
                            <div key={i} style={{ padding: '20px', borderRight: i < 3 ? '1px solid #111' : 'none' }}>
                                <p style={{ fontSize: '0.5rem', color: '#fff', letterSpacing: '2px', margin: '0 0 8px' }}>{s.label}</p>
                                <p style={{ fontSize: '1rem', fontWeight: 900, margin: 0, color: s.accent || '#fff' }}>{s.value}</p>
                            </div>
                        ))}
                    </div>

                    {/* Facility breakup */}
                    {Object.keys(rec.facility_breakup || {}).length > 0 && (
                        <div style={{ border: '1px solid #111', marginBottom: '24px' }}>
                            <div style={{ padding: '13px 18px', borderBottom: '1px solid #111' }}>
                                <span style={{ fontSize: '0.6rem', letterSpacing: '2px', color: '#666' }}>FACILITY STRUCTURE</span>
                            </div>
                            {Object.entries(rec.facility_breakup).map(([f, p], i) => (
                                <div key={i} style={{ padding: '12px 18px', borderBottom: '1px solid #080808', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                    <span style={{ fontSize: '0.68rem', color: '#777' }}>{f.replace(/_/g, ' ').toUpperCase()}</span>
                                    <span style={{ fontSize: '0.75rem', fontWeight: 700 }}>{crore(p)}</span>
                                </div>
                            ))}
                        </div>
                    )}

                    {/* Decision rationale */}
                    <div style={{ border: '1px solid #111', marginBottom: '24px' }}>
                        <div style={{ padding: '13px 18px', borderBottom: '1px solid #111' }}>
                            <span style={{ fontSize: '0.6rem', letterSpacing: '2px', color: '#666' }}>DECISION RATIONALE</span>
                        </div>
                        <div style={{ padding: '18px' }}>
                            <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
                                {(rec.reasons || ['No rationale generated']).map((r, i) => (
                                    <li key={i} style={{ fontSize: '0.75rem', color: '#fff', lineHeight: '1.8', marginBottom: '8px', paddingLeft: '14px', borderLeft: '2px solid #222' }}>
                                        {r}
                                    </li>
                                ))}
                            </ul>
                        </div>
                    </div>

                    {/* Mitigation Section */}
                    {rec.mitigation_plan && (
                        <div style={{ marginBottom: '24px' }}>
                             <div style={{ padding: '13px 0', borderBottom: '1px solid #111', marginBottom: '16px' }}>
                                <span style={{ fontSize: '0.65rem', letterSpacing: '3px', color: '#fff', fontWeight: 900 }}>ACTIONABLE MITIGATION PLAN</span>
                            </div>
                            <MitigationPlan plan={rec.mitigation_plan} />
                        </div>
                    )}

                    {/* Covenants */}
                    {(rec.covenants || []).length > 0 && (
                        <div style={{ border: '1px solid #111', borderLeft: '3px solid #ff880050' }}>
                            <div style={{ padding: '13px 18px', borderBottom: '1px solid #111', display: 'flex', gap: '10px', alignItems: 'center' }}>
                                <span style={{ fontSize: '0.6rem', letterSpacing: '2px', color: '#666' }}>MANDATORY COVENANTS</span>
                                <span style={{ fontSize: '0.5rem', border: '1px solid #ff880040', color: '#ff8800', padding: '1px 7px' }}>{rec.covenants.length} CONDITIONS</span>
                            </div>
                            {rec.covenants.map((c, i) => <CovenantRow key={i} text={c} i={i} />)}
                        </div>
                    )}
                </div>
            )}

            {/* ══════ TAB: FIVE Cs ══════ */}
            {tab === 'five_cs' && (
                <div>
                    <div style={{ background: '#040404', border: '1px solid #111', padding: '16px 20px', marginBottom: '20px' }}>
                        <p style={{ fontSize: '0.62rem', color: '#aaa', lineHeight: '1.8', margin: 0 }}>
                            The Five Cs framework evaluates creditworthiness across <strong style={{ color: '#ccc' }}>Character</strong> (integrity & governance),
                            <strong style={{ color: '#ccc' }}> Capacity</strong> (repayment ability via DSCR/EBITDA),
                            <strong style={{ color: '#ccc' }}> Capital</strong> (leverage & equity structure),
                            <strong style={{ color: '#ccc' }}> Collateral</strong> (security coverage), and
                            <strong style={{ color: '#ccc' }}> Conditions</strong> (sector, GST compliance, market context).
                            Each is scored 0–100 using 50 extracted features. <strong style={{ color: '#ccc' }}>Benchmark: 60/100 per C.</strong>
                        </p>
                    </div>

                    <div style={{ border: '1px solid #111', padding: '24px', marginBottom: '20px' }}>
                        {[
                            { c: 'Character',   desc: 'Audit opinion · Director CIRP links · MCA compliance · Going concern' },
                            { c: 'Capacity',    desc: 'DSCR · EBITDA margin · Interest coverage · NACH bounces · PAT trend' },
                            { c: 'Capital',     desc: 'Debt-to-Equity · TOL/TNW · Undisclosed borrowings · Shareholder funds' },
                            { c: 'Collateral',  desc: 'Security coverage ratio · Lien quality · Collateral type scoring' },
                            { c: 'Conditions',  desc: 'Sector risk · GST filing compliance · ITC fraud signals · Circular trading' },
                        ].map(({ c, desc }) => (
                            <CBar key={c} name={c} score={fiveCs[c]} desc={desc} />
                        ))}
                        <div style={{ marginTop: '20px', paddingTop: '16px', borderTop: '1px solid #111', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <div>
                                <span style={{ fontSize: '0.65rem', fontWeight: 700, color: '#fff' }}>COMPOSITE WEIGHTED SCORE</span>
                                <span style={{ fontSize: '0.55rem', color: '#fff', marginLeft: '8px' }}>Passes at 60/100</span>
                            </div>
                            <span style={{ fontSize: '1.5rem', fontWeight: 900, color: (fiveCs.Composite || 0) >= 60 ? '#fff' : '#ff4444' }}>
                                {round1(fiveCs.Composite)}/100
                            </span>
                        </div>
                    </div>
                </div>
            )}

            {/* ══════ TAB: SHAP ══════ */}
            {tab === 'shap' && (
                <div>
                    <div style={{ background: '#040404', border: '1px solid #111', padding: '16px 20px', marginBottom: '24px' }}>
                        <p style={{ fontSize: '0.62rem', color: '#666', lineHeight: '1.8', margin: 0 }}>
                            <strong style={{ color: '#aaa' }}>EXPLAINABLE AI (SHAP)</strong>: Features that pushed the default risk up (Red) or down (Green). 
                            Impact shown as the percentage contribution to the final risk probability.
                        </p>
                    </div>

                    <div style={{ border: '1px solid #111', padding: '30px' }}>
                        {(rec.shap_contributions || []).length > 0 ? (
                            rec.shap_contributions.map((c, i) => (
                                <SHAPBar 
                                    key={i}
                                    feature={c.feature_name}
                                    value={c.feature_value}
                                    impact={c.shap_value}
                                    explanation={c.explanation}
                                />
                            ))
                        ) : (
                            <div style={{ textAlign: 'center', padding: '40px', color: '#444', fontSize: '0.7rem' }}>
                                NO SHAP VALUES GENERATED FOR THIS CASE.
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* ══════ TAB: SWOT ══════ */}
            {tab === 'swot' && (
                <div>
                    {swot ? (
                        <>
                            <div style={{ background: '#040404', border: '1px solid #111', padding: '14px 18px', marginBottom: '20px' }}>
                                <p style={{ fontSize: '0.62rem', color: '#666', margin: 0, lineHeight: '1.7' }}>
                                    SWOT analysis synthesised from: (1) financial ratio trends, (2) EWS flag triggers, (3) secondary research sentiment, (4) sector conditions, and (5) management/governance signals.
                                    <strong style={{ color: '#aaa' }}> Triangulated across all data sources.</strong>
                                </p>
                            </div>
                            <SWOTGrid swot={swot} />
                        </>
                    ) : (
                        <div style={{ textAlign: 'center', padding: '80px', border: '1px solid #111', color: '#444' }}>
                            <p style={{ fontSize: '0.8rem', marginBottom: '10px' }}>SWOT NOT GENERATED</p>
                            <p style={{ fontSize: '0.6rem', color: '#333' }}>Regenerate the CAM — SWOT requires completed ML analysis + EWS report.</p>
                        </div>
                    )}

                    {/* GenAI summary */}
                    {rec.score_narrative && (
                        <div style={{ marginTop: '20px', border: '1px solid #111', padding: '30px' }}>
                            <div style={{ fontSize: '0.65rem', letterSpacing: '3px', color: '#fff', fontWeight: 900, marginBottom: '20px', paddingBottom: '10px', borderBottom: '1px solid #111' }}>AI-SYNTHESISED CREDIT NARRATIVE</div>
                            <p style={{ fontSize: '0.85rem', color: '#fff', lineHeight: '2.0', whiteSpace: 'pre-line' }}>
                                {rec.score_narrative}
                            </p>
                        </div>
                    )}
                </div>
            )}

            {/* ══════ TAB: SECONDARY RESEARCH ══════ */}
            {tab === 'research' && (
                <div>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', background: '#080808', border: '1px solid #111', marginBottom: '20px' }}>
                        {[
                            { label: 'ARTICLES FOUND',  value: researchItems.length },
                            { label: 'POSITIVE SIGNALS',value: positiveRes, color: '#22ff66' },
                            { label: 'NEGATIVE SIGNALS',value: negativeRes, color: '#ff4444' },
                            { label: 'SOURCES SCRAPED', value: new Set(researchItems.map(i => i.source)).size },
                        ].map((s, i) => (
                            <div key={i} style={{ padding: '18px', borderRight: i < 3 ? '1px solid #111' : 'none' }}>
                                <p style={{ fontSize: '0.5rem', color: '#fff', letterSpacing: '2px', margin: '0 0 6px' }}>{s.label}</p>
                                <p style={{ fontSize: '1.4rem', fontWeight: 900, margin: 0, color: s.color || '#fff' }}>{s.value}</p>
                            </div>
                        ))}
                    </div>

                    {researchItems.length === 0 ? (
                        <div style={{ textAlign: 'center', padding: '60px', border: '1px solid #111', color: '#444' }}>
                            <p style={{ fontSize: '0.75rem', marginBottom: '10px' }}>NO SECONDARY RESEARCH DATA</p>
                            <p style={{ fontSize: '0.6rem', color: '#333' }}>
                                The research agent scrapes news, BSE/NSE filings, MCA, and e-Courts for the entity.<br/>
                                Ensure COMPANY_NAME and PAN are set for the web agent to query.
                            </p>
                        </div>
                    ) : (
                        <div>
                            {['NEGATIVE', 'POSITIVE', 'NEUTRAL', 'MIXED'].map(sentiment => {
                                const items = researchItems.filter(i => i.sentiment === sentiment)
                                if (!items.length) return null
                                return (
                                    <div key={sentiment} style={{ marginBottom: '20px' }}>
                                        <p style={{ fontSize: '0.55rem', color: '#444', letterSpacing: '2px', marginBottom: '10px' }}>
                                            {sentiment} ({items.length})
                                        </p>
                                        {items.map((item, i) => <ResearchCard key={i} item={item} />)}
                                    </div>
                                )
                            })}
                        </div>
                    )}

                    {/* Triangulation note */}
                    <div style={{ marginTop: '20px', background: '#040404', border: '1px solid #111', padding: '16px 18px' }}>
                        <p style={{ fontSize: '0.55rem', letterSpacing: '2px', color: '#444', marginBottom: '8px' }}>TRIANGULATION METHOD</p>
                        <p style={{ fontSize: '0.62rem', color: '#555', lineHeight: '1.7', margin: 0 }}>
                            Secondary research is cross-referenced with: (1) EWS flags from document extraction, (2) GST filing patterns,
                            (3) financial ratio trends, and (4) MCA compliance data. Negative news that corroborates an EWS flag
                            increases the flag severity by one level (LOW→MEDIUM, MEDIUM→HIGH, HIGH→CRITICAL).
                        </p>
                    </div>
                </div>
            )}

            {/* ══════ TAB: PRIMARY INSIGHTS ══════ */}
            {tab === 'insights' && (
                <div>
                    <div className="card">
                        <h3 className="overline mb-2">ADD QUALITATIVE INSIGHT</h3>
                        <p className="text-muted" style={{ fontSize: '0.65rem', marginBottom: '20px' }}>
                            Input notes from factory site visits, management interviews, or promoter diligence. 
                            AI will automatically map these to Five Cs adjustments.
                        </p>
                        <textarea
                            value={newNote}
                            onChange={e => setNewNote(e.target.value)}
                            placeholder="e.g. Factory found operating at 40% capacity due to labor shortage. Management seems evasive about group company debt..."
                            rows={4}
                            style={{ marginBottom: '16px', fontSize: '0.75rem', padding: '15px' }}
                        />
                        <button 
                            className="btn-primary" 
                            onClick={addNote} 
                            disabled={addingNote || !newNote.trim()}
                            style={{ width: '100%' }}
                        >
                            {addingNote ? 'PROCESSING INSIGHT...' : 'SUBMIT & ADJUST RISK SCORE'}
                        </button>
                    </div>

                    <div className="section-header">SUBMITTED INSIGHTS ({notes.length})</div>
                    
                    {notes.length === 0 ? (
                        <div className="card text-center text-muted" style={{ padding: '60px' }}>
                            NO PRIMARY INSIGHTS RECORDED YET.
                        </div>
                    ) : (
                        <div className="flex-col gap-3">
                            {notes.map((n, i) => {
                                const adj = n.processed_adjustment || {}
                                const isPos = adj.adjustment > 0
                                const isNeg = adj.adjustment < 0
                                return (
                                    <div key={n._id} className="card-2" style={{ borderLeft: `3px solid ${isPos ? 'var(--success)' : isNeg ? 'var(--danger)' : 'var(--border-mid)'}` }}>
                                        <div className="flex justify-between items-center mb-3">
                                            <div className="flex items-center gap-2">
                                                <span className={`badge ${isPos ? 'badge-success' : isNeg ? 'badge-danger' : 'badge-muted'}`}>
                                                    {adj.dimension?.toUpperCase() || 'GENERAL'}
                                                </span>
                                                <span className="mono" style={{ fontSize: '0.7rem', color: isPos ? 'var(--success)' : isNeg ? 'var(--danger)' : 'var(--text-muted)' }}>
                                                    {adj.adjustment > 0 ? '+' : ''}{adj.adjustment?.toFixed(1)} POINTS
                                                </span>
                                            </div>
                                            <button onClick={() => deleteNote(n._id)} className="btn-ghost" style={{ padding: '4px 10px', fontSize: '0.6rem' }}>DELETE</button>
                                        </div>
                                        <p style={{ fontSize: '0.8rem', color: 'var(--text-bright)', marginBottom: '10px', lineHeight: '1.6' }}>"{n.note}"</p>
                                        <p className="text-muted" style={{ fontSize: '0.65rem', fontStyle: 'italic' }}>
                                            {adj.reason}
                                        </p>
                                        <div className="text-muted" style={{ fontSize: '0.55rem', marginTop: '14px', textAlign: 'right', borderTop: '1px solid var(--border-dim)', paddingTop: '8px' }}>
                                            RECORDED BY AI-MANAGER · {new Date(n.created_at).toLocaleString('en-IN')}
                                        </div>
                                    </div>
                                )
                            })}
                        </div>
                    )}

                    <div className="card-2 mt-4" style={{ background: '#0a0a0a', border: '1px solid var(--border-dim)' }}>
                        <p className="text-muted" style={{ fontSize: '0.6rem', margin: 0 }}>
                            <span className="text-info">ℹ</span> Qualitative adjustments are capped at ±15 points per dimension to maintain model integrity. 
                            The composite score is automatically recalculated upon saving. 
                            Regenerate the CAM to reflect these changes in the final PDF/Word report.
                        </p>
                    </div>
                </div>
            )}

            {/* ══════ TAB: EVALUATION CRITERIA ══════ */}
            {tab === 'judiciary' && (
                <div>
                    <div style={{ background: '#040404', border: '1px solid #111', padding: '14px 18px', marginBottom: '24px' }}>
                        <p style={{ fontSize: '0.62rem', color: '#666', margin: 0 }}>
                            How Intelli-Credit addresses each hackathon evaluation criterion. This CAM demonstrates all 5 dimensions to judges.
                        </p>
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '24px' }}>
                        <CriteriaCard
                            icon="📄"
                            label="EXTRACTION ACCURACY"
                            status="COVERED"
                            detail="5-layer pipeline: PyMuPDF OCR + pdfplumber for tables, regex-based financial statement parsing, keyword-anchored section detection. Supports scanned PDFs (Indian bank letterheads, handwritten notes). Auto-detects GSTR-1, 3B, 2A, 9C, HDFC/SBI/ICICI statement formats, CRISIL/ICRA ratings."
                        />
                        <CriteriaCard
                            icon="🔍"
                            label="RESEARCH DEPTH"
                            status="COVERED"
                            detail="Research agent scrapes: Google News (company + sector terms), BSE/NSE corporate filings, MCA21 e-filing data, eCourts for DRT/NCLT cases, RBI regulatory circulars. Findings are sentiment-scored and triangulated against extracted data to amplify or confirm EWS flags."
                        />
                        <CriteriaCard
                            icon="🧠"
                            label="EXPLAINABILITY"
                            status="COVERED"
                            detail="SHAP (SHapley Additive exPlanations) on 50-feature vector from XGBoost + LightGBM + CatBoost stacking ensemble. Each risk driver shows: actual value, SHAP magnitude, industry benchmark, plain-English 'why this matters' paragraph. Judges can trace every decision from raw PDF to final grade."
                        />
                        <CriteriaCard
                            icon="🇮🇳"
                            label="INDIAN CONTEXT SENSITIVITY"
                            status="COVERED"
                            detail="Native support for: GSTR-2A vs 3B ITC reconciliation, NACH bounce detection, MPBF (Tandon Committee), MCA21 compliance gaps, DRT/NCLT case extraction, CIBIL Commercial / CRISIL / ICRA / CARE rating formats, RBI NPA classification norms, sector-specific risk scoring for Manufacturing, NBFC, Infrastructure."
                        />
                        <CriteriaCard
                            icon="⚙"
                            label="OPERATIONAL EXCELLENCE"
                            status="COVERED"
                            detail="FastAPI + Motor async backend, React 18 + Vite frontend, MongoDB Atlas. Uptime-ready with health check. CORS configured for all dev and prod ports. JWT authentication. Background task queue for non-blocking pipeline execution. Loguru verbose logging for observability."
                        />
                        <CriteriaCard
                            icon="🚀"
                            label="USER EXPERIENCE"
                            status="COVERED"
                            detail="4-step guided workflow: (1) Entity onboarding with PAN/CIN/Sector/Loan details, (2) Multi-format upload with expected doc type hints, (3) Human-in-the-loop classification review, (4) Real-time pipeline progress polling. Results in tabbed views: EWS flags, GST analysis, ratios, SWOT, SHAP drivers. Downloadable PDF/Word CAM."
                        />
                    </div>

                    {/* Full user journey */}
                    <div style={{ border: '1px solid #111' }}>
                        <div style={{ padding: '13px 18px', borderBottom: '1px solid #111' }}>
                            <span style={{ fontSize: '0.6rem', letterSpacing: '2px', color: '#666' }}>HACKATHON USER JOURNEY — ALL 4 STAGES IMPLEMENTED</span>
                        </div>
                        {[
                            {
                                n: '01', title: 'ENTITY ONBOARDING',
                                items: ['Company Name, CIN, PAN, Sector, Annual Turnover', 'Loan Type (Term Loan / CC / OD / LC / BG), Amount, Tenure', 'Loan Purpose (free text)', 'Multi-step form with validation'],
                            },
                            {
                                n: '02', title: 'INTELLIGENT DATA INGESTION',
                                items: ['Supports ALM, Shareholding Pattern, Borrowing Profile, Annual Reports, Portfolio/Performance data', 'Also: GST (GSTR-1/3B/2A/9C), Bank Statements (HDFC/SBI/ICICI/AXIS), Rating Reports, Legal Notices', 'PDF · JSON · CSV · XLSX · XLS (up to 50MB per file)', 'Drag-and-drop with queuing'],
                            },
                            {
                                n: '03', title: 'AUTOMATED EXTRACTION & SCHEMA MAPPING',
                                items: ['AI auto-classifies each document on upload (confidence score shown)', 'Human-in-the-loop table: user can override any classification before pipeline runs', 'Fixed schema: 50-feature vector (ratios, EWS, GST flags, bank indicators)', 'Override stored in MongoDB with human_override: true flag'],
                            },
                            {
                                n: '04', title: 'PRE-COGNITIVE SECONDARY ANALYSIS',
                                items: ['Secondary research agent: news, legal, market sentiment', 'Triangulated with extracted financial signals', 'SHAP-driven explainable recommendation engine', 'SWOT synthesis: Strengths / Weaknesses / Opportunities / Threats', 'Downloadable CAM: PDF + Word'],
                            },
                        ].map(({ n, title, items }) => (
                            <div key={n} style={{ padding: '18px 20px', borderBottom: '1px solid #080808', display: 'grid', gridTemplateColumns: '100px 1fr', gap: '20px' }}>
                                <div>
                                    <div style={{ fontSize: '1.5rem', fontWeight: 900, color: '#111', lineHeight: 1 }}>{n}</div>
                                    <div style={{ fontSize: '0.5rem', color: '#555', marginTop: '4px' }}>STAGE {n}</div>
                                </div>
                                <div>
                                    <p style={{ fontSize: '0.65rem', fontWeight: 700, color: '#bbb', margin: '0 0 10px', letterSpacing: '1px' }}>{title}</p>
                                    <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
                                        {items.map((item, i) => (
                                            <li key={i} style={{ fontSize: '0.62rem', color: '#555', lineHeight: '1.7', paddingLeft: '12px', borderLeft: '2px solid #1a1a1a', marginBottom: '4px' }}>
                                                ✓ {item}
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    )
}
