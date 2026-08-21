import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from 'sonner'
import { QueryProvider } from '@/services/queryProvider'
import { WebSocketProvider } from '@/services/WebSocketProvider'
import { Layout } from '@/components/layout/Layout'
import { Dashboard } from '@/pages/Dashboard'
import { Jobs } from '@/pages/Jobs'
import { Applications } from '@/pages/Applications'
import { Settings } from '@/pages/Settings'
import { Profile } from '@/pages/Profile'

function App() {
  return (
    <QueryProvider>
      <WebSocketProvider>
        <BrowserRouter>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<Navigate to="/dashboard" replace />} />
            <Route path="dashboard" element={<Dashboard />} />
            <Route path="jobs" element={<Jobs />} />
            <Route path="applications" element={<Applications />} />
            <Route path="profile" element={<Profile />} />
            <Route path="settings" element={<Settings />} />
            {/* Legacy paths that live code still links to — redirect so
                navigation never lands on a blank content area. */}
            <Route path="job-search" element={<Navigate to="/jobs" replace />} />
            <Route path="job-matching" element={<Navigate to="/jobs" replace />} />
            <Route path="resume-builder" element={<Navigate to="/jobs" replace />} />
            <Route path="analytics" element={<Navigate to="/dashboard" replace />} />
            {/* The 401 interceptor used to hard-navigate here; keep it valid. */}
            <Route path="login" element={<Navigate to="/dashboard" replace />} />
            {/* Catch-all: unknown URLs go to the dashboard instead of a blank page */}
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Route>
        </Routes>
        <Toaster
          position="top-right"
          toastOptions={{
            duration: 4000,
            style: {
              background: 'var(--surface)',
              color: 'var(--foreground)',
              border: '1px solid var(--border)',
            },
          }}
        />
      </BrowserRouter>
        </WebSocketProvider>
    </QueryProvider>
  )
}

export default App