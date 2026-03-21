# TerraBot

AI-powered Terraform automation platform. Combines a FastAPI backend, Typer CLI, and Claude AI to
generate, validate, plan, and apply Terraform configurations — with interactive tutorials and cost
estimates built in.

## Features

- **AI generation** — describe infrastructure in plain English; Claude writes the HCL
- **Template engine** — Jinja2 blueprints for common AWS and Proxmox patterns
- **HCL validation** — syntax checking and resource-type whitelisting before any apply
- **Cost estimation** — static monthly USD estimates from `terraform plan` JSON output
- **Approval workflow** — human-in-the-loop gate between plan and apply
- **Interactive tutorials** — step-by-step guides for beginners (5 tutorials, 2 providers)
- **Glossary** — 20 Terraform concepts with examples and related terms
- **Streaming output** — real-time terraform logs via Server-Sent Events

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
┌─────────────────────────────────────────────────────┐
│                   TerraBot                          │
│                                                     │
│  ┌──────────┐   ┌──────────┐   ┌────────────────┐  │
│  │  Typer   │   │ FastAPI  │   │  React / Vite  │  │
│  │   CLI    │   │   API    │   │   Frontend     │  │
│  └────┬─────┘   └────┬─────┘   └───────┬────────┘  │
│       │              │                  │           │
│       └──────────────┼──────────────────┘           │
│                      │                              │
│          ┌───────────▼───────────┐                  │
│          │      Core Engine      │                  │
│          │  hcl-validator        │                  │
│          │  template-engine      │                  │
│          │  cost-estimator       │                  │
│          │  terraform-runner     │                  │
│          │  ai-agent (Claude)    │                  │
│          └───────────┬───────────┘                  │
│                      │                              │
│          ┌───────────▼───────────┐                  │
│          │  SQLite (aiosqlite)   │                  │
│          │  Job / approval state │                  │
│          └───────────────────────┘                  │
└─────────────────────────────────────────────────────┘
```

## Tech Stack

| Layer      | Technology                        |
|------------|-----------------------------------|
| API        | FastAPI 0.115, uvicorn            |
| CLI        | Typer, Rich                       |
| AI         | Anthropic Claude (claude-sonnet)  |
| Templates  | Jinja2                            |
| Validation | python-hcl2                       |
| Database   | SQLAlchemy async + aiosqlite      |
| Frontend   | React, Vite, TypeScript           |
| Tests      | pytest, pytest-asyncio, httpx     |

## Contributing

1. Fork the repo and create a feature branch
2. Install dev dependencies: `pip install -e ".[dev]"`
3. Run tests: `pytest tests/unit/ -v`
4. Submit a pull request with a clear description

## License

MIT
