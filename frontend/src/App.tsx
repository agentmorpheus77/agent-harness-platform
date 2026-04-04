import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { LoginPage } from '@/pages/LoginPage'
import { IssuesPage } from '@/pages/IssuesPage'
import { IssueCreatorPage } from '@/pages/IssueCreatorPage'
import { SettingsPage } from '@/pages/SettingsPage'
import { AppLayout } from '@/components/AppLayout'

export default function App() {
  return (
    <BrowserRouter>
      <Toaster position="top-right" />
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/app" element={<AppLayout />}>
          <Route index element={<Navigate to="issues" replace />} />
          <Route path="issues" element={<IssuesPage />} />
          <Route path="issues/new" element={<IssueCreatorPage />} />
          <Route path="settings" element={<SettingsPage />} />
        </Route>
        <Route path="*" element={<Navigate to="/app" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
