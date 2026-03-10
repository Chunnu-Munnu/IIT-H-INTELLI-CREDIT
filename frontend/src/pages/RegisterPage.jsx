import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { authService } from '../services/authService'

export default function RegisterPage() {
    const nav = useNavigate()
    const [form, setForm] = useState({ name: '', email: '', organization: '', password: '' })
    const [error, setError] = useState('')
    const [loading, setLoading] = useState(false)

    const set = k => e => setForm(f => ({ ...f, [k]: e.target.value }))

    const submit = async e => {
        e.preventDefault()
        setError('')
        setLoading(true)
        try {
            await authService.register(form)
            nav('/dashboard')
        } catch (err) {
            setError(err.response?.data?.detail || 'Registration failed.')
        } finally {
            setLoading(false)
        }
    }

    return (
        <div style={{ minHeight: '100vh', background: '#000', display: 'flex' }}>

            {/* Left panel — branding */}
            <div style={{ width: '42%', borderRight: '1px solid #1a1a1a', padding: '4rem 3rem', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
                <div>
                    <div className="logo-text" style={{ marginBottom: '3rem' }}>INTELLI-CREDIT</div>
                    <div style={{ fontSize: '2.5rem', fontWeight: 700, lineHeight: 1.1, color: '#fff', marginBottom: '1.5rem' }}>
                        AI-Powered<br />Credit Appraisal<br />Engine
                    </div>
                    <div style={{ color: '#444', fontSize: '0.875rem', lineHeight: 1.7 }}>
                        Production-grade ML ensemble for Indian corporate credit risk assessment.
                        SHAP explainability · GST reconciliation · Graph intelligence.
                    </div>
                </div>

                {/* Stats strip */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1px', background: '#1a1a1a', border: '1px solid #1a1a1a' }}>
                    {[['0.78', 'Val AUC'], ['52K', 'Training Rows'], ['3', 'Base Models'], ['67', 'Features']].map(([v, l]) => (
                        <div key={l} style={{ background: '#000', padding: '1.25rem', textAlign: 'center' }}>
                            <div className="mono" style={{ fontSize: '1.5rem', fontWeight: 700, color: '#fff' }}>{v}</div>
                            <div style={{ fontSize: '0.65rem', color: '#444', textTransform: 'uppercase', letterSpacing: '0.1em', marginTop: '0.25rem' }}>{l}</div>
                        </div>
                    ))}
                </div>
            </div>

            {/* Right panel — form */}
            <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '3rem' }}>
                <div style={{ width: '100%', maxWidth: '400px' }}>

                    <div style={{ borderBottom: '1px solid #1a1a1a', paddingBottom: '1.5rem', marginBottom: '2rem' }}>
                        <div style={{ fontSize: '0.65rem', color: '#444', textTransform: 'uppercase', letterSpacing: '0.15em', marginBottom: '0.5rem' }}>Create Account</div>
                        <div style={{ fontSize: '1.75rem', fontWeight: 700, color: '#fff' }}>Register</div>
                    </div>

                    {error && (
                        <div style={{ border: '1px solid #ffaaaa', color: '#ffaaaa', padding: '0.75rem 1rem', fontSize: '0.8rem', marginBottom: '1.5rem' }}>
                            {error}
                        </div>
                    )}

                    <form onSubmit={submit} style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
                        {[
                            { key: 'name', label: 'Full Name', type: 'text', placeholder: 'Amogh Sharma' },
                            { key: 'email', label: 'Email', type: 'email', placeholder: 'officer@sbi.co.in' },
                            { key: 'organization', label: 'Bank / Organization', type: 'text', placeholder: 'State Bank of India' },
                            { key: 'password', label: 'Password', type: 'password', placeholder: '••••••••' },
                        ].map(({ key, label, type, placeholder }) => (
                            <div key={key}>
                                <label className="label">{label}</label>
                                <input
                                    className="input"
                                    type={type}
                                    placeholder={placeholder}
                                    value={form[key]}
                                    onChange={set(key)}
                                    required
                                />
                            </div>
                        ))}

                        <button
                            type="submit"
                            className="btn-primary"
                            disabled={loading}
                            style={{ width: '100%', marginTop: '0.5rem' }}
                        >
                            {loading ? 'Creating...' : 'Create Account'}
                        </button>
                    </form>

                    <div style={{ marginTop: '2rem', paddingTop: '1.5rem', borderTop: '1px solid #1a1a1a', textAlign: 'center', fontSize: '0.8rem', color: '#444' }}>
                        Already registered?{' '}
                        <Link to="/login" style={{ color: '#fff', textDecoration: 'none', borderBottom: '1px solid #333' }}>
                            Sign in
                        </Link>
                    </div>
                </div>
            </div>
        </div>
    )
}
