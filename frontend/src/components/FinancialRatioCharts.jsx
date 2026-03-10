import { BarChart, Bar, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer, LineChart, Line, CartesianGrid, ReferenceLine } from 'recharts'

const RATIO_BENCHMARKS = {
    DSCR: { good: 1.5, warn: 1.25 },
    'D/E': { good: 2.0, warn: 3.0, invert: true },
    'EBITDA%': { good: 12, warn: 8 },
    'PAT%': { good: 5, warn: 2 },
    'Curr. Ratio': { good: 1.5, warn: 1.0 },
    ROCE: { good: 15, warn: 10 },
}

function RatioBar({ name, value, benchmark }) {
    if (value == null) return null
    const pct = benchmark.invert
        ? Math.max(0, Math.min(100, (1 - value / (benchmark.warn * 2)) * 100))
        : Math.max(0, Math.min(100, (value / (benchmark.good * 1.5)) * 100))
    const color = benchmark.invert
        ? value > benchmark.warn ? '#ef4444' : value > benchmark.good ? '#f59e0b' : '#22c55e'
        : value >= benchmark.good ? '#22c55e' : value >= benchmark.warn ? '#f59e0b' : '#ef4444'

    return (
        <div className="mb-3">
            <div className="flex justify-between text-sm mb-1">
                <span className="text-slate-400">{name}</span>
                <span className="font-semibold" style={{ color }}>{typeof value === 'number' ? value.toFixed(2) : value}</span>
            </div>
            <div className="bg-slate-800 rounded-full h-2">
                <div className="h-2 rounded-full transition-all duration-1000" style={{ width: pct + '%', background: color }} />
            </div>
        </div>
    )
}

export default function FinancialRatioCharts({ ratios = [], latestRatios = {} }) {
    // Build trend data
    const trendData = ratios.map(r => ({
        period: r.period?.fy_label || 'N/A',
        DSCR: r.dscr != null ? +r.dscr.toFixed(2) : null,
        'D/E': r.debt_equity != null ? +r.debt_equity.toFixed(2) : null,
        'EBITDA%': r.ebitda_margin != null ? +(r.ebitda_margin * 100).toFixed(1) : null,
        'PAT%': r.pat_margin != null ? +(r.pat_margin * 100).toFixed(1) : null,
        'Curr. Ratio': r.current_ratio != null ? +r.current_ratio.toFixed(2) : null,
        ROCE: r.roce != null ? +(r.roce * 100).toFixed(1) : null,
    })).reverse()

    return (
        <div className="space-y-6">
            {/* Current Ratio Gauges */}
            <div className="card p-5">
                <div className="text-sm font-semibold text-slate-300 mb-4">Latest Year — Key Ratios</div>
                <div className="grid grid-cols-2 gap-6">
                    <div>
                        <RatioBar name="DSCR (Debt Service Coverage)" value={latestRatios.dscr} benchmark={RATIO_BENCHMARKS.DSCR} />
                        <RatioBar name="Debt/Equity Ratio" value={latestRatios.debt_equity} benchmark={RATIO_BENCHMARKS['D/E']} />
                        <RatioBar name="EBITDA Margin %" value={latestRatios.ebitda_margin != null ? latestRatios.ebitda_margin * 100 : null} benchmark={RATIO_BENCHMARKS['EBITDA%']} />
                    </div>
                    <div>
                        <RatioBar name="PAT Margin %" value={latestRatios.pat_margin != null ? latestRatios.pat_margin * 100 : null} benchmark={RATIO_BENCHMARKS['PAT%']} />
                        <RatioBar name="Current Ratio" value={latestRatios.current_ratio} benchmark={RATIO_BENCHMARKS['Curr. Ratio']} />
                        <RatioBar name="ROCE %" value={latestRatios.roce != null ? latestRatios.roce * 100 : null} benchmark={RATIO_BENCHMARKS['ROCE']} />
                    </div>
                </div>
            </div>

            {/* Trend Charts */}
            {trendData.length > 1 && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="card p-5">
                        <div className="text-sm font-semibold text-slate-300 mb-3">DSCR & Interest Coverage Trend</div>
                        <ResponsiveContainer width="100%" height={200}>
                            <LineChart data={trendData}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                                <XAxis dataKey="period" tick={{ fill: '#64748b', fontSize: 11 }} />
                                <YAxis tick={{ fill: '#64748b', fontSize: 11 }} />
                                <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8 }} />
                                <ReferenceLine y={1.25} stroke="#f59e0b" strokeDasharray="4 4" label={{ value: 'Min DSCR', position: 'right', fill: '#f59e0b', fontSize: 10 }} />
                                <Line type="monotone" dataKey="DSCR" stroke="#60a5fa" strokeWidth={2} dot={{ fill: '#60a5fa', r: 4 }} />
                            </LineChart>
                        </ResponsiveContainer>
                    </div>

                    <div className="card p-5">
                        <div className="text-sm font-semibold text-slate-300 mb-3">Profitability Trend</div>
                        <ResponsiveContainer width="100%" height={200}>
                            <LineChart data={trendData}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                                <XAxis dataKey="period" tick={{ fill: '#64748b', fontSize: 11 }} />
                                <YAxis tick={{ fill: '#64748b', fontSize: 11 }} />
                                <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8 }} />
                                <ReferenceLine y={0} stroke="#ef4444" strokeWidth={1} />
                                <Line type="monotone" dataKey="EBITDA%" stroke="#a78bfa" strokeWidth={2} dot={{ fill: '#a78bfa', r: 4 }} />
                                <Line type="monotone" dataKey="PAT%" stroke="#22c55e" strokeWidth={2} dot={{ fill: '#22c55e', r: 4 }} />
                                <Legend wrapperStyle={{ fontSize: 11, color: '#94a3b8' }} />
                            </LineChart>
                        </ResponsiveContainer>
                    </div>

                    <div className="card p-5">
                        <div className="text-sm font-semibold text-slate-300 mb-3">Leverage Trend</div>
                        <ResponsiveContainer width="100%" height={200}>
                            <LineChart data={trendData}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                                <XAxis dataKey="period" tick={{ fill: '#64748b', fontSize: 11 }} />
                                <YAxis tick={{ fill: '#64748b', fontSize: 11 }} />
                                <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8 }} />
                                <ReferenceLine y={3} stroke="#f59e0b" strokeDasharray="4 4" label={{ value: 'Warn', position: 'right', fill: '#f59e0b', fontSize: 10 }} />
                                <Line type="monotone" dataKey="D/E" stroke="#f87171" strokeWidth={2} dot={{ fill: '#f87171', r: 4 }} />
                            </LineChart>
                        </ResponsiveContainer>
                    </div>

                    <div className="card p-5">
                        <div className="text-sm font-semibold text-slate-300 mb-3">Liquidity Trend</div>
                        <ResponsiveContainer width="100%" height={200}>
                            <LineChart data={trendData}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                                <XAxis dataKey="period" tick={{ fill: '#64748b', fontSize: 11 }} />
                                <YAxis tick={{ fill: '#64748b', fontSize: 11 }} />
                                <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8 }} />
                                <ReferenceLine y={1} stroke="#ef4444" strokeDasharray="4 4" label={{ value: 'Min', position: 'right', fill: '#ef4444', fontSize: 10 }} />
                                <Line type="monotone" dataKey="Curr. Ratio" stroke="#34d399" strokeWidth={2} dot={{ fill: '#34d399', r: 4 }} />
                            </LineChart>
                        </ResponsiveContainer>
                    </div>
                </div>
            )}
        </div>
    )
}
