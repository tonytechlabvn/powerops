# PowerOps (TerraBot)

Enterprise Terraform automation platform with multi-tenant support, remote state management, policy enforcement, and VCS integration. AI-powered HCL generation and validation via Claude, with approval workflows and real-time streaming.

## Core Features

**Infrastructure & State:**
- **Remote state management** — PostgreSQL backend, AES-256-GCM encryption, state versioning + rollback
- **State locking** — distributed locking with lease timeout (prevents concurrent applies)
- **State versioning** — 50-version history per workspace with pruning

**Teams & Access Control:**
- **Multi-tenant architecture** — Organization → Team → User → Workspace hierarchy
- **RBAC** — workspace-scoped permissions (read/plan/write/admin)
- **Authentication** — email/password (bcrypt), JWT tokens (15-min), API tokens (tb_ prefix)
- **First-user-becomes-admin** — automatic bootstrap flow

**VCS Integration:**
- **GitHub App integration** — JWT OAuth + installation tokens
- **Auto-plan on PR** — automatic terraform plan when PR opens/syncs
- **Auto-apply on merge** — automatic terraform apply when merged to default branch
- **PR comments** — plan summaries posted to GitHub PRs
- **Webhook verification** — HMAC-SHA256 signature validation

**Policy as Code:**
- **OPA sidecar** — Open Policy Agent for policy evaluation
- **6 starter policies** — tags, encryption, security groups, instance sizes, deprecated resources
- **3 enforcement levels** — advisory (logged), soft-mandatory (blockable), hard-mandatory (enforced)
- **Policy sets** — grouping and assignment of policies

**AI-Powered Features:**
- **HCL generation** — Claude writes Terraform from English descriptions
- **Code review** — AI-powered HCL review and suggestions
- **Resource explanation** — ask Claude about any Terraform resource
- **Error diagnostics** — AI debug Terraform errors

**Developer Experience:**
- **Template engine** — Jinja2 blueprints for AWS (EC2, RDS, VPC) and Proxmox
- **Cost estimation** — monthly USD estimates from terraform plan
- **Drift detection** — compare actual vs desired state
- **Import wizard** — guided Terraform import automation
- **Interactive tutorials** — step-by-step guides for beginners
- **Glossary** — 20 Terraform concepts with examples
- **Streaming logs** — real-time terraform output via Server-Sent Events

## Quick Start

```bash
# 1. Clone
git clone https://github.com/your-org/terrabot && cd terrabot

# 2. Install (Python 3.11+)
pip install -e ".[dev]"

# 3. Initialise a workspace
terrabot init ./my-workspace

# 4. Use a template
terrabot template render aws/ec2-web-server --var key_name=my-key

# 5. Plan then apply
terrabot plan ./my-workspace
terrabot apply ./my-workspace
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      PowerOps Platform                          │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │  Typer CLI   │  │  FastAPI     │  │  React / Vite        │  │
│  │  Local Ops   │  │  REST API    │  │  Web Dashboard       │  │
│  └────────┬─────┘  └────────┬─────┘  └──────────────┬───────┘  │
│           │                  │                       │          │
│           └──────────────────┼───────────────────────┘          │
│                              │                                  │
│                    ┌─────────▼──────────┐                       │
│                    │   Core Engine      │                       │
│                    │ ┌────────────────┐ │                       │
│                    │ │ AI Agent       │ │ (Claude)             │
│                    │ │ HCL Validator  │ │                       │
│                    │ │ Cost Estimator │ │                       │
│                    │ │ Tf Runner      │ │                       │
│                    │ └────────────────┘ │                       │
│                    └────────────────────┘                       │
│                              │                                  │
│            ┌─────────────────┼─────────────────┐                │
│            │                 │                 │                │
│    ┌───────▼───────┐  ┌──────▼──────┐  ┌──────▼──────┐         │
│    │    Auth &     │  │   State     │  │ Policy as   │         │
│    │    RBAC       │  │  Management │  │ Code (OPA)  │         │
│    └───────────────┘  └─────────────┘  └─────────────┘         │
│            │                 │                 │                │
│            └─────────────────┼─────────────────┘                │
│                              │                                  │
│    ┌─────────────────────────▼──────────────────────────┐      │
│    │   PostgreSQL 16 + asyncpg (connection pooling)     │      │
│    │   Org → Team → User → Workspace → State hierarchy  │      │
│    └────────────────────────────────────────────────────┘      │
│                              │                                  │
└──────────────────────────────┼──────────────────────────────────┘
                               │
                ┌──────────────┼──────────────┐
                │              │              │
         ┌──────▼────┐  ┌──────▼──────┐  ┌───▼─────────┐
         │ GitHub    │  │ Terraform   │  │ OPA         │
         │ API/VCS   │  │ CLI         │  │ 0.70.0      │
         └───────────┘  └─────────────┘  └─────────────┘
```

## Tech Stack

| Layer | Technology |
|-------|------------|
| **API** | FastAPI 0.115, uvicorn |
| **CLI** | Typer, Rich |
| **Authentication** | JWT (HS256), bcrypt, API tokens |
| **Database** | PostgreSQL 16 + SQLAlchemy async + asyncpg |
| **State Encryption** | AES-256-GCM (cryptography) |
| **VCS Integration** | GitHub App API, JWT signing |
| **Policy Engine** | Open Policy Agent 0.70.0 (OPA) |
| **AI** | Anthropic Claude (claude-sonnet) |
| **Templates** | Jinja2 |
| **Validation** | python-hcl2 |
| **Frontend** | React 18, Vite, TypeScript, TailwindCSS |
| **Testing** | pytest, pytest-asyncio, httpx |
| **Containerization** | Docker, Docker Compose |

## Deployment

**Server:** powerops.tonytechlab.com (72.60.211.23)

**Docker Containers:**
- `postgres:16-alpine` - State and metadata store
- `openpolicyagent/opa:0.70.0` - Policy evaluation sidecar
- `powerops` - FastAPI application server

All containers run on the `tony-net` Docker network with health checks and automatic restart.

**Configuration via environment variables:**
```bash
TERRABOT_ANTHROPIC_API_KEY=sk-ant-...
TERRABOT_DB_URL=postgresql+asyncpg://powerops:password@postgres:5432/powerops
TERRABOT_STATE_ENCRYPTION_KEY=<base64-32-byte-key>
TERRABOT_JWT_SECRET=<32+-byte-random-secret>
TERRABOT_GITHUB_APP_ID=123456
TERRABOT_GITHUB_WEBHOOK_SECRET=webhook-secret
TERRABOT_OPA_URL=http://opa:8181
```

## API Highlights

**Authentication:**
- `POST /api/auth/register` - Create account (first user becomes admin)
- `POST /api/auth/login` - Get JWT + refresh token
- `POST /api/auth/refresh` - Renew access token

**State Management:**
- `GET /api/state/{workspace_id}` - Download state (terraform backend compatible)
- `POST /api/state/{workspace_id}` - Upload state
- `POST/DELETE /api/state/{workspace_id}/lock` - Distributed state locking
- `GET /api/state/{workspace_id}/versions` - State version history
- `POST /api/state/{workspace_id}/rollback/{version_id}` - Restore previous state

**VCS:**
- `POST /api/vcs/connect` - Link workspace to GitHub repo
- `POST /api/webhooks/github` - Receive GitHub webhooks
- `GET /api/vcs/{workspace_id}/runs` - List VCS-triggered runs

**Policy:**
- `GET /api/policies` - List policies
- `POST /api/policies` - Create policy (upload Rego file)
- `GET /api/policies/{workspace_id}/evaluate` - Preview policy evaluation

**Operations:**
- `POST /api/deploy/plan` - Run terraform plan
- `POST /api/deploy/apply` - Run terraform apply
- `GET /api/jobs/{job_id}` - Job status and logs
- `GET /api/stream/{job_id}` - Real-time logs (Server-Sent Events)

## Documentation

- **[system-architecture.md](../docs/system-architecture.md)** - Detailed architecture, data flows, and configuration
- **[codebase-summary.md](../docs/codebase-summary.md)** - Module inventory, file organization, API reference
- **[code-standards.md](../docs/code-standards.md)** - Coding conventions and patterns

## Contributing

1. Fork the repo and create a feature branch
2. Install dev dependencies: `pip install -e ".[dev]"`
3. Run tests: `pytest tests/unit/ -v`
4. Submit a pull request with a clear description

## License

MIT
