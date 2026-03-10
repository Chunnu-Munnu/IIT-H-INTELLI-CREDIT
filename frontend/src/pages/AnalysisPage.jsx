import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import {
    RadarChart, Radar, PolarGrid, PolarAngleAxis,
    BarChart, Bar, XAxis, YAxis, Cell, Tooltip, ResponsiveContainer, ReferenceLine
} from 'recharts'
import { Brain } from 'lucide-react'
import api from '../services/api'

/* ── Helpers ────────────────────────────── */
const GRADE_COLOR = { AAA:'#fff', AA:'#fff', A:'#ccc', BBB:'#aaa', BB:'#ff8800', B:'#ff6600', C:'#ff4444', D:'#ff0000' }

const FEATURE_LABELS = {
    dscr_fy1:                'Debt Service Coverage (FY1)',
    dscr_fy2:                'Debt Service Coverage (FY2)',
    ebitda_margin_fy1:       'EBITDA Margin (FY1)',
    ebitda_margin_fy2:       'EBITDA Margin (FY2)',
    debt_equity_fy1:         'Debt-to-Equity (FY1)',
    debt_equity_fy2:         'Debt-to-Equity (FY2)',
    interest_coverage_fy1:   'Interest Coverage (FY1)',
    current_ratio_fy1:       'Current Ratio (FY1)',
    tol_tnw_fy1:             'TOL / TNW (FY1)',
    gst_bank_inflation_ratio:'GST vs Bank Inflation Ratio',
    itc_inflation_flag:      'ITC Inflation Suspected',
    circular_trading_flag:   'Circular Trading Detected',
    nach_bounce_count:        'NACH Bounce Count',
    going_concern_flag:       'Going Concern Doubt',
    director_cirp_linked:     'Director CIRP Linked',
    total_ews_score_deduction:'EWS Penalty Score',
    ews_character_flags:      'Character Flags (EWS)',
    ews_capacity_flags:       'Capacity Flags (EWS)',
    ews_capital_flags:        'Capital Flags (EWS)',
    ews_conditions_flags:     'Conditions Flags (EWS)',
}

const FEATURE_DIRECTION_HINT = {
    dscr_fy1:                { higher: 'better', benchmark: 'DSCR ≥ 1.25x needed for loan eligibility' },
    ebitda_margin_fy1:       { higher: 'better', benchmark: 'EBITDA margin ≥ 10% is preferred' },
    debt_equity_fy1:         { higher: 'worse',  benchmark: 'D/E ≤ 3x is acceptable; above is over-leveraged' },
    interest_coverage_fy1:   { higher: 'better', benchmark: 'ICR ≥ 2.5x preferred; below 1.5x is distress' },
    gst_bank_inflation_ratio:{ higher: 'worse',  benchmark: 'Ratio > 1.15x indicates revenue inflation' },
    itc_inflation_flag:      { higher: 'worse',  benchmark: '1 = Suspected ITC fraud, 0 = clean' },
    circular_trading_flag:   { higher: 'worse',  benchmark: '1 = Circular trading detected in GST graph' },
    nach_bounce_count:        { higher: 'worse',  benchmark: 'Any NACH bounce is a liquidity warning signal' },
    going_concern_flag:       { higher: 'worse',  benchmark: 'Going concern doubt = existential audit risk' },
    total_ews_score_deduction:{ higher: 'worse', benchmark: 'Each EWS flag reduces the base credit score' },
}

function GradeRing({ grade, score }) {
    const color = GRADE_COLOR[grade] || '#fff'
    return (
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '12px' }}>
            <div style={{
                width: '160px', height: '160px',
                border: `6px solid ${color}`,
                display: 'flex', flexDirection: 'column',
                alignItems: 'center', justifyContent: 'center',
                boxShadow: `0 0 30px ${color}15`,
            }}>
                <div style={{ fontSize: '3.5rem', fontWeight: 900, color, lineHeight: 1 }}>{grade}</div>
                <div style={{ fontSize: '0.7rem', color: '#666', letterSpacing: '3px', marginTop: '6px' }}>GRADE</div>
            </div>
            <div style={{ fontSize: '1.6rem', fontWeight: 900, color: '#fff' }}>{score}<span style={{ fontSize: '0.7rem', color: '#555', fontWeight: 400 }}>/850</span></div>
        </div>
    )
}

function SHAPCard({ feature, index }) {
    const [open, setOpen] = useState(false)
    const isRisk      = feature.impact === 'RISK'
    const barColor    = isRisk ? '#ff4444' : '#fff'
    const label       = FEATURE_LABELS[feature.raw_name] || feature.name
    const hint        = FEATURE_DIRECTION_HINT[feature.raw_name]
    const shapMag     = Math.abs(feature.shap_value)
    const maxShap     = 0.4  // normalise bar to this max

    return (
        <div
            onClick={() => setOpen(o => !o)}
            style={{
                border: `1px solid ${isRisk ? '#ff444430' : '#ffffff20'}`,
                background: isRisk ? '#0a0303' : '#050505',
                padding: '20px 24px',
                marginBottom: '8px',
                cursor: 'pointer',
                userSelect: 'none',
                transition: 'all 0.2s ease',
            }}
        >
            {/* Main row */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
                {/* Rank */}
                <span style={{ fontSize: '0.7rem', color: '#444', width: '24px', flexShrink: 0, fontWeight: 900 }}>{String(index + 1).padStart(2, '0')}</span>
                
                {/* Feature label */}
                <span style={{ fontSize: '0.85rem', flex: 1, color: isRisk ? '#ffcccc' : '#fff', fontWeight: 600 }}>
                    {label}
                </span>

                {/* Direction badge */}
                <span style={{ 
                    fontSize: '0.6rem', 
                    letterSpacing: '1.5px', 
                    color: isRisk ? '#ff4444' : '#fff', 
                    background: isRisk ? '#ff444415' : '#ffffff10',
                    padding: '4px 10px',
                    fontWeight: 800,
                    flexShrink: 0,
                }}>
                    {isRisk ? '▲ RISK' : '▼ PROTECTIVE'}
                </span>

                {/* SHAP magnitude */}
                <span style={{ fontSize: '0.95rem', fontWeight: 900, width: '70px', textAlign: 'right', flexShrink: 0, color: isRisk ? '#ff4444' : '#fff' }}>
                    {shapMag.toFixed(3)}
                </span>

                {/* Expand */}
                <span style={{ color: '#444', fontSize: '0.8rem', transform: open ? 'rotate(90deg)' : 'none', transition: 'transform 0.2s' }}>▶</span>
            </div>

            {/* SHAP bar */}
            <div style={{ marginTop: '8px', height: '3px', background: '#0a0a0a', width: '100%' }}>
                <div style={{
                    height: '100%',
                    background: barColor,
                    width: `${Math.min(100, (shapMag / maxShap) * 100)}%`,
                    transition: 'width 0.4s',
                }} />
            </div>

            {/* Expanded explanation */}
            {open && (
                <div style={{ marginTop: '14px', paddingTop: '14px', borderTop: '1px solid #111' }}>

                    {/* Feature value */}
                    {feature.feature_value != null && (
                        <div style={{ marginBottom: '10px', display: 'flex', gap: '20px', alignItems: 'center' }}>
                            <div>
                                <div style={{ fontSize: '0.5rem', color: '#444', letterSpacing: '2px' }}>ACTUAL VALUE</div>
                                <div style={{ fontSize: '1rem', fontWeight: 700, color: isRisk ? '#ff4444' : '#fff', fontFamily: 'monospace' }}>
                                    {typeof feature.feature_value === 'number' ? feature.feature_value.toFixed(3) : String(feature.feature_value)}
                                </div>
                            </div>
                            <div>
                                <div style={{ fontSize: '0.5rem', color: '#444', letterSpacing: '2px' }}>SHAP IMPACT</div>
                                <div style={{ fontSize: '1rem', fontWeight: 700, color: isRisk ? '#ff4444' : '#aaa', fontFamily: 'monospace' }}>
                                    {feature.shap_value > 0 ? '+' : ''}{feature.shap_value.toFixed(4)}
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Plain-English explanation */}
                    <div style={{ background: '#000', border: '1px solid #111', padding: '24px', marginBottom: '14px' }}>
                        <div style={{ fontSize: '0.6rem', color: '#555', letterSpacing: '3px', marginBottom: '12px', fontWeight: 900 }}>AI ANALYSIS & INSIGHT</div>
                        <p style={{ fontSize: '0.85rem', color: '#fff', lineHeight: '1.9', margin: 0 }}>
                            {feature.explanation || (
                                isRisk 
                                    ? `Elevated risk detected on ${label}. Higher levels of this metric were found to be predictive of default in a training cohort of 60,000 corporate cases.`
                                    : `Positive variance on ${label} contributes to credit strength. This metric is within safer operational bounds as per ensemble logic.`
                            )}
                        </p>
                    </div>

                    {/* Industry benchmark */}
                    {hint && (
                        <div style={{ display: 'flex', alignItems: 'flex-start', gap: '8px' }}>
                            <span style={{ fontSize: '0.55rem', color: '#444', flexShrink: 0, paddingTop: '2px' }}>BENCHMARK:</span>
                            <span style={{ fontSize: '0.65rem', color: '#666', lineHeight: '1.5' }}>{hint.benchmark}</span>
                        </div>
                    )}
                </div>
            )}
        </div>
    )
}

/* ── Decision Box ──────────────────────── */
function DecisionBanner({ grade, dp, score }) {
    const dp_pct = (dp * 100).toFixed(1)
    let decision, reasoning, color
    if (dp < 0.05 && (grade === 'AAA' || grade === 'AA' || grade === 'A')) {
        decision = 'RECOMMEND: APPROVE'
        color = '#fff'
        reasoning = `Default probability of ${dp_pct}% is below the 5% threshold. Strong Five Cs composite.`
    } else if (dp < 0.15 && (grade === 'BBB' || grade === 'AA' || grade === 'A')) {
        decision = 'RECOMMEND: APPROVE WITH CONDITIONS'
        color = '#aaa'
        reasoning = `Default probability of ${dp_pct}% is within acceptable range. Enhanced monitoring recommended.`
    } else if (dp < 0.30) {
        decision = 'CAUTION: REFER TO CREDIT COMMITTEE'
        color = '#ff8800'
        reasoning = `Default probability of ${dp_pct}% exceeds standard threshold. Senior committee review required.`
    } else {
        decision = 'RECOMMEND: DECLINE'
        color = '#ff4444'
        reasoning = `Default probability of ${dp_pct}% is above the 30% hard limit. Multiple risk signals detected.`
    }
    return (
        <div style={{ border: `2px solid ${color}`, boxShadow: `0 0 40px ${color}10`, padding: '36px', background: '#000', marginBottom: '40px', display: 'flex', gap: '50px', alignItems: 'center' }}>
            <div style={{ flexShrink: 0 }}>
                <GradeRing grade={grade} score={score} />
            </div>
            <div style={{ flex: 1 }}>
                <div style={{ fontSize: '0.7rem', color: '#666', letterSpacing: '4px', marginBottom: '12px', fontWeight: 900 }}>AI PRELIMINARY RECOMMENDATION</div>
                <div style={{ fontSize: '1.8rem', fontWeight: 900, color, marginBottom: '20px', letterSpacing: '1px', lineHeight: 1.1 }}>{decision}</div>
                <p style={{ fontSize: '0.95rem', color: '#fff', lineHeight: '1.8', marginBottom: '24px', maxWidth: '600px' }}>{reasoning}</p>
                <div style={{ display: 'flex', gap: '20px', flexWrap: 'wrap' }}>
                    {[
                        { label: 'DEFAULT PROB', value: `${dp_pct}%`, accent: dp > 0.15 ? '#ff4444' : '#fff' },
                        { label: 'CREDIT SCORE', value: score, accent: '#fff' },
                        { label: 'RISK LEVEL',   value: dp > 0.3 ? 'CRITICAL' : dp > 0.15 ? 'HIGH' : 'LOW', accent: dp > 0.15 ? '#ff4444' : '#fff' },
                    ].map(s => (
                        <div key={s.label} style={{ border: '1px solid #1a1a1a', padding: '12px 24px', background: '#050505' }}>
                            <div style={{ fontSize: '0.6rem', color: '#555', letterSpacing: '2.5px', marginBottom: '6px', fontWeight: 900 }}>{s.label}</div>
                            <div style={{ fontSize: '1.4rem', fontWeight: 900, color: s.accent, fontFamily: 'monospace' }}>{s.value}</div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    )
}

/* ── MAIN ──────────────────────────────── */
export default function AnalysisPage() {
    const { caseId }  = useParams()
    const [analysis, setAnalysis] = useState(null)
    const [caseData, setCaseData] = useState(null)
    const [loading,  setLoading]  = useState(true)
    const [running,  setRunning]  = useState(false)
    const [tab,      setTab]      = useState('decision') // decision | shap | radar | narrative

    useEffect(() => { load() }, [caseId])

    const load = async () => {
        setLoading(true)
        try {
            const [aRes, cRes] = await Promise.allSettled([
                api.get(`/cases/${caseId}/analysis`),
                api.get(`/cases/${caseId}`),
            ])
            if (aRes.status === 'fulfilled') setAnalysis(aRes.value.data)
            if (cRes.status === 'fulfilled') setCaseData(cRes.value.data)
        } finally { setLoading(false) }
    }

    const runAnalysis = async () => {
        setRunning(true)
        try {
            await api.post(`/cases/${caseId}/analyze`, {})
            for (let i = 0; i < 25; i++) {
                await new Promise(r => setTimeout(r, 2500))
                try {
                    const res = await api.get(`/cases/${caseId}/analysis`)
                    setAnalysis(res.data)
                    break
                } catch { }
            }
        } finally { setRunning(false) }
    }

    if (loading) return (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '60vh', color: '#333', fontSize: '0.75rem', letterSpacing: '3px' }}>
            LOADING ANALYSIS...
        </div>
    )

    /* ── No analysis yet ── */
    if (!analysis) return (
        <div style={{ maxWidth: '700px', margin: '80px auto', textAlign: 'center' }}>
            <Brain size={56} style={{ color: '#111', marginBottom: '24px' }} />
            <h2 style={{ fontSize: '1.1rem', marginBottom: '10px' }}>ML ENSEMBLE IDLE</h2>
            <p style={{ color: '#444', fontSize: '0.7rem', lineHeight: '1.7', marginBottom: '40px', maxWidth: '500px', margin: '0 auto 40px' }}>
                The XGBoost + LightGBM + CatBoost stacking ensemble will score this entity on the Five Cs of Credit (Character, Capacity, Capital, Collateral, Conditions) using the 50-feature vector extracted from uploaded documents.
            </p>
            <button onClick={runAnalysis} disabled={running} style={{ padding: '16px 50px', fontWeight: 900, fontSize: '0.8rem', background: '#fff', color: '#000', border: 'none' }}>
                {running ? '⟳ ENGAGING MODELS...' : '▶ INITIALIZE ENSEMBLE'}
            </button>
        </div>
    )

    /* ── Data prep ── */
    const fiveCs     = analysis.five_cs_score || {}
    const shapRaw    = (analysis.shap_result?.feature_contributions || [])
    const shapData   = shapRaw.slice(0, 10).map(f => ({
        name:          (FEATURE_LABELS[f.feature_name] || f.feature_name.replace(/_/g, ' ').toUpperCase()).slice(0, 28),
        raw_name:      f.feature_name,
        impact:        f.direction === 'positive_risk' ? 'RISK' : 'PROTECTIVE',
        shap_value:    f.shap_value,
        feature_value: f.feature_value,
        explanation:   f.explanation || null,
    }))

    const barShap = shapRaw.slice(0, 12).map(f => ({
        name:  (FEATURE_LABELS[f.feature_name] || f.feature_name).replace(/_/g, ' ').slice(0, 22).toUpperCase(),
        value: Math.abs(f.shap_value),
        color: f.direction === 'positive_risk' ? '#ff4444' : '#555',
    }))

    const radarData = Object.entries(fiveCs)
        .filter(([k]) => k !== 'Composite')
        .map(([name, value]) => ({ name, value: +value.toFixed(1) }))

    const grade     = analysis.risk_grade       || 'N/A'
    const score     = analysis.credit_score     || 0
    const dp        = analysis.default_probability || 0
    const composite = fiveCs.Composite          || 0

    const TABS = [
        { id: 'decision',  label: 'DECISION' },
        { id: 'shap',      label: `TOP RISK DRIVERS (${shapData.length})` },
        { id: 'radar',     label: 'FIVE Cs RADAR' },
        { id: 'narrative', label: 'AI NARRATIVE' },
    ]

    return (
        <div style={{ maxWidth: '1100px', margin: '0 auto' }}>

            {/* Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginBottom: '25px', paddingBottom: '18px', borderBottom: '1px solid #1a1a1a' }}>
                <div>
                    <p style={{ fontSize: '0.55rem', color: '#555', letterSpacing: '3px', margin: 0 }}>ML SCORECARD</p>
                    <h1 style={{ margin: '6px 0 0', fontSize: '1.4rem', fontWeight: 900 }}>
                        {caseData?.company_name || 'ENSEMBLE ANALYSIS'}
                    </h1>
                </div>
                <div style={{ display: 'flex', gap: '10px' }}>
                    <button onClick={runAnalysis} disabled={running} style={{ padding: '10px 20px', fontSize: '0.6rem', background: '#000', color: running ? '#444' : '#fff' }}>
                        {running ? '⟳ RUNNING...' : '↺ RERUN'}
                    </button>
                    <Link to={`/cases/${caseId}/recommendation`} style={{ padding: '10px 20px', background: '#fff', color: '#000', fontSize: '0.6rem', fontWeight: 700, textDecoration: 'none', letterSpacing: '2px', display: 'flex', alignItems: 'center' }}>
                        GENERATE CAM →
                    </Link>
                </div>
            </div>

            {/* Tab bar */}
            <div style={{ display: 'flex', borderBottom: '1px solid #1a1a1a', marginBottom: '25px' }}>
                {TABS.map(t => (
                    <button key={t.id} onClick={() => setTab(t.id)} style={{
                        padding: '12px 20px',
                        fontSize: '0.6rem',
                        letterSpacing: '1px',
                        background: tab === t.id ? '#fff' : 'transparent',
                        color: tab === t.id ? '#000' : '#555',
                        border: 'none',
                        cursor: 'pointer',
                        fontWeight: tab === t.id ? 700 : 400,
                    }}>
                        {t.label}
                    </button>
                ))}
            </div>

            {/* ─── DECISION TAB ─── */}
            {tab === 'decision' && (
                <div>
                    <DecisionBanner grade={grade} dp={dp} score={score} />

                    {/* Five Cs summary table */}
                    <div style={{ border: '1px solid #1a1a1a', padding: '20px', marginBottom: '20px' }}>
                        <p style={{ fontSize: '0.55rem', color: '#444', letterSpacing: '3px', marginBottom: '16px' }}>FIVE Cs BREAKDOWN</p>
                        {Object.entries(fiveCs).filter(([k]) => k !== 'Composite').map(([c, v]) => {
                            const width = Math.min(100, Math.max(0, v))
                            const color = v >= 70 ? '#fff' : v >= 50 ? '#888' : '#ff4444'
                            return (
                                <div key={c} style={{ marginBottom: '14px' }}>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '5px' }}>
                                        <span style={{ fontSize: '0.65rem', color: '#777' }}>{c.toUpperCase()}</span>
                                        <span style={{ fontSize: '0.65rem', fontWeight: 700, color }}>{v.toFixed(0)}/100</span>
                                    </div>
                                    <div style={{ height: '4px', background: '#0f0f0f' }}>
                                        <div style={{ height: '100%', width: `${width}%`, background: color, transition: 'width 0.5s' }} />
                                    </div>
                                </div>
                            )
                        })}
                        <div style={{ marginTop: '16px', paddingTop: '12px', borderTop: '1px solid #111', display: 'flex', justifyContent: 'space-between' }}>
                            <span style={{ fontSize: '0.65rem', color: '#555' }}>COMPOSITE SCORE</span>
                            <span style={{ fontSize: '1rem', fontWeight: 900 }}>{composite.toFixed(0)}/100</span>
                        </div>
                    </div>
                </div>
            )}

            {/* ─── SHAP DRIVERS TAB ─── */}
            {tab === 'shap' && (
                <div>
                    <div style={{ marginBottom: '20px', background: '#050505', border: '1px solid #111', padding: '16px' }}>
                        <p style={{ fontSize: '0.65rem', color: '#777', lineHeight: '1.7' }}>
                            <strong style={{ color: '#fff' }}>SHAP (SHapley Additive exPlanations)</strong> breaks down how each feature pushed the final credit score up or down from the baseline.
                            A positive SHAP value increases predicted default risk (shown in red).
                            A negative SHAP value reduces predicted default risk (shown in grey).
                            Click any row to see the exact feature value, impact magnitude, and plain-English reasoning.
                        </p>
                    </div>

                    {/* SHAP waterfall bar chart */}
                    {barShap.length > 0 && (
                        <div style={{ border: '1px solid #1a1a1a', padding: '20px', marginBottom: '20px' }}>
                            <p style={{ fontSize: '0.55rem', color: '#444', letterSpacing: '2px', marginBottom: '15px' }}>FEATURE IMPORTANCE (|SHAP|)</p>
                            <div style={{ height: `${barShap.length * 30 + 30}px` }}>
                                <ResponsiveContainer width="100%" height="100%">
                                    <BarChart data={barShap} layout="vertical" margin={{ left: 180, right: 20 }}>
                                        <XAxis type="number" hide />
                                        <YAxis
                                            type="category"
                                            dataKey="name"
                                            tick={{ fill: '#666', fontSize: 9, fontFamily: 'monospace' }}
                                            width={180}
                                            tickLine={false}
                                        />
                                        <ReferenceLine x={0} stroke="#222" />
                                        <Bar dataKey="value" radius={0}>
                                            {barShap.map((entry, i) => (
                                                <Cell key={i} fill={entry.color} />
                                            ))}
                                        </Bar>
                                    </BarChart>
                                </ResponsiveContainer>
                            </div>
                            <div style={{ display: 'flex', gap: '20px', marginTop: '8px' }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                    <div style={{ width: '12px', height: '12px', background: '#ff4444' }} />
                                    <span style={{ fontSize: '0.55rem', color: '#555' }}>Increases Default Risk</span>
                                </div>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                    <div style={{ width: '12px', height: '12px', background: '#555' }} />
                                    <span style={{ fontSize: '0.55rem', color: '#555' }}>Reduces Default Risk</span>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Interactive SHAP cards */}
                    <p style={{ fontSize: '0.55rem', color: '#333', letterSpacing: '2px', marginBottom: '12px' }}>CLICK EACH DRIVER TO EXPAND EXPLANATION</p>
                    {shapData.length > 0
                        ? shapData.map((f, i) => <SHAPCard key={i} feature={f} index={i} />)
                        : <div style={{ textAlign: 'center', padding: '40px', color: '#333', fontSize: '0.7rem' }}>NO SHAP DATA — RERUN ANALYSIS</div>
                    }
                </div>
            )}

            {/* ─── RADAR TAB ─── */}
            {tab === 'radar' && (
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
                    <div style={{ border: '1px solid #1a1a1a', padding: '20px' }}>
                        <p style={{ fontSize: '0.55rem', color: '#444', letterSpacing: '2px', marginBottom: '15px' }}>FIVE Cs RADAR — {caseData?.company_name}</p>
                        <div style={{ height: '320px' }}>
                            <ResponsiveContainer width="100%" height="100%">
                                <RadarChart data={radarData} margin={{ top: 10, right: 40, bottom: 10, left: 40 }}>
                                    <PolarGrid stroke="#1a1a1a" />
                                    <PolarAngleAxis dataKey="name" tick={{ fill: '#555', fontSize: 11, fontFamily: 'monospace' }} />
                                    <Radar name="Score" dataKey="value" stroke="#fff" fill="#fff" fillOpacity={0.07} strokeWidth={2} />
                                    <Tooltip contentStyle={{ background: '#000', border: '1px solid #333', borderRadius: 0, fontSize: '11px', fontFamily: 'monospace' }} />
                                </RadarChart>
                            </ResponsiveContainer>
                        </div>
                    </div>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                        <div style={{ border: '1px solid #1a1a1a', padding: '20px', flex: 1 }}>
                            <p style={{ fontSize: '0.55rem', color: '#444', letterSpacing: '2px', marginBottom: '10px' }}>WHAT EACH "C" MEASURES</p>
                            {[
                                { c: 'Character',   desc: 'Management integrity, audit opinions, director DRT/CIRP links, MCA compliance history', score: fiveCs.Character },
                                { c: 'Capacity',     desc: 'DSCR, EBITDA margin, interest coverage, PAT trends, NACH bounce patterns', score: fiveCs.Capacity },
                                { c: 'Capital',      desc: 'Debt/Equity ratio, TOL/TNW, undisclosed borrowings, shareholder equity adequacy', score: fiveCs.Capital },
                                { c: 'Collateral',  desc: 'Security coverage ratio, nature of collateral, lien quality (RBI NPA guidelines)', score: fiveCs.Collateral },
                                { c: 'Conditions',  desc: 'Sector risk, GST compliance, circular trading, macro headwinds, ITC fraud signals', score: fiveCs.Conditions },
                            ].map(({ c, desc, score: s }) => (
                                <div key={c} style={{ marginBottom: '12px', paddingBottom: '12px', borderBottom: '1px solid #0a0a0a' }}>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                                        <span style={{ fontSize: '0.65rem', fontWeight: 700 }}>{c.toUpperCase()}</span>
                                        <span style={{ fontSize: '0.65rem', fontWeight: 700, color: s >= 70 ? '#fff' : s >= 50 ? '#888' : '#ff4444' }}>
                                            {s?.toFixed(0) ?? '?'}/100
                                        </span>
                                    </div>
                                    <p style={{ fontSize: '0.6rem', color: '#555', lineHeight: '1.5' }}>{desc}</p>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            )}

            {/* ─── NARRATIVE TAB ─── */}
            {tab === 'narrative' && (
                <div>
                    <div style={{ border: '1px solid #1a1a1a', padding: '40px', marginBottom: '30px', background: '#030303' }}>
                        <div style={{ fontSize: '0.7rem', color: '#666', letterSpacing: '4px', marginBottom: '24px', fontWeight: 900, borderBottom: '1px solid #111', paddingBottom: '12px' }}>AI-SYNTHESISED PRELIMINARY NARRATIVE</div>
                        <div style={{ fontSize: '0.95rem', color: '#fff', lineHeight: '2.1', whiteSpace: 'pre-line' }}>
                            {analysis.score_narrative || 'No narrative generated. Rerun the ensemble with sufficient feature data.'}
                        </div>
                    </div>

                    {analysis.model_details && (
                        <div style={{ border: '1px solid #1a1a1a', padding: '20px' }}>
                            <p style={{ fontSize: '0.55rem', color: '#444', letterSpacing: '2px', marginBottom: '12px' }}>MODEL METADATA</p>
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '15px' }}>
                                {Object.entries(analysis.model_details || {}).map(([k, v]) => (
                                    <div key={k}>
                                        <div style={{ fontSize: '0.5rem', color: '#444', letterSpacing: '2px', marginBottom: '4px' }}>{k.toUpperCase().replace('_', ' ')}</div>
                                        <div style={{ fontSize: '0.7rem', fontFamily: 'monospace', color: '#888' }}>{String(v)}</div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            )}
        </div>
    )
}
