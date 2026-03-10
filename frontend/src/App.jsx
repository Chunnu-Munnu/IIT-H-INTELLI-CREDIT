import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'

import TopNav from "./components/TopNav"
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import DashboardPage from './pages/DashboardPage'
import CasesPage from './pages/CasesPage'
import NewCasePage from './pages/NewCasePage'
import ProcessingPage from './pages/ProcessingPage'
import ResultsPage from './pages/ResultsPage'
import AnalysisPage from './pages/AnalysisPage'
import RecommendationPage from './pages/RecommendationPage'
import AuditPage from './pages/AuditPage'
import ProtectedRoute from './components/auth/ProtectedRoute'

function Layout({ children }) {
  return (
    <div style={{ minHeight: '100vh', background: '#000' }}>
      <TopNav />
      <main style={{ paddingTop: '50px' }}>
        {children}
      </main>
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: '#0d0d0d',
            color: '#e0e0e0',
            border: '1px solid #2a2a2a',
            fontFamily: '"JetBrains Mono", monospace',
            fontSize: '0.65rem',
            borderRadius: '0',
            boxShadow: '0 4px 24px rgba(0,0,0,0.8)',
          },
        }}
      />

      <Routes>
        {/* Public */}
        <Route path="/login"    element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />

        {/* Protected */}
        <Route element={<ProtectedRoute />}>
          <Route element={<Layout><DashboardPage /></Layout>}      path="/dashboard" />
          <Route element={<Layout><CasesPage /></Layout>}           path="/cases" />
          <Route element={<Layout><NewCasePage /></Layout>}         path="/cases/new" />
          <Route element={<Layout><ProcessingPage /></Layout>}      path="/cases/:caseId/processing" />
          <Route element={<Layout><ResultsPage /></Layout>}         path="/cases/:caseId/results" />
          <Route element={<Layout><AnalysisPage /></Layout>}        path="/cases/:caseId/analysis" />
          <Route element={<Layout><RecommendationPage /></Layout>}  path="/cases/:caseId/recommendation" />
          <Route element={<Layout><AuditPage /></Layout>}           path="/cases/:caseId/audit" />
        </Route>

        <Route path="/"  element={<Navigate to="/dashboard" replace />} />
        <Route path="*"  element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
