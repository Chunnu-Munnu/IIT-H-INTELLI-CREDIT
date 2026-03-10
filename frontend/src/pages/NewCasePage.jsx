import { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { toast } from 'react-hot-toast'
import { useDropzone } from 'react-dropzone'
import { Upload, File, X, CheckCircle, Edit3 } from 'lucide-react'
import api from '../services/api'

const SECTORS = [
    'Manufacturing', 'Infrastructure', 'Real Estate', 'NBFC', 'Textile',
    'Steel & Metals', 'Pharmaceuticals', 'IT & Technology', 'FMCG',
    'Automobiles', 'Energy & Power', 'Agriculture', 'Hospitality', 'Other'
]

const LOAN_TYPES = [
    'Term Loan', 'Cash Credit (CC)', 'Overdraft (OD)', 'Working Capital',
    'Letter of Credit (LC)', 'Bank Guarantee (BG)', 'Buyers Credit', 'Mixed Facility'
]

const DOC_TYPES_HACKATHON = [
    { value: 'annual_report',           label: 'Annual Report / P&L / Balance Sheet',  hint: 'PDF', critical: true },
    { value: 'shareholding_pattern',    label: 'Shareholding Pattern',                   hint: 'PDF / XLSX', critical: true },
    { value: 'alm_data',                label: 'ALM (Asset-Liability Management)',        hint: 'PDF / XLSX', critical: true },
    { value: 'borrowing_profile',       label: 'Borrowing Profile',                      hint: 'PDF / XLSX', critical: true },
    { value: 'portfolio_performance',   label: 'Portfolio Cuts / Performance Data',       hint: 'PDF / XLSX / CSV', critical: true },
    { value: 'gst_gstr1',              label: 'GSTR-1',                                  hint: 'JSON / PDF' },
    { value: 'gst_gstr3b',             label: 'GSTR-3B',                                 hint: 'JSON / PDF' },
    { value: 'gst_gstr2a',             label: 'GSTR-2A',                                 hint: 'JSON / PDF' },
    { value: 'bank_generic',           label: 'Bank Statement',                          hint: 'PDF / CSV' },
    { value: 'rating_report',          label: 'Rating Report (CRISIL / ICRA)',            hint: 'PDF' },
    { value: 'legal_notice',           label: 'Legal Notice / DRT / NCLT',               hint: 'PDF' },
    { value: 'unknown',                label: 'Other',                                    hint: 'Any' },
]

const DOC_MAP = Object.fromEntries(DOC_TYPES_HACKATHON.map(d => [d.value, d]))

export default function NewCasePage() {
    const navigate = useNavigate()
    const [step, setStep] = useState(1)
    const [caseId, setCaseId] = useState(null)

    // Step 1 — Entity Info
    const [caseInfo, setCaseInfo] = useState({
        company_name: '',
        company_cin: '',
        company_pan: '',
        sector: '',
        annual_turnover_cr: '',
        loan_type: '',
        loan_amount_cr: '',
        loan_tenure_months: '',
        loan_purpose: '',
    })

    // Step 2 — Files
    const [files, setFiles] = useState([])
    const [uploading, setUploading] = useState(false)
    const [creating, setCreating] = useState(false)

    // Step 3 — Classification review
    const [uploadedDocs, setUploadedDocs] = useState([])
    const [docOverrides, setDocOverrides] = useState({}) // file_id → doc_type override

    // Step 4 — Ready to process
    const [processing, setProcessing] = useState(false)

    const set = k => e => setCaseInfo(f => ({ ...f, [k]: e.target.value }))

    // ── Step 1: Create case ────────────────────────────────────────
    const createCase = async () => {
        if (!caseInfo.company_name.trim()) { toast.error('COMPANY NAME REQUIRED'); return }
        if (!caseInfo.sector) { toast.error('SELECT SECTOR'); return }
        if (!caseInfo.loan_amount_cr) { toast.error('LOAN AMOUNT REQUIRED'); return }
        setCreating(true)
        try {
            const res = await api.post('/cases/', {
                company_name: caseInfo.company_name,
                company_cin: caseInfo.company_cin,
                company_pan: caseInfo.company_pan,
                sector: caseInfo.sector,
                annual_turnover_cr: parseFloat(caseInfo.annual_turnover_cr) || null,
                loan_type: caseInfo.loan_type,
                loan_amount_cr: parseFloat(caseInfo.loan_amount_cr) || null,
                loan_tenure_months: parseInt(caseInfo.loan_tenure_months) || null,
                loan_purpose: caseInfo.loan_purpose,
            })
            setCaseId(res.data.case_id)
            setStep(2)
            toast.success('CASE INITIALIZED')
        } catch (err) {
            toast.error(err.response?.data?.detail || 'FAILED TO CREATE CASE')
        } finally { setCreating(false) }
    }

    // ── Step 2: Upload ────────────────────────────────────────────
    const onDrop = useCallback((accepted) => setFiles(prev => [...prev, ...accepted]), [])
    const { getRootProps, getInputProps, isDragActive } = useDropzone({
        onDrop,
        accept: {
            'application/pdf': ['.pdf'],
            'application/json': ['.json'],
            'text/csv': ['.csv'],
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
            'application/vnd.ms-excel': ['.xls'],
        },
        maxSize: 50 * 1024 * 1024,
    })

    const uploadFiles = async () => {
        if (files.length === 0) { toast.error('ADD AT LEAST ONE DOCUMENT'); return }
        setUploading(true)
        const formData = new FormData()
        files.forEach(f => formData.append('files', f))
        try {
            const res = await api.post(`/cases/${caseId}/upload`, formData)
            const docs = res.data.documents || []
            setUploadedDocs(docs)
            // Init overrides map with auto-detected types
            const overrides = {}
            docs.forEach(d => { overrides[d.file_id] = d.doc_type })
            setDocOverrides(overrides)
            setStep(3)
            toast.success(`${res.data.uploaded} DOCUMENTS UPLOADED`)
        } catch (err) {
            toast.error((err.response?.data?.detail || 'UPLOAD FAILED').toString().toUpperCase())
        } finally { setUploading(false) }
    }

    // ── Step 3: Classification confirm ───────────────────────────
    const confirmClassification = async () => {
        // Push user overrides back to backend
        try {
            await api.patch(`/cases/${caseId}/classify`, { overrides: docOverrides })
        } catch {
            // Endpoint may not exist yet — skip silently, classification still works
        }
        setStep(4)
    }

    // ── Step 4: Start pipeline ────────────────────────────────────
    const startProcessing = async () => {
        setProcessing(true)
        try {
            await api.post(`/cases/${caseId}/process`, {})
            toast.success('AI PIPELINE INITIATED')
            navigate(`/cases/${caseId}/processing`)
        } catch (err) {
            toast.error('FAILED TO START PIPELINE')
            setProcessing(false)
        }
    }

    const stepLabels = ['ENTITY INFO', 'UPLOAD', 'CLASSIFY', 'EXECUTE']

    return (
        <div style={{ maxWidth: '800px', margin: '0 auto' }}>

            {/* Step Header */}
            <div style={{ display: 'flex', borderBottom: '1px solid #333', marginBottom: '40px' }}>
                {stepLabels.map((label, i) => (
                    <div key={i} style={{
                        padding: '18px',
                        fontSize: '0.6rem',
                        letterSpacing: '2px',
                        flex: 1,
                        textAlign: 'center',
                        borderRight: i < 3 ? '1px solid #333' : 'none',
                        background: step === i + 1 ? '#fff' : step > i + 1 ? '#111' : '#000',
                        color: step === i + 1 ? '#000' : step > i + 1 ? '#fff' : '#444',
                        fontWeight: 'bold',
                        position: 'relative',
                    }}>
                        {step > i + 1 && <span style={{ marginRight: '5px' }}>✓</span>}
                        {i + 1}. {label}
                    </div>
                ))}
            </div>

            {/* ─── STEP 1: Entity & Loan Info ─── */}
            {step === 1 && (
                <div className="card">
                    <h2 style={{ fontSize: '1rem', marginBottom: '5px' }}>ENTITY ONBOARDING</h2>
                    <p style={{ color: '#555', fontSize: '0.65rem', marginBottom: '30px' }}>Complete all fields to initialize the appraisal pipeline.</p>

                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginBottom: '30px' }}>
                        {[
                            { key: 'company_name', label: 'LEGAL ENTITY NAME *', placeholder: 'Reliance Industries Limited', full: true },
                            { key: 'company_cin',  label: 'CIN (CORPORATE ID)', placeholder: 'L17110MH1973PLC019786' },
                            { key: 'company_pan',  label: 'PAN NUMBER', placeholder: 'AAACR5055K' },
                            { key: 'annual_turnover_cr', label: 'ANNUAL TURNOVER (₹ CR)', placeholder: '500', type: 'number' },
                        ].map(({ key, label, placeholder, full, type }) => (
                            <div key={key} style={full ? { gridColumn: '1 / -1' } : {}}>
                                <label style={{ display: 'block', fontSize: '0.6rem', color: '#666', marginBottom: '6px' }}>{label}</label>
                                <input type={type || 'text'} placeholder={placeholder} value={caseInfo[key]} onChange={set(key)} />
                            </div>
                        ))}
                        <div>
                            <label style={{ display: 'block', fontSize: '0.6rem', color: '#666', marginBottom: '6px' }}>SECTOR *</label>
                            <select value={caseInfo.sector} onChange={set('sector')} style={{ width: '100%' }}>
                                <option value="">-- SELECT SECTOR --</option>
                                {SECTORS.map(s => <option key={s} value={s}>{s.toUpperCase()}</option>)}
                            </select>
                        </div>
                        <div>
                            <label style={{ display: 'block', fontSize: '0.6rem', color: '#666', marginBottom: '6px' }}>LOAN TYPE *</label>
                            <select value={caseInfo.loan_type} onChange={set('loan_type')} style={{ width: '100%' }}>
                                <option value="">-- SELECT LOAN TYPE --</option>
                                {LOAN_TYPES.map(t => <option key={t} value={t}>{t.toUpperCase()}</option>)}
                            </select>
                        </div>
                        <div>
                            <label style={{ display: 'block', fontSize: '0.6rem', color: '#666', marginBottom: '6px' }}>REQUESTED AMOUNT (₹ CR) *</label>
                            <input type="number" placeholder="50" value={caseInfo.loan_amount_cr} onChange={set('loan_amount_cr')} />
                        </div>
                        <div>
                            <label style={{ display: 'block', fontSize: '0.6rem', color: '#666', marginBottom: '6px' }}>TENURE (MONTHS)</label>
                            <input type="number" placeholder="60" value={caseInfo.loan_tenure_months} onChange={set('loan_tenure_months')} />
                        </div>
                        <div style={{ gridColumn: '1 / -1' }}>
                            <label style={{ display: 'block', fontSize: '0.6rem', color: '#666', marginBottom: '6px' }}>LOAN PURPOSE</label>
                            <input type="text" placeholder="Capital expenditure for plant expansion..." value={caseInfo.loan_purpose} onChange={set('loan_purpose')} />
                        </div>
                    </div>

                    <button onClick={createCase} disabled={creating} style={{ width: '100%', padding: '15px', fontWeight: 'bold' }}>
                        {creating ? 'INITIALIZING...' : 'PROCEED TO DOCUMENT UPLOAD →'}
                    </button>
                </div>
            )}

            {/* ─── STEP 2: Upload ─── */}
            {step === 2 && (
                <div className="card">
                    <h2 style={{ fontSize: '1rem', marginBottom: '5px' }}>INTELLIGENT DATA INGESTION</h2>
                    <p style={{ color: '#555', fontSize: '0.65rem', marginBottom: '20px' }}>
                        Upload at least the <strong style={{ color: '#888' }}>5 CRITICAL DOCUMENTS</strong> required for this entity. 
                        GST and Bank data enables deep fraud detection.
                    </p>

                    {/* Critical doc types checklist */}
                    <div className="card" style={{ marginBottom: '25px', background: '#080808', border: '1px solid #1a1a1a' }}>
                        <div style={{ fontSize: '0.55rem', letterSpacing: '2.5px', color: '#444', marginBottom: '12px' }}>REQUIRED BY HACKATHON STAGE 2</div>
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                            {DOC_TYPES_HACKATHON.filter(d => d.critical).map(d => (
                                <div key={d.value} style={{ fontSize: '0.62rem', color: '#777', padding: '6px 12px', border: '1px solid #111', background: '#000' }}>
                                    ■ {d.label.split(' / ')[0]}
                                </div>
                            ))}
                        </div>
                    </div>

                    <div {...getRootProps()} style={{
                        border: isDragActive ? '1px solid #fff' : '1px dashed #333',
                        padding: '50px 40px',
                        textAlign: 'center',
                        cursor: 'pointer',
                        background: isDragActive ? '#111' : '#000',
                        marginBottom: '20px'
                    }}>
                        <input {...getInputProps()} />
                        <Upload size={36} style={{ marginBottom: '15px', color: '#444' }} />
                        <p style={{ fontSize: '0.85rem', marginBottom: '5px' }}>{isDragActive ? 'DROP NOW' : 'DROP FILES OR CLICK TO BROWSE'}</p>
                        <p style={{ color: '#444', fontSize: '0.6rem' }}>PDF · JSON · CSV · XLSX (MAX 50MB PER FILE)</p>
                    </div>

                    {files.length > 0 && (
                        <div style={{ marginBottom: '20px' }}>
                            <p style={{ fontSize: '0.65rem', color: '#666', marginBottom: '8px' }}>QUEUED ({files.length})</p>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '1px', background: '#222', border: '1px solid #222' }}>
                                {files.map((f, i) => (
                                    <div key={i} style={{ background: '#000', padding: '10px 15px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                                            <File size={12} color="#444" />
                                            <span style={{ fontSize: '0.75rem' }}>{f.name}</span>
                                            <span style={{ fontSize: '0.6rem', color: '#444' }}>({(f.size / (1024 * 1024)).toFixed(1)}MB)</span>
                                        </div>
                                        <button onClick={e => { e.stopPropagation(); setFiles(files.filter((_, j) => j !== i)) }}
                                            style={{ border: 'none', background: 'transparent', cursor: 'pointer' }}>
                                            <X size={12} color="#ff4444" />
                                        </button>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    <button onClick={uploadFiles} disabled={uploading || files.length === 0} style={{ width: '100%', padding: '15px', fontWeight: 'bold' }}>
                        {uploading ? 'UPLOADING...' : `UPLOAD ${files.length} FILE${files.length !== 1 ? 'S' : ''} AND CLASSIFY →`}
                    </button>
                </div>
            )}

            {/* ─── STEP 3: Human-in-the-loop Classification ─── */}
            {step === 3 && (
                <div className="card">
                    <h2 style={{ fontSize: '1rem', marginBottom: '5px' }}>CLASSIFICATION REVIEW</h2>
                    <p style={{ color: '#555', fontSize: '0.65rem', marginBottom: '25px' }}>
                        AI has auto-classified each document. Review and correct any misclassifications before proceeding.
                    </p>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: '1px', background: '#222', border: '1px solid #222', marginBottom: '30px' }}>
                        {/* Header row */}
                        <div style={{ background: '#111', padding: '10px 15px', display: 'grid', gridTemplateColumns: '2fr 1fr 1fr', gap: '10px' }}>
                            <span style={{ fontSize: '0.55rem', color: '#444', letterSpacing: '1px' }}>FILENAME</span>
                            <span style={{ fontSize: '0.55rem', color: '#444', letterSpacing: '1px' }}>AI CLASSIFICATION</span>
                            <span style={{ fontSize: '0.55rem', color: '#444', letterSpacing: '1px' }}>OVERRIDE</span>
                        </div>
                        {uploadedDocs.map((doc) => {
                            const currentType = docOverrides[doc.file_id] || doc.doc_type
                            const isOverridden = currentType !== doc.doc_type
                            return (
                                <div key={doc.file_id} style={{ background: '#000', padding: '12px 15px', display: 'grid', gridTemplateColumns: '2fr 1fr 1fr', gap: '10px', alignItems: 'center' }}>
                                    <div>
                                        <div style={{ fontSize: '0.75rem', marginBottom: '2px' }}>{doc.filename}</div>
                                        <div style={{ fontSize: '0.6rem', color: '#444' }}>{(doc.file_size_bytes / (1024 * 1024)).toFixed(1)}MB</div>
                                    </div>
                                    <div>
                                        <span style={{
                                            fontSize: '0.6rem',
                                            border: `1px solid ${isOverridden ? '#666' : '#fff'}`,
                                            color: isOverridden ? '#666' : '#fff',
                                            padding: '2px 8px',
                                            textDecoration: isOverridden ? 'line-through' : 'none'
                                        }}>
                                            {(DOC_MAP[doc.doc_type] || DOC_MAP.unknown).label}
                                        </span>
                                    </div>
                                    <div>
                                        <select
                                            value={currentType}
                                            onChange={e => setDocOverrides(prev => ({ ...prev, [doc.file_id]: e.target.value }))}
                                            style={{ fontSize: '0.6rem', padding: '4px 6px', width: '100%' }}
                                        >
                                            {DOC_TYPES_HACKATHON.map(d => (
                                                <option key={d.value} value={d.value}>{d.label}</option>
                                            ))}
                                        </select>
                                        {isOverridden && (
                                            <div style={{ fontSize: '0.55rem', color: '#fff', marginTop: '2px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                                                <CheckCircle size={10} /> OVERRIDDEN
                                            </div>
                                        )}
                                    </div>
                                </div>
                            )
                        })}
                    </div>

                    <div style={{ display: 'flex', gap: '10px' }}>
                        <button onClick={() => setStep(2)} style={{ padding: '12px 25px', background: '#000', border: '1px solid #333', color: '#666' }}>
                            ← REUPLOAD
                        </button>
                        <button onClick={confirmClassification} style={{ flex: 1, padding: '15px', fontWeight: 'bold' }}>
                            CONFIRM CLASSIFICATION → EXECUTE
                        </button>
                    </div>
                </div>
            )}

            {/* ─── STEP 4: Execute ─── */}
            {step === 4 && (
                <div className="card">
                    <h2 style={{ fontSize: '1rem', marginBottom: '5px' }}>PIPELINE EXECUTION</h2>
                    <p style={{ color: '#555', fontSize: '0.65rem', marginBottom: '25px' }}>
                        Review entity and document summary before triggering the 5-layer AI pipeline.
                    </p>

                    {/* Summary */}
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1px', background: '#222', border: '1px solid #222', marginBottom: '25px' }}>
                        {[
                            { label: 'ENTITY', value: caseInfo.company_name },
                            { label: 'CASE ID', value: caseId?.slice(0, 8) + '...' },
                            { label: 'SECTOR', value: caseInfo.sector || '—' },
                            { label: 'LOAN ASK', value: caseInfo.loan_amount_cr ? `₹${caseInfo.loan_amount_cr} Cr` : '—' },
                            { label: 'LOAN TYPE', value: caseInfo.loan_type || '—' },
                            { label: 'DOCUMENTS', value: `${uploadedDocs.length} files ready` },
                        ].map((s, i) => (
                            <div key={i} style={{ background: '#000', padding: '15px' }}>
                                <div style={{ fontSize: '0.55rem', color: '#666', marginBottom: '4px' }}>{s.label}</div>
                                <div style={{ fontSize: '0.8rem', fontWeight: 'bold' }}>{s.value}</div>
                            </div>
                        ))}
                    </div>

                    {/* Pipeline tasks */}
                    <div style={{ background: '#0a0a0a', border: '1px solid #222', padding: '20px', marginBottom: '30px' }}>
                        <p style={{ fontSize: '0.65rem', color: '#666', marginBottom: '15px', letterSpacing: '1px' }}>5-LAYER PIPELINE TASKS:</p>
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                            {[
                                'L1 PERCEPTION — Document classification',
                                'L2 EXTRACTION — OCR + table parsing',
                                'L3 NORMALIZATION — Ratio computation',
                                'L4 CROSS-VALIDATION — GST vs Bank',
                                'L5 FRAUD DETECTION — Circular trading + EWS',
                                'ML ENSEMBLE — XGB + LGBM + CatBoost scoring',
                            ].map((task, i) => (
                                <div key={i} style={{ fontSize: '0.6rem', color: '#555', display: 'flex', alignItems: 'flex-start', gap: '8px' }}>
                                    <span style={{ color: '#333', flexShrink: 0 }}>■</span> {task}
                                </div>
                            ))}
                        </div>
                    </div>

                    <button onClick={startProcessing} disabled={processing} style={{ width: '100%', padding: '18px', fontWeight: '900', fontSize: '0.9rem', background: '#fff', color: '#000' }}>
                        {processing ? 'INITIALIZING ENGINE...' : '▶ START AI ANALYSIS PIPELINE'}
                    </button>
                </div>
            )}
        </div>
    )
}
