# System Architecture

## Overview

PowerOps is an enterprise Terraform automation platform with multi-tenant support, remote state management, policy enforcement, and VCS integration.

## Core Layers

### API Layer

**FastAPI 0.115** REST API with streaming support:
- Authentication endpoints: register, login, token refresh
- State management: CRUD operations, versioning, locking
- Deployment: plan, apply, destroy
- VCS webhook integration
- Policy evaluation and management

### Backend Services

#### Core Engine
- **AI Agent** (Claude Sonnet) — HCL generation, code review, resource explanation, error diagnostics
- **HCL Validator** — Syntax validation, resource type checking
- **Cost Estimator** — Monthly USD cost projections from terraform plan
- **Terraform Runner** — Subprocess execution with streaming logs
- **Workspace Manager** — Local workspace initialization and management
- **Drift Detector** — Actual vs desired state comparison
- **Glossary & Tutorials** — Terraform concept definitions and interactive guides

#### Knowledge Base Module
Located at `backend/kb/`:
- **CurriculumLoader** — 12-chapter Terraform curriculum loading and caching
- **QuizEngine** — MCQ question generation, answer grading, streak tracking
- **LabValidator** — HCL code validation in lab exercises
- **ProgressTracker** — User progress storage and milestone tracking
- **Leaderboard** — Team/org rankings with badges and reputation scoring

12-chapter Terraform Curriculum:
1. IaC Intro
2. HCL Syntax
3. Providers & Init
4. Resources
5. Variables & Outputs
6. Data Sources
7. State Management
8. Modules
9. Meta-Arguments
10. Workspaces & Environments
11. CI/CD & VCS Workflows
12. Advanced Patterns

#### Authentication & RBAC
- JWT token authentication (HS256, 15-min expiry)
- API tokens (tb_ prefix)
- bcrypt password hashing
- Multi-tenant hierarchy: Org → Team → User → Workspace
- Workspace-scoped permissions: read, plan, write, admin

#### State Management
- PostgreSQL backend with asyncpg connection pooling
- AES-256-GCM encryption for sensitive data
- Distributed state locking with lease timeouts
- 50-version history per workspace with pruning
- Terraform-compatible state format

#### VCS Integration
- GitHub App OAuth integration with JWT signing
- Webhook verification (HMAC-SHA256)
- Auto-plan on PR open/sync
- Auto-apply on merge to default branch
- PR comment posting with plan summaries

#### Policy as Code
- Open Policy Agent (OPA 0.70.0) sidecar
- 6 starter policies: tags, encryption, security groups, instance sizes, deprecated resources
- 3 enforcement levels: advisory, soft-mandatory, hard-mandatory
- Policy sets for grouping and assignment

### Frontend Layer

**React 18 + Vite + TypeScript**
- TailwindCSS for styling
- WebSocket/Server-Sent Events for streaming logs
- KB module routes:
  - `/kb` — curriculum overview with chapter cards
  - `/kb/:slug` — full chapter content
  - `/kb/:slug/quiz` — quiz interface with MCQ
  - `/kb/:slug/lab` — lab editor with HCL validation
  - `/kb/leaderboard` — team rankings with badges

### Database Layer

**PostgreSQL 16 + SQLAlchemy Async**

Key tables for KB module:
- `kb_user_progress` — chapter completion, quiz scores, lab attempts
- `kb_user_badges` — achievement tracking, reputation points
- `kb_leaderboard_scores` — aggregated rankings

Main tables:
- `organizations`, `teams`, `users`, `workspaces`
- `state_versions`, `state_locks`
- `policies`, `policy_sets`
- `audit_logs`

### External Services

- **GitHub API** — VCS integration, webhook webhooks
- **Terraform CLI** — Infrastructure deployment
- **Anthropic Claude API** — AI-powered features
- **OPA** — Policy evaluation via sidecar

## KB Module API

12 endpoints under `/api/kb/`:

```
GET    /api/kb/curriculum              — List chapters + user progress
GET    /api/kb/chapters/{slug}         — Full chapter content
POST   /api/kb/chapters/{slug}/start   — Mark chapter started
GET    /api/kb/chapters/{slug}/quiz    — Quiz questions (no answers)
POST   /api/kb/chapters/{slug}/quiz    — Submit quiz answers + grading
GET    /api/kb/chapters/{slug}/lab     — Lab instructions + starter code
POST   /api/kb/chapters/{slug}/lab/validate — Validate HCL submission
POST   /api/kb/chapters/{slug}/complete — Mark chapter completed
GET    /api/kb/progress                — User overall progress
GET    /api/kb/leaderboard             — Team/org rankings
GET    /api/kb/glossary                — All glossary concepts
GET    /api/kb/glossary/{term}         — Single glossary definition
```

## Data Flow

### KB Learning Flow
1. User GET `/api/kb/curriculum` → loads chapter list with progress
2. User GET `/api/kb/chapters/{slug}` → loads chapter content
3. User POST `/api/kb/chapters/{slug}/start` → tracks start time
4. User GET `/api/kb/chapters/{slug}/quiz` → loads MCQ (no answers)
5. User POST `/api/kb/chapters/{slug}/quiz` → submits answers, receives grade + feedback
6. User GET `/api/kb/chapters/{slug}/lab` → loads lab instructions + starter
7. User POST `/api/kb/chapters/{slug}/lab/validate` → validates HCL, receives score
8. User POST `/api/kb/chapters/{slug}/complete` → marks complete, unlocks next chapter
9. User GET `/api/kb/leaderboard` → sees rankings, badges, reputation

### Deployment Flow
1. CLI or UI triggers plan → Terraform Runner executes `terraform plan`
2. Plan output → Cost Estimator projects monthly costs
3. Plan output → OPA evaluates policies
4. User approves → Plan stored in PostgreSQL
5. Apply triggered → Terraform Runner executes `terraform apply`
6. Apply output → streamed via SSE to UI
7. State downloaded → encrypted and versioned in PostgreSQL

### VCS Flow
1. GitHub webhook received → verified via HMAC-SHA256
2. PR opened/synced → Terraform plan auto-triggered
3. Plan results → posted as GitHub PR comment
4. PR merged → Terraform apply auto-triggered
5. Apply results → stored in audit logs

## Tech Stack Summary

| Layer | Technology |
|-------|-----------|
| API | FastAPI 0.115, uvicorn |
| CLI | Typer, Rich |
| Authentication | JWT (HS256), bcrypt, API tokens |
| Database | PostgreSQL 16 + SQLAlchemy async + asyncpg |
| State Encryption | AES-256-GCM |
| VCS | GitHub App API, JWT signing |
| Policy Engine | Open Policy Agent 0.70.0 |
| AI | Anthropic Claude (claude-sonnet) |
| Templates | Jinja2 |
| Validation | python-hcl2 |
| Frontend | React 18, Vite, TypeScript, TailwindCSS |
| Testing | pytest, pytest-asyncio, httpx |
| Containers | Docker, Docker Compose |

## Deployment

**Server**: powerops.tonytechlab.com (72.60.211.23)

Docker containers on `tony-net` bridge network:
- `postgres:16-alpine` — State and metadata
- `openpolicyagent/opa:0.70.0` — Policy sidecar
- `powerops` — FastAPI application

All containers have health checks and auto-restart policy.

## Configuration

Environment variables:
```
TERRABOT_ANTHROPIC_API_KEY        — Claude API key
TERRABOT_DB_URL                   — PostgreSQL connection string
TERRABOT_STATE_ENCRYPTION_KEY     — Base64-encoded 32-byte AES key
TERRABOT_JWT_SECRET               — 32+ byte random secret
TERRABOT_GITHUB_APP_ID            — GitHub App ID for OAuth
TERRABOT_GITHUB_WEBHOOK_SECRET    — Webhook signature verification
TERRABOT_OPA_URL                  — OPA sidecar endpoint
```
