import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { AlertTriangle } from 'lucide-react'
import api from '../services/api'

export default function AuditPage() {
    const { caseId } = useParams()
    const [entries, setEntries] = useState([])
    const [loading, setLoading] = useState(true)
    const [filter, setFilter] = useState('ALL')

    useEffect(() => {
        const load = async () => {
            try {
                const res = await api.get(`/cases/${caseId}/audit-trail`)
                setEntries(res.data.entries || [])
            } catch { }
            finally { setLoading(false) }
        }
        load()
    }, [caseId])

    const levels = ['ALL', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW']
    const filtered = entries.filter(e => filter === 'ALL' || e.risk_level === filter)

    return (
        <div style={{ maxWidth: '900px', margin: '0 auto' }}>
            
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginBottom: '40px', paddingBottom: '20px', borderBottom: '1px solid #333' }}>
                <div>
                    <h1 style={{ fontSize: '1.5rem', margin: 0 }}>REGULATORY AUDIT TRAIL</h1>
                    <p style={{ color: '#666', fontSize: '0.7rem', letterSpacing: '2px', marginTop: '5px' }}>TRACEABILITY LOG: {caseId?.slice(0, 8)}</p>
                </div>
                <div style={{ display: 'flex', gap: '5px' }}>
                    {levels.map(l => (
                        <button 
                            key={l} 
                            onClick={() => setFilter(l)} 
                            style={{ 
                                padding: '5px 12px', 
                                fontSize: '0.6rem', 
                                background: filter === l ? '#fff' : '#000',
                                color: filter === l ? '#000' : '#666',
                                border: filter === l ? '1px solid #fff' : '1px solid #333',
                                fontWeight: 'bold'
                            }}
                        >
                            {l}
                        </button>
                    ))}
                </div>
            </div>

            {loading ? (
                <div style={{ textAlign: 'center', padding: '100px', color: '#666', fontSize: '0.7rem' }}>RETRIEVING AUDIT LOGS...</div>
            ) : filtered.length === 0 ? (
                <div className="card" style={{ textAlign: 'center', padding: '100px 40px' }}>
                    <AlertTriangle size={32} style={{ color: '#333', marginBottom: '15px' }} />
                    <p style={{ color: '#666', fontSize: '0.7rem' }}>NO AUDIT ENTRIES FOUND FOR THIS LEVEL.</p>
                </div>
            ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
                    {filtered.map((entry, i) => (
                        <div key={i} className="card" style={{ padding: '0', overflow: 'hidden' }}>
                            <div style={{ 
                                padding: '15px 20px', 
                                background: entry.risk_level === 'CRITICAL' ? '#ff4444' : '#000',
                                color: entry.risk_level === 'CRITICAL' ? '#000' : '#fff',
                                display: 'flex',
                                justifyContent: 'space-between',
                                alignItems: 'center'
                            }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
                                    <span style={{ fontSize: '0.8rem', fontWeight: 'bold' }}>{entry.finding_type}</span>
                                    {entry.five_c_mapping && (
                                        <span style={{ fontSize: '0.6rem', border: '1px solid currentColor', padding: '1px 5px' }}>{entry.five_c_mapping}</span>
                                    )}
                                </div>
                                <span style={{ fontSize: '0.65rem', fontWeight: 'bold', letterSpacing: '1px' }}>{entry.risk_level}</span>
                            </div>

                            <div style={{ padding: '20px' }}>
                                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '20px', marginBottom: '20px' }}>
                                    <div>
                                        <div style={{ fontSize: '0.6rem', color: '#666', marginBottom: '5px' }}>SOURCE</div>
                                        <div style={{ fontSize: '0.7rem' }}>{entry.source_document} {entry.page_number > 0 ? ` (P. ${entry.page_number})` : ''}</div>
                                    </div>
                                    {entry.extracted_value !== null && (
                                        <div>
                                            <div style={{ fontSize: '0.6rem', color: '#666', marginBottom: '5px' }}>EXTRACTED DATA</div>
                                            <div style={{ fontSize: '0.7rem' }} className="mono">{JSON.stringify(entry.extracted_value)}</div>
                                        </div>
                                    )}
                                    {entry.delta_paise !== null && entry.delta_paise !== undefined && (
                                        <div>
                                            <div style={{ fontSize: '0.6rem', color: '#666', marginBottom: '5px' }}>VARIANCE / IMPACT</div>
                                            <div style={{ fontSize: '0.7rem', fontWeight: 'bold', color: entry.delta_paise < 0 ? '#ff4444' : '#fff' }}>
                                                ₹{Math.abs(entry.delta_paise / 10000000 / 100).toFixed(2)} CR
                                            </div>
                                        </div>
                                    )}
                                </div>
                                <p style={{ fontSize: '0.75rem', color: '#999', lineHeight: '1.6', borderLeft: '2px solid #333', paddingLeft: '15px' }}>{entry.narrative}</p>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    )
}
