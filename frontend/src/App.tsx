// Root application: router configuration with all page routes

import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AppLayout } from './components/layout/app-layout'
import { DashboardPage } from './components/dashboard/dashboard-page'
import { TemplateBrowserPage } from './components/templates/template-browser-page'
import { JobMonitorPage } from './components/jobs/job-monitor-page'
import { PlanViewerPage } from './components/plan/plan-viewer-page'
import { ApprovalPanelPage } from './components/approvals/approval-panel-page'
import { ProviderConfigPage } from './components/config/provider-config-page'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppLayout />}>
          <Route index element={<DashboardPage />} />
          <Route path="templates" element={<TemplateBrowserPage />} />
          <Route path="templates/:provider/:tplName" element={<TemplateBrowserPage />} />
          <Route path="jobs" element={<JobMonitorPage />} />
          <Route path="jobs/:id" element={<JobMonitorPage />} />
          <Route path="jobs/:id/plan" element={<PlanViewerPage />} />
          <Route path="approvals" element={<ApprovalPanelPage />} />
          <Route path="config" element={<ProviderConfigPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
