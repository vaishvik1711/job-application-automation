import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from 'sonner'
import { QueryProvider } from '@/services/queryProvider'
import { WebSocketProvider } from '@/services/WebSocketProvider'
import { Layout } from '@/components/layout/Layout'
import { Dashboard } from '@/pages/Dashboard'
import { Profile } from '@/pages/Profile'
import { JobSearch } from '@/pages/JobSearch'
import { JobMatching } from '@/pages/JobMatching'
import { ResumeBuilder } from '@/pages/ResumeBuilder'
import { Applications } from '@/pages/Applications'
import { Analytics } from '@/pages/Analytics'
import { Settings } from '@/pages/Settings'

function App() {
  return (
    <QueryProvider>
      <WebSocketProvider>
        <BrowserRouter>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<Navigate to="/dashboard" replace />} />
            <Route path="dashboard" element={<Dashboard />} />
            <Route path="profile" element={<Profile />} />
            <Route path="job-search" element={<JobSearch />} />
            <Route path="job-matching" element={<JobMatching />} />
            <Route path="resume-builder" element={<ResumeBuilder />} />
            <Route path="applications" element={<Applications />} />
            <Route path="analytics" element={<Analytics />} />
            <Route path="settings" element={<Settings />} />
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