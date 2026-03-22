// Root application: router with auth guard and all page routes

import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './components/auth/auth-provider'
import { AppLayout } from './components/layout/app-layout'
import { LoginPage } from './components/auth/login-page'
import { RegisterPage } from './components/auth/register-page'
import { DashboardPage } from './components/dashboard/dashboard-page'
import { TemplateBrowserPage } from './components/templates/template-browser-page'
import { JobMonitorPage } from './components/jobs/job-monitor-page'
import { PlanViewerPage } from './components/plan/plan-viewer-page'
import { ApprovalPanelPage } from './components/approvals/approval-panel-page'
import { ProviderConfigPage } from './components/config/provider-config-page'
import { StatePage } from './components/state/state-page'
import { PolicyPage } from './components/policies/policy-page'
import { SettingsPage } from './components/settings/settings-page'
import { ProjectListPage } from './components/projects/project-list-page'
import { ProjectDetailPage } from './components/projects/project-detail-page'
import { HCLEditorPage } from './components/editor/hcl-editor-page'
import { WorkspaceEnvironmentPage } from './components/workspaces/workspace-environment-page'
import { VariableSetsPage } from './components/variable-sets/variable-sets-page'
import { ModuleRegistryPage } from './components/registry/module-registry-page'
import { ModuleDetailPage } from './components/registry/module-detail-page'
import { StackComposerPage } from './components/stacks/stack-composer-page'
import { AIStudioPage } from './components/studio/ai-studio-page'
import { KBLandingPage } from './components/kb/kb-landing-page'
import { KBChapterPage } from './components/kb/kb-chapter-page'
import { KBQuizPage } from './components/kb/kb-quiz-page'
import { KBLabPage } from './components/kb/kb-lab-page'
import { KBLeaderboardPage } from './components/kb/kb-leaderboard-page'

function ProtectedRoutes() {
  const { isAuthenticated, isLoading } = useAuth()

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-zinc-950 text-zinc-400">
        Loading...
      </div>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route index element={<DashboardPage />} />
        <Route path="templates" element={<TemplateBrowserPage />} />
        <Route path="templates/:provider/:tplName" element={<TemplateBrowserPage />} />
        <Route path="jobs" element={<JobMonitorPage />} />
        <Route path="jobs/:id" element={<JobMonitorPage />} />
        <Route path="jobs/:id/plan" element={<PlanViewerPage />} />
        <Route path="approvals" element={<ApprovalPanelPage />} />
        <Route path="state" element={<StatePage />} />
        <Route path="policies" element={<PolicyPage />} />
        <Route path="projects" element={<ProjectListPage />} />
        <Route path="projects/:id" element={<ProjectDetailPage />} />
        <Route path="workspaces/:id/editor" element={<HCLEditorPage />} />
        <Route path="environments" element={<WorkspaceEnvironmentPage />} />
        <Route path="variable-sets" element={<VariableSetsPage />} />
        <Route path="registry" element={<ModuleRegistryPage />} />
        <Route path="registry/:moduleId" element={<ModuleDetailPage />} />
        <Route path="stacks" element={<StackComposerPage />} />
        <Route path="studio" element={<AIStudioPage />} />
        <Route path="studio/edit/*" element={<AIStudioPage />} />
        <Route path="modules/generate" element={<Navigate to="/studio" replace />} />
        <Route path="kb" element={<KBLandingPage />} />
        <Route path="kb/:slug" element={<KBChapterPage />} />
        <Route path="kb/:slug/quiz" element={<KBQuizPage />} />
        <Route path="kb/:slug/lab" element={<KBLabPage />} />
        <Route path="kb/leaderboard" element={<KBLeaderboardPage />} />
        <Route path="config" element={<ProviderConfigPage />} />
        <Route path="settings" element={<SettingsPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/*" element={<ProtectedRoutes />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}
