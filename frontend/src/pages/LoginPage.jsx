import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import { authService } from '../services/authService'

export default function LoginPage() {
    const nav = useNavigate()
    const setAuth = useAuthStore(s => s.setAuth)
    const [form, setForm] = useState({ email: '', password: '' })
    const [error, setError] = useState('')
    const [loading, setLoading] = useState(false)

    const set = k => e => setForm(f => ({ ...f, [k]: e.target.value }))

    const submit = async e => {
        e.preventDefault()
        setError('')
        setLoading(true)
        try {
            await authService.login(form.email, form.password)
            nav('/dashboard')
        } catch (err) {
            setError(err.response?.data?.detail || 'Invalid credentials.')
        } finally {
            setLoading(false)
        }
    }

    return (
        <div style={{ minHeight: '100vh', background: '#000', display: 'flex', paddingTop: 0 }}>

            {/* Left panel — branding */}
            <div style={{ width: '42%', borderRight: '1px solid #1c1c1c', padding: '4rem 3rem', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', background: '#060606' }}>
                <div>
                    <div style={{ fontWeight: 800, letterSpacing: '4px', fontSize: '0.72rem', marginBottom: '3rem', color: '#f0f0f0' }}>INTELLI·CREDIT</div>
                    <div style={{ fontSize: '2.5rem', fontWeight: 700, lineHeight: 1.1, color: '#fff', marginBottom: '1.5rem' }}>
                        Corporate<br />Credit Appraisal<br />Intelligence
                    </div>
                    <div style={{ color: '#444', fontSize: '0.875rem', lineHeight: 1.7 }}>
                        Next-generation AI engine for Indian corporate lending.
                        Built for credit officers. Powered by real banking data.
                    </div>
                </div>

                {/* Feature list */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0', background: '#0a0a0a', border: '1px solid #1c1c1c', padding: '4px 0' }}>
                    {[
                        'ML Ensemble (XGB · LGBM · CatBoost)',
                        'GST + Bank Statement Reconciliation',
                        'SHAP Explainability per Decision',
                        'Graph Intelligence & Network Risk',
                        'Five Cs Credit Scoring Framework',
                        'Automated CAM Generation',
                    ].map((f, i) => (
                        <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', padding: '0.75rem 1rem', borderBottom: '1px solid #111' }}>
                            <div style={{ width: '5px', height: '5px', background: '#2a2a2a', flexShrink: 0 }} />
                            <span style={{ fontSize: '0.65rem', color: '#555', fontFamily: 'JetBrains Mono, monospace' }}>{f}</span>
                        </div>
                    ))}
                </div>
            </div>

            {/* Right panel — form */}
            <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '3rem', background: '#000' }}>
                <div style={{ width: '100%', maxWidth: '380px', background: '#0d0d0d', border: '1px solid #222', padding: '36px' }}>

                    <div style={{ borderBottom: '1px solid #1c1c1c', paddingBottom: '1.5rem', marginBottom: '2rem' }}>
                        <div style={{ fontSize: '0.52rem', color: '#444', textTransform: 'uppercase', letterSpacing: '3px', marginBottom: '6px' }}>Secure Access</div>
                        <div style={{ fontSize: '1.6rem', fontWeight: 800, color: '#f0f0f0', textTransform: 'uppercase', letterSpacing: '2px' }}>Sign In</div>
                    </div>

                    {error && (
                        <div style={{ border: '1px solid #ffaaaa', color: '#ffaaaa', padding: '0.75rem 1rem', fontSize: '0.8rem', marginBottom: '1.5rem' }}>
                            {error}
                        </div>
                    )}

                    <form onSubmit={submit} style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
                        <div>
                            <label className="label">Email</label>
                            <input
                                className="input"
                                type="email"
                                placeholder="officer@sbi.co.in"
                                value={form.email}
                                onChange={set('email')}
                                required
                            />
                        </div>
                        <div>
                            <label className="label">Password</label>
                            <input
                                className="input"
                                type="password"
                                placeholder="••••••••"
                                value={form.password}
                                onChange={set('password')}
                                required
                            />
                        </div>

                        <button
                            type="submit"
                            className="btn-primary"
                            disabled={loading}
                            style={{ width: '100%', marginTop: '0.5rem' }}
                        >
                            {loading ? 'Authenticating...' : 'Sign In'}
                        </button>
                    </form>

                    <div style={{ marginTop: '2rem', paddingTop: '1.5rem', borderTop: '1px solid #1c1c1c', textAlign: 'center', fontSize: '0.65rem', color: '#444' }}>
                        No account?{' '}
                        <Link to="/register" style={{ color: '#888', textDecoration: 'none', borderBottom: '1px solid #2a2a2a' }}>
                            Register here
                        </Link>
                    </div>

                    {/* System status */}
                    <div style={{ marginTop: '2rem', padding: '14px 16px', border: '1px solid #1c1c1c', background: '#080808' }}>
                        <div style={{ fontSize: '0.5rem', color: '#333', textTransform: 'uppercase', letterSpacing: '2px', marginBottom: '8px' }}>System Status</div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <span style={{ fontSize: '0.6rem', color: '#555' }}>ML Engine</span>
                            <span style={{ fontSize: '0.55rem', color: '#22cc55', border: '1px solid #22cc5540', padding: '2px 8px', letterSpacing: '1px' }}>ONLINE</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    )
}
