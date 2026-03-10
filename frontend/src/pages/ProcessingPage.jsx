import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { CheckCircle, Clock, AlertTriangle } from 'lucide-react'
import api from '../services/api'

const PIPELINE_STEPS = [
    { key: 'perception', label: 'DOCUMENT CLASSIFICATION', desc: 'Classifying document types with AI fingerprinting' },
    { key: 'extraction', label: 'DATA EXTRACTION', desc: 'OCR + table parsing for financial statements, GST, bank data' },
    { key: 'normalization', label: 'DATA NORMALIZATION', desc: 'Converting to paise, normalizing Indian FY periods, computing ratios' },
    { key: 'cross_validation', label: 'CROSS-VALIDATION', desc: 'GST vs bank reconciliation, GSTR-1 vs GSTR-3B vs GSTR-2A' },
    { key: 'fraud_detection', label: 'FRAUD DETECTION & EWS', desc: 'Circular trading graph, 15 early warning signal checks' },
]

const STATUS_ICONS = {
    done: { icon: CheckCircle, color: '#fff', bg: '#000', border: '#fff' },
    running: { icon: Clock, color: '#fff', bg: '#111', border: '#fff' },
    pending: { icon: Clock, color: '#444', bg: '#000', border: '#222' },
    error: { icon: AlertTriangle, color: '#ff4444', bg: '#000', border: '#ff4444' },
}

export default function ProcessingPage() {
    const { caseId } = useParams()
    const navigate = useNavigate()
    const [status, setStatus] = useState(null)
    const [elapsed, setElapsed] = useState(0)
    const [startTime] = useState(Date.now())

    useEffect(() => {
        const timer = setInterval(() => {
            setElapsed(Math.floor((Date.now() - startTime) / 1000))
        }, 1000)
        return () => clearInterval(timer)
    }, [startTime])

    useEffect(() => {
        const poll = setInterval(async () => {
            try {
                const res = await api.get(`/cases/${caseId}/status`)
                setStatus(res.data)
                if (res.data.status === 'completed') {
                    clearInterval(poll)
                    setTimeout(() => navigate(`/cases/${caseId}/results`), 1500)
                } else if (res.data.status === 'failed') {
                    clearInterval(poll)
                }
            } catch (err) {
                console.error("Polling error:", err)
            }
        }, 2000)
        return () => clearInterval(poll)
    }, [caseId, navigate])

    const pipeline = status?.pipeline_status || {}

    return (
        <div style={{ maxWidth: '600px', margin: '40px auto' }}>
            
            <div style={{ textAlign: 'center', marginBottom: '50px' }}>
                <h1 style={{ fontSize: '1.5rem', marginBottom: '10px' }}>AI ANALYSIS ENGINE</h1>
                <p style={{ color: '#666', fontSize: '0.7rem', letterSpacing: '2px' }}>
                    PROCESSING CASE ID: <span className="mono" style={{ color: '#fff' }}>{caseId?.slice(0, 8)}...</span>
                </p>
                {elapsed > 0 && (
                    <p className="mono" style={{ fontSize: '0.8rem', marginTop: '15px', color: '#fff' }}>
                        TIME ELAPSED: {Math.floor(elapsed / 60)}:{String(elapsed % 60).padStart(2, '0')}
                    </p>
                )}
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
                {PIPELINE_STEPS.map((step) => {
                    const stepStatus = pipeline[step.key] || 'pending'
                    const cfg = STATUS_ICONS[stepStatus] || STATUS_ICONS.pending
                    const Icon = cfg.icon

                    return (
                        <div key={step.key} style={{ 
                            border: `1px solid ${cfg.border}`,
                            padding: '15px 20px',
                            background: cfg.bg,
                            display: 'flex',
                            gap: '20px',
                            alignItems: 'center'
                        }}>
                            <div style={{ color: cfg.color }}>
                                <Icon size={20} className={stepStatus === 'running' ? 'animate-spin' : ''} />
                            </div>
                            <div style={{ flex: 1 }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                    <span style={{ fontSize: '0.8rem', fontWeight: 'bold' }}>{step.label}</span>
                                    <span style={{ fontSize: '0.6rem', letterSpacing: '1px', color: cfg.color }}>{stepStatus.toUpperCase()}</span>
                                </div>
                                <p style={{ fontSize: '0.65rem', color: '#666', marginTop: '4px' }}>{step.desc}</p>
                            </div>
                        </div>
                    )
                })}
            </div>

            {status?.status === 'completed' && (
                <div style={{ marginTop: '40px', border: '1px solid #fff', padding: '20px', textAlign: 'center' }}>
                    <p style={{ fontSize: '0.9rem', fontWeight: 'bold' }}>PIPELINE COMPLETE</p>
                    <p style={{ fontSize: '0.7rem', color: '#666', marginTop: '5px' }}>REDIRECTING TO AUDIT RESULTS...</p>
                </div>
            )}

            {status?.status === 'failed' && (
                <div style={{ marginTop: '40px', border: '1px solid #ff4444', padding: '20px', textAlign: 'center' }}>
                    <p style={{ fontSize: '0.9rem', fontWeight: 'bold', color: '#ff4444' }}>PIPELINE FAILURE</p>
                    <p style={{ fontSize: '0.7rem', color: '#ff4444', marginTop: '5px', fontFamily: 'monospace' }}>
                        {status?.error || 'CRITICAL ERROR ENCOUNTERED DURING EXTRACTION.'}
                    </p>
                    <p style={{ fontSize: '0.6rem', color: '#666', marginTop: '10px' }}>
                        CHECK BACKEND TERMINAL FOR FULL TRACEBACK.
                    </p>
                </div>
            )}
        </div>
    )
}
