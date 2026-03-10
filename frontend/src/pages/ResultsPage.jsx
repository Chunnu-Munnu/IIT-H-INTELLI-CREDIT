import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import {
    LineChart, Line, BarChart, Bar, XAxis, YAxis, Tooltip,
    ResponsiveContainer, ReferenceLine
} from 'recharts'
import api from '../services/api'

/* ── Helpers ──────────────────────────────── */
const crore  = p => (p != null && p !== 0) ? `₹${(p / 10000000 / 100).toFixed(2)} Cr` : '—'
const pct    = v => (v != null) ? `${(v * 100).toFixed(1)}%` : '—'
const round2 = v => (v != null) ? (+v).toFixed(2) : '—'

const SEVERITY_COLOR = { CRITICAL: '#ff3333', HIGH: '#ff8800', MEDIUM: '#ffcc00', LOW: '#666' }
const SEVERITY_BG    = { CRITICAL: '#1a0000', HIGH: '#1a0800', MEDIUM: '#1a1400', LOW: '#0a0a0a' }

/* ── Sub-components ───────────────────────── */
function StatBox({ label, value, accent }) {
    return (
        <div style={{ background: '#000', border: '1px solid #222', padding: '18px' }}>
            <div style={{ fontSize: '0.55rem', color: '#fff', letterSpacing: '2px', marginBottom: '8px' }}>{label}</div>
            <div style={{ fontSize: '1.3rem', fontWeight: 900, color: accent || '#fff' }}>{value ?? '—'}</div>
        </div>
    )
}

function SectionHeader({ title, badge }) {
    return (
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '18px', paddingBottom: '12px', borderBottom: '1px solid #1a1a1a' }}>
            <h2 style={{ fontSize: '0.75rem', fontWeight: 700, letterSpacing: '3px', margin: 0 }}>{title}</h2>
            {badge && <span style={{ fontSize: '0.55rem', border: '1px solid #444', color: '#fff', padding: '2px 8px', letterSpacing: '1px' }}>{badge}</span>}
        </div>
    )
}

/* ── EWS Flag card with precise evidence ─── */
function EWSFlagCard({ flag, index }) {
    const [open, setOpen] = useState(false)
    const color = SEVERITY_COLOR[flag.severity] || '#666'
    const bg    = SEVERITY_BG[flag.severity]    || '#0a0a0a'

    return (
        <div style={{ border: `1px solid ${color}30`, background: bg, marginBottom: '8px' }}>
            {/* Header row — always visible */}
            <div
                onClick={() => setOpen(o => !o)}
                style={{
                    padding: '14px 18px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '12px',
                    cursor: 'pointer',
                    userSelect: 'none',
                }}
            >
                {/* Severity pill */}
                <span style={{
                    fontSize: '0.55rem',
                    fontWeight: 700,
                    letterSpacing: '1px',
                    color,
                    border: `1px solid ${color}`,
                    padding: '2px 8px',
                    flexShrink: 0,
                }}>
                    {flag.severity}
                </span>

                {/* Flag name */}
                <span style={{ fontSize: '0.75rem', fontWeight: 700, flex: 1, fontFamily: 'monospace' }}>
                    {flag.flag_name.replace(/_/g, ' ')}
                </span>

                {/* Five-C impact */}
                <span style={{ fontSize: '0.6rem', color: '#fff', flexShrink: 0 }}>
                    {flag.five_c_impact}
                </span>

                {/* Score deduction */}
                <span style={{ fontSize: '0.8rem', fontWeight: 900, color: '#ff4444', flexShrink: 0, width: '50px', textAlign: 'right' }}>
                    -{flag.score_deduction}
                </span>

                {/* Expand chevron */}
                <span style={{ color: '#fff', fontSize: '0.7rem', flexShrink: 0, transform: open ? 'rotate(90deg)' : 'none', transition: 'transform 0.15s' }}>▶</span>
            </div>

            {/* Expanded detail */}
            {open && (
                <div style={{ borderTop: `1px solid ${color}20`, padding: '18px' }}>

                    {/* Evidence text */}
                    {flag.evidence_summary && (
                        <div style={{ marginBottom: '16px' }}>
                            <div style={{ fontSize: '0.55rem', color: '#fff', letterSpacing: '2px', marginBottom: '8px' }}>EVIDENCE SUMMARY</div>
                            <div style={{ fontSize: '0.75rem', color: '#ccc', lineHeight: '1.7', borderLeft: `3px solid ${color}`, paddingLeft: '12px', fontFamily: 'monospace' }}>
                                {flag.evidence_summary}
                            </div>
                        </div>
                    )}

                    {/* Source documents with page numbers */}
                    {flag.source_documents?.length > 0 && (
                        <div style={{ marginBottom: '16px' }}>
                            <div style={{ fontSize: '0.55rem', color: '#555', letterSpacing: '2px', marginBottom: '8px' }}>SOURCE DOCUMENTS</div>
                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                                {flag.source_documents.filter(Boolean).map((src, i) => (
                                    <span key={i} style={{
                                        fontSize: '0.6rem',
                                        border: '1px solid #333',
                                        padding: '3px 10px',
                                        color: '#fff',
                                        fontFamily: 'monospace',
                                    }}>
                                        📄 {src}
                                    </span>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Context text snippet (from risk_signals) */}
                    {flag.context_text && (
                        <div>
                            <div style={{ fontSize: '0.55rem', color: '#fff', letterSpacing: '2px', marginBottom: '8px' }}>EXTRACTED CONTEXT (from document)</div>
                            <pre style={{
                                fontSize: '0.65rem',
                                color: '#fff',
                                background: '#050505',
                                border: '1px solid #1a1a1a',
                                padding: '12px',
                                whiteSpace: 'pre-wrap',
                                wordBreak: 'break-word',
                                lineHeight: '1.6',
                                fontFamily: 'monospace',
                                maxHeight: '150px',
                                overflow: 'auto',
                            }}>
                                {flag.context_text}
                            </pre>
                        </div>
                    )}

                    {/* Keyword matched */}
                    {flag.keyword_matched && (
                        <div style={{ marginTop: '10px', display: 'flex', gap: '8px', alignItems: 'center' }}>
                            <span style={{ fontSize: '0.55rem', color: '#fff' }}>KEYWORD HIT:</span>
                            <code style={{ fontSize: '0.65rem', color: color, background: '#111', padding: '2px 8px', border: `1px solid ${color}40` }}>
                                "{flag.keyword_matched}"
                            </code>
                            {flag.page_number > 0 && (
                                <span style={{ fontSize: '0.6rem', color: '#fff' }}>on page {flag.page_number}</span>
                            )}
                            {flag.confidence && (
                                <span style={{ fontSize: '0.6rem', color: '#fff', marginLeft: 'auto' }}>
                                    confidence: {(flag.confidence * 100).toFixed(0)}%
                                </span>
                            )}
                        </div>
                    )}
                </div>
            )}
        </div>
    )
}

/* ── Ratio row ─────────────────────────────── */
function RatioRow({ label, value, benchmark, unit = '', good = 'high' }) {
    if (value == null) return null
    const ok = good === 'high' ? value >= (benchmark || 0) : value <= (benchmark || 999)
    return (
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 0', borderBottom: '1px solid #0f0f0f' }}>
            <span style={{ fontSize: '0.65rem', color: '#fff' }}>{label}</span>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                {benchmark != null && (
                    <span style={{ fontSize: '0.55rem', color: '#fff' }}>benchmark: {benchmark}{unit}</span>
                )}
                <span style={{ fontSize: '0.75rem', fontWeight: 700, color: ok ? '#fff' : '#ff4444' }}>
                    {round2(value)}{unit}
                </span>
                <span style={{ fontSize: '0.65rem' }}>{ok ? '✓' : '✗'}</span>
            </div>
        </div>
    )
}

/* ── MAIN PAGE ─────────────────────────────── */
export default function ResultsPage() {
    const { caseId } = useParams()
    const [results,  setResults]  = useState(null)
    const [ews,      setEws]      = useState(null)
    const [ratios,   setRatios]   = useState([])
    const [caseData, setCaseData] = useState(null)
    const [loading,  setLoading]  = useState(true)
    const [tab,      setTab]      = useState('ews') // ews | gst | ratios

    useEffect(() => {
        const load = async () => {
            try {
                const [rRes, ewsRes, ratioRes, caseRes] = await Promise.allSettled([
                    api.get(`/cases/${caseId}/results`),
                    api.get(`/cases/${caseId}/ews`),
                    api.get(`/cases/${caseId}/ratios`),
                    api.get(`/cases/${caseId}`),
                ])
                if (rRes.status === 'fulfilled')   setResults(rRes.value.data)
                if (ewsRes.status === 'fulfilled')  setEws(ewsRes.value.data)
                if (ratioRes.status === 'fulfilled')setRatios(ratioRes.value.data.ratios || [])
                if (caseRes.status === 'fulfilled') setCaseData(caseRes.value.data)
            } finally { setLoading(false) }
        }
        load()
    }, [caseId])

    if (loading) return (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '60vh', color: '#fff', fontSize: '0.75rem', letterSpacing: '3px' }}>
            LOADING AUDIT DATA...
        </div>
    )

    if (!results && !ews) return (
        <div style={{ textAlign: 'center', padding: '100px', color: '#fff' }}>
            <div style={{ color: '#fff', fontSize: '0.75rem', marginBottom: '8px' }}>INSUFFICIENT DATA</div>
            <p style={{ fontSize: '0.65rem', color: '#fff' }}>Awaiting GST and bank statement reconciliation...</p>
        </div>
    )

    const gstBank   = results?.gst_bank_reconciliation  || {}
    const gstInternal = results?.gst_internal_reconciliation || {}
    const circular  = results?.circular_trading_summary  || {}

    const allFlags       = ews?.flags || []
    const triggeredFlags = allFlags.filter(f => f.triggered)
    const clearFlags     = allFlags.filter(f => !f.triggered)

    // Enrich flags with risk_signal context when available
    const riskSignals   = results?.risk_signals || []
    const enrichedFlags = triggeredFlags.map(flag => {
        const signal = riskSignals.find(s =>
            s.signal_type?.includes(flag.flag_name.replace('_DOUBT','').replace('_DETECTED','')) ||
            flag.flag_name.includes(s.signal_type?.replace('AUDITOR_QUALIFICATION','AUDITOR'))
        )
        return {
            ...flag,
            context_text:    signal?.context_text    || null,
            keyword_matched: signal?.keyword_matched || null,
            page_number:     signal?.page_number     || 0,
            confidence:      signal?.confidence      || null,
        }
    })

    const ratioChartData = ratios.map(r => ({
        period:   r.period?.fy_label || 'N/A',
        DSCR:     r.dscr             ? +r.dscr.toFixed(2)                  : null,
        'D/E':    r.debt_equity      ? +r.debt_equity.toFixed(2)           : null,
        'EBITDA': r.ebitda_margin    ? +(r.ebitda_margin * 100).toFixed(1) : null,
        'PAT':    r.pat_margin       ? +(r.pat_margin * 100).toFixed(1)     : null,
        'ICR':    r.interest_coverage ? +r.interest_coverage.toFixed(2)    : null,
    })).reverse()

    const latestRatio = ratios[0] || {}

    const TABS = [
        { id: 'ews',    label: `EWS FLAGS (${triggeredFlags.length})` },
        { id: 'gst',    label: 'GST ANALYSIS' },
        { id: 'ratios', label: 'FINANCIAL RATIOS' },
        { id: 'asset_debt', label: 'ASSET & DEBT' },
        { id: 'docs',   label: 'DOCUMENTS' },
    ]

    return (
        <div style={{ maxWidth: '1100px', margin: '0 auto' }}>

            {/* ── Page Header ── */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginBottom: '30px', paddingBottom: '20px', borderBottom: '1px solid #1a1a1a' }}>
                <div>
                    <p style={{ fontSize: '0.55rem', color: '#fff', letterSpacing: '3px', margin: 0 }}>EXTRACTION RESULTS & AUDIT</p>
                    <h1 style={{ margin: '6px 0 0', fontSize: '1.4rem', fontWeight: 900 }}>
                        {caseData?.company_name || 'CASE RESULTS'}
                    </h1>
                    <p style={{ fontSize: '0.6rem', color: '#fff', margin: '4px 0 0', fontFamily: 'monospace' }}>
                        ID: {caseId}
                    </p>
                </div>
                <Link
                    to={`/cases/${caseId}/analysis`}
                    style={{ padding: '12px 25px', background: '#fff', color: '#000', fontWeight: 700, fontSize: '0.65rem', textDecoration: 'none', letterSpacing: '2px' }}
                >
                    RUN ML ENSEMBLE →
                </Link>
            </div>

            {/* ── Summary KPIs ── */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '1px', background: '#111', marginBottom: '30px' }}>
                <StatBox label="EWS RISK" value={ews?.overall_risk_classification}
                    accent={SEVERITY_COLOR[ews?.overall_risk_classification]} />
                <StatBox label="FLAGS TRIGGERED" value={`${ews?.triggered_count ?? 0} / ${allFlags.length}`}
                    accent={triggeredFlags.length > 0 ? '#ff4444' : '#fff'} />
                <StatBox label="CRITICAL FLAGS" value={ews?.critical_count ?? 0}
                    accent={ews?.critical_count > 0 ? '#ff3333' : '#fff'} />
                <StatBox label="SCORE DEDUCTION" value={`-${ews?.total_score_deduction ?? 0} pts`}
                    accent={ews?.total_score_deduction > 20 ? '#ff4444' : '#fff'} />
                <StatBox label="LATEST DSCR" value={round2(latestRatio.dscr)}
                    accent={latestRatio.dscr >= 1.25 ? '#fff' : '#ff8800'} />
            </div>

            {/* ── Tab bar ── */}
            <div style={{ display: 'flex', borderBottom: '1px solid #1a1a1a', marginBottom: '25px' }}>
                {TABS.map(t => (
                    <button key={t.id} onClick={() => setTab(t.id)} style={{
                        padding: '12px 24px',
                        fontSize: '0.6rem',
                        letterSpacing: '1px',
                        background: tab === t.id ? '#fff' : 'transparent',
                        color: tab === t.id ? '#000' : '#fff',
                        border: 'none',
                        borderBottom: tab === t.id ? '2px solid #fff' : '2px solid transparent',
                        cursor: 'pointer',
                        fontWeight: tab === t.id ? 700 : 400,
                    }}>
                        {t.label}
                    </button>
                ))}
            </div>

            {/* ────────────── TAB: EWS FLAGS ────────────── */}
            {tab === 'ews' && (
                <div>
                    {triggeredFlags.length === 0 ? (
                        <div style={{ textAlign: 'center', padding: '60px', border: '1px solid #111', color: '#fff', fontSize: '0.75rem' }}>
                            ✓ NO EARLY WARNING FLAGS TRIGGERED — ALL CLEAR
                        </div>
                    ) : (
                        <div style={{ marginBottom: '30px' }}>
                            <p style={{ fontSize: '0.6rem', color: '#fff', marginBottom: '15px', letterSpacing: '1px' }}>
                                CLICK A FLAG TO EXPAND EVIDENCE, SOURCE DOCUMENTS, AND EXTRACTED CONTEXT TEXT
                            </p>
                            {enrichedFlags.map((flag, i) => (
                                <EWSFlagCard key={i} flag={flag} index={i} />
                            ))}
                        </div>
                    )}

                    {clearFlags.length > 0 && (
                        <div style={{ marginTop: '25px' }}>
                            <p style={{ fontSize: '0.55rem', color: '#fff', letterSpacing: '2px', marginBottom: '12px' }}>ALL CLEAR CHECKS ({clearFlags.length})</p>
                            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1px', background: '#111' }}>
                                {clearFlags.map((flag, i) => (
                                    <div key={i} style={{ background: '#000', padding: '10px 14px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                                        <span style={{ color: '#2a2a2a', fontSize: '0.7rem' }}>✓</span>
                                        <span style={{ fontSize: '0.6rem', color: '#fff', fontFamily: 'monospace' }}>
                                            {flag.flag_name.replace(/_/g, ' ')}
                                        </span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            )}

            {/* ────────────── TAB: GST ANALYSIS ────────────── */}
            {tab === 'gst' && (
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>

                    {/* GST vs Bank */}
                    <div style={{ border: '1px solid #1a1a1a', padding: '20px' }}>
                        <SectionHeader title="GST VS BANK RECONCILIATION" badge="REVENUE LAYER" />
                        <RatioRow label="GST Annual Turnover"   value={gstBank.gst_annual_paise  ? gstBank.gst_annual_paise  / 10000000 / 100 : null} unit=" Cr" />
                        <RatioRow label="Bank Annual Deposits"  value={gstBank.bank_annual_paise ? gstBank.bank_annual_paise / 10000000 / 100 : null} unit=" Cr" />
                        <RatioRow label="Inflation Ratio"       value={gstBank.overall_ratio} benchmark={1.15} good="low" />
                        <div style={{ marginTop: '15px', padding: '12px', background: '#050505', borderLeft: `3px solid ${gstBank.flag_triggered ? '#ff4444' : '#333'}`, fontSize: '0.65rem', color: '#fff', lineHeight: '1.7' }}>
                            {gstBank.narrative || 'Awaiting GST and bank statement reconciliation.'}
                        </div>
                        {gstBank.monthly_ratios && (
                            <div style={{ marginTop: '15px' }}>
                                <p style={{ fontSize: '0.55rem', color: '#fff', marginBottom: '8px', letterSpacing: '1px' }}>MONTHLY INFLATION RATIO</p>
                                <div style={{ height: '120px' }}>
                                    <ResponsiveContainer width="100%" height="100%">
                                        <BarChart data={Object.entries(gstBank.monthly_ratios || {}).map(([m, v]) => ({ month: m.slice(5), ratio: v ? +v.toFixed(2) : 0 }))}>
                                            <XAxis dataKey="month" tick={{ fill:'#fff', fontSize:8 }} tickLine={false} />
                                            <YAxis tick={{ fill:'#fff', fontSize:8 }} tickLine={false} />
                                            <ReferenceLine y={1.15} stroke="#ff4444" strokeDasharray="3 3" />
                                            <Bar dataKey="ratio" fill="#fff" />
                                        </BarChart>
                                    </ResponsiveContainer>
                                </div>
                            </div>
                        )}
                    </div>

                    {/* ITC / Internal GST */}
                    <div style={{ border: '1px solid #1a1a1a', padding: '20px' }}>
                        <SectionHeader title="ITC FRAUD CHECK" badge="INPUT TAX CREDIT" />
                        <RatioRow label="ITC Excess Claim"        value={gstInternal.itc_excess_claim_paise ? gstInternal.itc_excess_claim_paise / 10000000 / 100 : 0} unit=" Cr" benchmark={0} good="low" />
                        <RatioRow label="ITC Utilisation Rate"    value={gstInternal.itc_utilisation_rate} benchmark={0.95} good="low" />
                        <RatioRow label="Turnover Suppression"    value={gstInternal.turnover_suppression_pct ? gstInternal.turnover_suppression_pct : null} unit="%" benchmark={5} good="low" />

                        <div style={{ marginTop: '15px', display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                            {[
                                { label: 'ITC INFLATION', flag: gstInternal.itc_inflation_flag },
                                { label: 'TURNOVER SUPP.', flag: gstInternal.turnover_suppression_flag },
                            ].map(({ label, flag }) => (
                                <span key={label} style={{
                                    fontSize: '0.6rem',
                                    border: `1px solid ${flag ? '#ff4444' : '#222'}`,
                                    color: flag ? '#ff4444' : '#fff',
                                    padding: '4px 10px',
                                }}>
                                    {label}: {flag ? '⚠ FLAGGED' : '✓ OK'}
                                </span>
                            ))}
                        </div>

                        <div style={{ marginTop: '15px', padding: '12px', background: '#050505', borderLeft: `3px solid ${gstInternal.itc_inflation_flag ? '#ff4444' : '#333'}`, fontSize: '0.65rem', color: '#fff', lineHeight: '1.7' }}>
                            {gstInternal.itc_narrative || 'No ITC anomalies detected or insufficient data.'}
                        </div>

                        {/* Circular trading */}
                        <div style={{ marginTop: '20px', paddingTop: '15px', borderTop: '1px solid #111' }}>
                            <p style={{ fontSize: '0.55rem', color: '#fff', letterSpacing: '2px', marginBottom: '10px' }}>CIRCULAR TRADING GRAPH</p>
                            {[
                                { label: 'Cycles Detected',     value: circular.total_cycles_detected ?? 0 },
                                { label: 'High-Value Cycles',   value: circular.high_value_cycles ?? 0 },
                                { label: 'Value at Risk',       value: circular.total_value_at_risk_paise ? crore(circular.total_value_at_risk_paise) : '₹0' },
                                { label: 'Graph Risk Level',    value: circular.risk_level || 'LOW' },
                            ].map(({ label, value }) => (
                                <div key={label} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid #0a0a0a', fontSize: '0.65rem' }}>
                                    <span style={{ color: '#fff' }}>{label}</span>
                                    <span style={{ fontWeight: 700 }}>{value}</span>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            )}

            {/* ────────────── TAB: FINANCIAL RATIOS ────────────── */}
            {tab === 'ratios' && (
                <div>
                    {ratios.length === 0 ? (
                        <div style={{ textAlign: 'center', padding: '60px', color: '#fff', fontSize: '0.7rem' }}>
                            NO FINANCIAL RATIO DATA — UPLOAD ANNUAL REPORTS WITH FINANCIAL TABLES
                        </div>
                    ) : (
                        <div>
                            {/* Ratio trend chart */}
                            <div style={{ border: '1px solid #1a1a1a', padding: '20px', marginBottom: '20px' }}>
                                <SectionHeader title="KEY RATIO TRENDS (FY SERIES)" />
                                <div style={{ height: '280px' }}>
                                    <ResponsiveContainer width="100%" height="100%">
                                        <LineChart data={ratioChartData} margin={{ left: 0, right: 20 }}>
                                            <XAxis dataKey="period" stroke="#222" tick={{ fill: '#fff', fontSize: 10 }} tickLine={false} />
                                            <YAxis stroke="#222" tick={{ fill: '#fff', fontSize: 10 }} tickLine={false} />
                                            <Tooltip contentStyle={{ background: '#000', border: '1px solid #333', borderRadius: 0, fontSize: '11px', fontFamily: 'monospace' }} />
                                            <ReferenceLine y={1.25} stroke="#ff8800" strokeDasharray="4 4" label={{ value: 'DSCR 1.25x', fill: '#ff8800', fontSize: 9 }} />
                                            <Line type="monotone" dataKey="DSCR"  stroke="#fff"    strokeWidth={2} dot={{ r: 4, fill: '#000', stroke: '#fff' }}    name="DSCR" />
                                            <Line type="monotone" dataKey="EBITDA" stroke="#666"  strokeWidth={1} dot={{ r: 3, fill: '#000', stroke: '#666' }}    name="EBITDA%" />
                                            <Line type="monotone" dataKey="D/E"   stroke="#444"   strokeWidth={1} strokeDasharray="5 5" dot={false}              name="D/E Ratio" />
                                            <Line type="monotone" dataKey="ICR"   stroke="#888"   strokeWidth={1} dot={{ r: 3, fill: '#000', stroke: '#888' }}    name="ICR" />
                                        </LineChart>
                                    </ResponsiveContainer>
                                </div>
                                <div style={{ display: 'flex', gap: '20px', marginTop: '10px', flexWrap: 'wrap' }}>
                                    {[
                                        { color: '#fff',  label: 'DSCR' },
                                        { color: '#666',  label: 'EBITDA %' },
                                        { color: '#444',  label: 'D/E Ratio' },
                                        { color: '#888',  label: 'ICR' },
                                        { color: '#ff8800', label: 'DSCR 1.25x Benchmark', dashed: true },
                                    ].map(l => (
                                        <div key={l.label} style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                            <div style={{ width: '20px', height: '2px', background: l.color, borderStyle: l.dashed ? 'dashed' : 'solid' }} />
                                            <span style={{ fontSize: '0.55rem', color: '#fff' }}>{l.label}</span>
                                        </div>
                                    ))}
                                </div>
                            </div>

                            {/* Per-year ratio table */}
                            {ratios.map((r, i) => (
                                <div key={i} style={{ border: '1px solid #1a1a1a', padding: '20px', marginBottom: '15px' }}>
                                    <SectionHeader title={`FY RATIOS — ${r.period?.fy_label || 'UNKNOWN PERIOD'}`} badge={r.period?.period_type} />
                                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0 30px' }}>
                                        <div>
                                            <p style={{ fontSize: '0.55rem', color: '#fff', letterSpacing: '2px', marginBottom: '8px', marginTop: '5px' }}>CAPACITY</p>
                                            <RatioRow label="DSCR"              value={r.dscr}             benchmark={1.25} good="high" />
                                            <RatioRow label="Interest Coverage" value={r.interest_coverage} benchmark={2.5}  good="high" />
                                            <RatioRow label="EBITDA Margin"     value={r.ebitda_margin}     benchmark={0.10} unit="x"    good="high" />
                                            <RatioRow label="PAT Margin"        value={r.pat_margin}       benchmark={0.05} unit="x"    good="high" />
                                        </div>
                                        <div>
                                            <p style={{ fontSize: '0.55rem', color: '#fff', letterSpacing: '2px', marginBottom: '8px', marginTop: '5px' }}>CAPITAL STRUCTURE</p>
                                            <RatioRow label="Debt / Equity"     value={r.debt_equity}      benchmark={3.0}  good="low" />
                                            <RatioRow label="TOL / TNW"         value={r.tol_tnw}          benchmark={4.0}  good="low" />
                                            <RatioRow label="Current Ratio"     value={r.current_ratio}    benchmark={1.33} good="high" />
                                            <RatioRow label="Quick Ratio"       value={r.quick_ratio}      benchmark={1.0}  good="high" />
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}

            {/* ────────────── TAB: ASSET & DEBT ────────────── */}
            {tab === 'asset_debt' && (
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
                    
                    {/* Shareholding Card */}
                    <div style={{ border: '1px solid #1a1a1a', padding: '20px' }}>
                        <SectionHeader title="SHAREHOLDING PATTERN" badge="EQUITY STAKE" />
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
                            {[
                                { label: 'PROMOTER HOLDING', value: (results?.shareholding_data?.promoter_pct || 0), color: '#fff' },
                                { label: 'PUBLIC HOLDING', value: (results?.shareholding_data?.public_pct || 0), color: '#666' },
                                { label: 'PLEDGED SHARES', value: (results?.shareholding_data?.pledged_pct || 0), color: '#ff4444' },
                                { label: 'INSTITUTIONAL', value: (results?.shareholding_data?.institutional_pct || 0), color: '#aaa' },
                            ].map(sh => (
                                <div key={sh.label}>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px', fontSize: '0.6rem', letterSpacing: '1px' }}>
                                        <span style={{ color: '#fff' }}>{sh.label}</span>
                                        <span style={{ fontWeight: 700 }}>{(sh.value * 100).toFixed(1)}%</span>
                                    </div>
                                    <div style={{ height: '4px', background: '#111', width: '100%' }}>
                                        <div style={{ height: '100%', background: sh.color, width: `${Math.min(100, sh.value * 100)}%` }} />
                                    </div>
                                </div>
                            ))}
                        </div>
                        {results?.shareholding_data?.pledged_pct > 0.1 && (
                            <div style={{ marginTop: '20px', padding: '10px', background: '#1a0800', border: '1px solid #ff880040', color: '#ff8800', fontSize: '0.65rem' }}>
                                ⚠ HIGH PROMOTER PLEDGE DETECTED ({(results.shareholding_data.pledged_pct * 100).toFixed(1)}%)
                            </div>
                        )}
                    </div>

                    {/* Borrowing Profile */}
                    <div style={{ border: '1px solid #1a1a1a', padding: '20px' }}>
                        <SectionHeader title="BORROWING PROFILE" badge="CREDIT FACILITIES" />
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '1px', background: '#111' }}>
                            {(results?.borrowing_profile?.lenders || []).map((l, i) => (
                                <div key={i} style={{ background: '#000', padding: '10px 14px', display: 'grid', gridTemplateColumns: '2fr 1fr 1fr', gap: '10px', alignItems: 'center' }}>
                                    <span style={{ fontSize: '0.7rem', fontWeight: 700, color: '#fff' }}>{l.bank_name}</span>
                                    <span style={{ fontSize: '0.6rem', color: '#fff' }}>{l.facility_type}</span>
                                    <span style={{ fontSize: '0.7rem', textAlign: 'right', fontWeight: 900 }}>{crore(l.limit_paise)}</span>
                                </div>
                            ))}
                            {(results?.borrowing_profile?.lenders || []).length === 0 && (
                                <div style={{ background: '#000', padding: '20px', textAlign: 'center', color: '#fff', fontSize: '0.65rem' }}>
                                    NO LENDER DATA EXTRACTED
                                </div>
                            )}
                        </div>
                    </div>

                    {/* ALM Card (Full width row) */}
                    <div style={{ gridColumn: '1 / span 2', border: '1px solid #1a1a1a', padding: '20px' }}>
                        <SectionHeader title="ASSET LIABILITY MATURITY (ALM)" badge="LIQUIDITY RISK" />
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: '1px', background: '#111', border: '1px solid #111' }}>
                            {['BUCKET', 'INFLOWS', 'OUTFLOWS', 'NET GAP', 'GAP %', 'CUM. GAP'].map(h => (
                                <div key={h} style={{ background: '#050505', padding: '10px', fontSize: '0.55rem', color: '#555', letterSpacing: '1px', textAlign: 'center' }}>{h}</div>
                            ))}
                            {(results?.alm_data?.buckets || []).map((b, i) => (
                                <>
                                    <div style={{ background: '#000', padding: '12px', fontSize: '0.65rem', textAlign: 'center', color: '#888' }}>{b.bucket_name}</div>
                                    <div style={{ background: '#000', padding: '12px', fontSize: '0.65rem', textAlign: 'center' }}>{crore(b.inflow_paise)}</div>
                                    <div style={{ background: '#000', padding: '12px', fontSize: '0.65rem', textAlign: 'center' }}>{crore(b.outflow_paise)}</div>
                                    <div style={{ background: '#000', padding: '12px', fontSize: '0.65rem', textAlign: 'center', color: b.gap_paise < 0 ? '#ff4444' : '#fff' }}>{crore(b.gap_paise)}</div>
                                    <div style={{ background: '#000', padding: '12px', fontSize: '0.65rem', textAlign: 'center', color: b.gap_pct < -0.15 ? '#ff4444' : '#fff' }}>{(b.gap_pct * 100).toFixed(1)}%</div>
                                    <div style={{ background: '#000', padding: '12px', fontSize: '0.65rem', textAlign: 'center' }}>{crore(b.cumulative_gap_paise)}</div>
                                </>
                            ))}
                        </div>
                        {(results?.alm_data?.buckets || []).length === 0 && (
                            <div style={{ background: '#000', padding: '40px', textAlign: 'center', color: '#fff', fontSize: '0.7rem' }}>
                                NO ALM DATA AVAILABLE FOR THIS CASE
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    )
}
