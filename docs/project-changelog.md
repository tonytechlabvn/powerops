# Project Changelog

## [Unreleased]

### Added

#### AI Studio — Unified Template Creation Hub (2026-03-23)
- **New feature: AI Studio** — Replaces "AI Generator" with comprehensive template creation hub at `/studio`
  - **Creator Mode**: Natural language → HCL template (describe infrastructure, Claude generates code)
  - **Extractor Mode**: HCL → Parameterized template (paste existing code, auto-extract variables)
  - **Wizard Mode**: AI-guided form (step-by-step questions with intelligent suggestions)
  - **Canvas Mode**: Visual infrastructure designer (React Flow graph with drag-drop resources, real-time preview)

- **Backend Components**
  - `AITemplateStudio` service — unified template creation orchestration
  - `TemplateStudioHelpers` — LLM prompt engineering and template generation
  - Specialized prompts: template-studio-prompt, wizard-step-prompt
  - Request/response schemas in `ai-studio-schemas.py`
  - 7 API endpoints under `/api/ai/studio/*`

- **Frontend Components**
  - `AIStudioPage` — main studio hub with mode selection
  - `StudioCreatorPanel` — NL input → template generation UI
  - `StudioExtractorPanel` — HCL paste/upload → parameterization UI
  - `StudioWizardPanel` — form-based multi-step template builder
  - `WizardStepProvider` & `WizardStepFields` — step management and rendering
  - `StudioCanvasPanel` — visual designer with React Flow canvas
  - `ResourceNodes` & `ResourcePalette` — canvas resource library
  - `CanvasPreviewSidebar` — real-time HCL preview from canvas design
  - `StudioChatPanel` — chat interface for template refinement
  - `StudioFilePreview` — syntax-highlighted template preview

- **State Management**
  - `use-template-studio` hook — API calls and state sync
  - `canvas-store.ts` (Zustand) — visual canvas state, node/edge management

- **UI/UX Features**
  - Seamless mode switching with context preservation
  - Real-time HCL preview in all modes
  - Resource palette for canvas mode
  - Step-by-step wizard with back/forward navigation
  - Template validation before saving
  - Syntax highlighting for HCL code
  - Responsive design (mobile-friendly)

- **Migration**
  - Old `/modules/generate` route redirects to `/studio`
  - Sidebar "AI Generator" link updated to "AI Studio"
  - Backward-compatible with existing templates

**Files Added: 25 files (8500+ lines)**
- Backend: 6 files (service, helpers, prompts, schemas, routes)
- Frontend: 16 files (pages, components, hooks, store)
- Tests: 2 files (unit tests for service and routes)

---

#### Hybrid WireGuard VPN Template (2026-03-22)
- **New template: `hybrid/wireguard-vpn`** — Proxmox VM + AWS EC2 connected via WireGuard VPN
  - EC2 as WireGuard server with Elastic IP for stable endpoint
  - Proxmox VM as WireGuard client with PersistentKeepalive
  - WireGuard keys as input variables (no regeneration drift)
  - Config delivered via SSH provisioner (private keys not in user_data)
  - Dynamic network interface detection for iptables rules
  - Providers: aws ~>5.0, proxmox/telmate ~>2.9, tls ~>4.0
- **New project config: `hybrid-wireguard-vpn.yaml`**

#### Knowledge Base Module (2026-03-22)
- **Interactive Terraform Curriculum** — 12-chapter learning path with hands-on labs and quizzes
  - Chapter 1: Infrastructure as Code (IaC) Intro
  - Chapter 2: HCL Syntax Fundamentals
  - Chapter 3: Providers and Terraform Init
  - Chapter 4: Resources and Attributes
  - Chapter 5: Variables and Outputs
  - Chapter 6: Data Sources
  - Chapter 7: State Management Deep Dive
  - Chapter 8: Terraform Modules
  - Chapter 9: Meta-Arguments
  - Chapter 10: Workspaces and Environments
  - Chapter 11: CI/CD and VCS Workflows
  - Chapter 12: Advanced Patterns

- **Backend Components** (`backend/kb/`)
  - `CurriculumLoader` — loads and caches curriculum chapters from YAML
  - `QuizEngine` — MCQ generation, answer grading, streak tracking
  - `LabValidator` — HCL syntax validation, linting, best-practices checking
  - `ProgressTracker` — user progress storage, milestone tracking, completion status
  - `Leaderboard` — team/org rankings, reputation scoring, badge system

- **12 API Endpoints** (`backend/api/routes/kb-routes.py`)
  - Curriculum browsing with progress tracking
  - Chapter content retrieval
  - Quiz submission and auto-grading
  - Lab HCL validation with feedback
  - Progress and leaderboard queries
  - Glossary concept definitions

- **Database Schema**
  - `kb_user_progress` — tracks completion, scores, timestamps per user per chapter
  - `kb_user_badges` — achievement tracking, reputation points
  - `kb_leaderboard_scores` — aggregated ranking scores

- **Frontend Pages**
  - KB curriculum index with chapter cards
  - Chapter detail view with content and navigation
  - Quiz interface with MCQ presentation
  - Lab editor with HCL syntax validation
  - Leaderboard with rankings and badges

- **Features**
  - Interactive quizzes with instant feedback
  - HCL lab exercises with real-time validation
  - Progress tracking and milestone rewards
  - Leaderboard with team/org rankings
  - Badge system for achievement unlocking
  - Chapter progression (unlock next chapter on completion)
  - Streak tracking for engagement

**Files Added/Modified: 39 files (7000+ lines)**
- Backend: 5 core modules + 1 API routes file + 12 curriculum YAML files
- Frontend: 4 React pages + components for quiz/lab interface
- Database migrations for KB schema

---

## Previous Releases

### Infrastructure & State Management
- Remote state backend with PostgreSQL encryption
- State versioning (50-version history) with rollback
- Distributed state locking with lease timeouts
- Terraform-compatible state format

### Authentication & Access Control
- Email/password authentication with bcrypt hashing
- JWT tokens (15-min expiry) and API tokens (tb_ prefix)
- Multi-tenant RBAC: Org → Team → User → Workspace
- First-user-becomes-admin bootstrap flow

### VCS Integration
- GitHub App OAuth integration
- Auto-plan on PR open/sync
- Auto-apply on merge to default branch
- PR comment posting with plan summaries
- Webhook verification (HMAC-SHA256)

### Policy as Code
- Open Policy Agent (OPA) sidecar integration
- 6 starter policies: tags, encryption, security groups, instance sizes, deprecated resources
- 3 enforcement levels: advisory, soft-mandatory, hard-mandatory

### AI Features
- Claude AI for HCL generation from English descriptions
- Code review with AI-powered suggestions
- Resource explanation tool
- Error diagnostics and troubleshooting

### Developer Experience
- Jinja2 template engine (AWS EC2, RDS, VPC; Proxmox VM, LXC)
- Cost estimation from terraform plan
- Drift detection (actual vs desired state)
- Import wizard for guided Terraform imports
- Interactive tutorials and learning guides
- Glossary with 20+ Terraform concepts
- Real-time streaming logs via Server-Sent Events

### Core Tech Stack
- FastAPI 0.115 REST API
- PostgreSQL 16 + SQLAlchemy async
- React 18 + Vite + TailwindCSS
- Typer CLI with Rich formatting
- Docker containers with health checks
