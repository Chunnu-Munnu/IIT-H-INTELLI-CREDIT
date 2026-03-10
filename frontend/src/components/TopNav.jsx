import { useNavigate, useLocation } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'

export default function TopNav() {
    const navigate  = useNavigate()
    const location  = useLocation()
    const { user, logout } = useAuthStore()

    const isActive = (path) =>
        path === '/dashboard'
            ? location.pathname === '/dashboard'
            : location.pathname.startsWith(path)

    const handleLogout = () => { logout(); navigate('/login') }

    const links = [
        { label: 'Dashboard', path: '/dashboard' },
        { label: 'Cases',     path: '/cases'     },
        { label: 'New Case',  path: '/cases/new' },
    ]

    return (
        <header className="topnav">
            <div className="topnav-logo" onClick={() => navigate('/dashboard')}>
                INTELLI<span>·</span>CREDIT
            </div>

            <nav style={{ display: 'flex', alignItems: 'stretch', height: '100%' }}>
                {links.map(({ label, path }) => (
                    <button
                        key={path}
                        onClick={() => navigate(path)}
                        className={`topnav-link ${isActive(path) ? 'active' : ''}`}
                    >
                        {label}
                    </button>
                ))}
            </nav>

            <div className="topnav-right">
                {user?.name && (
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontFamily: 'var(--sans)' }}>
                        {user.name}
                    </span>
                )}
                <button
                    onClick={handleLogout}
                    className="btn-ghost"
                    style={{ fontSize: '0.75rem', padding: '6px 14px' }}
                >
                    Logout
                </button>
            </div>
        </header>
    )
}
