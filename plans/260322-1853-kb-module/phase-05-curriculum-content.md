# Phase 5: Curriculum Content

**Status**: Complete
**Priority**: Critical
**Progress**: 100%

## Overview

Creation of 12 comprehensive Terraform curriculum chapters with learning objectives, quiz questions, lab exercises, and supplementary materials.

## Key Insights

- Content progression: beginner → intermediate → advanced
- Labs build on previous chapters (incremental complexity)
- Quiz difficulty increases with chapter number
- Real-world examples increase retention
- Estimated time per chapter: 45-90 minutes

## Requirements

### Functional
- 12 chapters covering Terraform fundamentals to advanced patterns
- 80+ quiz questions (MCQ format)
- 12 lab exercises with HCL validation
- Learning objectives for each chapter
- Prerequisites and dependencies
- Real-world examples and case studies
- Best practices and anti-patterns

### Non-Functional
- Content optimized for reading (< 8 min/section)
- Code examples syntax highlighted
- Estimated time to completion accurate
- Mobile-friendly formatting

## Architecture

### Chapter Structure

**Content Template** (each chapter):
```yaml
slug: string              # URL identifier
title: string             # Chapter title
description: string       # 1-2 sentence summary
difficulty: enum          # beginner, intermediate, advanced
estimated_time: int       # minutes
objectives: string[]      # Learning goals
prerequisites: string[]   # Required prior chapters
sections:
  - title: string
    content: markdown
    examples: code_block[]
quiz:
  - question: string
    options: string[4]
    correct_index: int
    explanation: string
lab:
  title: string
  description: string
  starter_code: hcl
  solution_code: hcl
  validation_rules: rule[]
  estimated_time: int
glossary_terms: string[]  # Links to glossary
further_reading: link[]
```

### 12 Chapters

**Chapter 1: Infrastructure as Code (IaC) Intro**
- IaC concepts and benefits
- Terraform overview
- Declarative vs imperative
- State and backends (intro)
- Quiz: 5 questions
- Lab: Create first Terraform config

**Chapter 2: HCL Syntax Fundamentals**
- HCL syntax basics
- Resources and arguments
- Data types (string, number, bool, list, map)
- Variables and locals
- Quiz: 8 questions
- Lab: Write multi-resource config

**Chapter 3: Providers and Terraform Init**
- Provider concept
- AWS provider setup
- Terraform init workflow
- Required version constraints
- Quiz: 7 questions
- Lab: Configure AWS provider

**Chapter 4: Resources and Attributes**
- Resource blocks
- Meta-arguments (count, for_each, depends_on)
- Resource references
- Implicit dependencies
- Quiz: 8 questions
- Lab: Create interdependent resources

**Chapter 5: Variables and Outputs**
- Input variables
- Variable validation
- Local values
- Output values
- Sensitive values
- Quiz: 8 questions
- Lab: Parameterize configuration

**Chapter 6: Data Sources**
- Data source concept
- Common data sources (AMI, VPC)
- Filtering and arguments
- Using data outputs
- Quiz: 6 questions
- Lab: Reference existing infrastructure

**Chapter 7: State Management**
- State file purpose and content
- Remote state backends
- State locking
- State versioning and rollback
- Sensitive data handling
- Quiz: 9 questions
- Lab: Configure PostgreSQL backend

**Chapter 8: Terraform Modules**
- Module structure
- Creating reusable modules
- Module sources
- Input/output variables
- Best practices
- Quiz: 8 questions
- Lab: Create and use custom module

**Chapter 9: Meta-Arguments Deep Dive**
- count and for_each patterns
- depends_on explicit dependencies
- lifecycle rules (create_before_destroy)
- triggers and replace_triggered_by
- Quiz: 8 questions
- Lab: Implement advanced patterns

**Chapter 10: Workspaces and Environments**
- Workspace concept
- Creating and switching workspaces
- Environment-specific configs
- Naming conventions
- Quiz: 6 questions
- Lab: Multi-environment setup

**Chapter 11: CI/CD and VCS Workflows**
- GitHub and GitLab integration
- Terraform Cloud/Enterprise intro
- Auto-plan on PR
- Auto-apply on merge
- Policy enforcement
- Quiz: 8 questions
- Lab: Setup GitHub App integration

**Chapter 12: Advanced Patterns**
- Monorepo vs multi-repo
- Dynamic blocks
- Conditional logic
- Complex transformations
- Testing and validation
- Disaster recovery
- Quiz: 10 questions
- Lab: Advanced multi-region deployment

## Related Code Files

**Files to Create**:
- `backend/kb/curriculum/01-iac-intro.yaml`
- `backend/kb/curriculum/02-hcl-syntax.yaml`
- `backend/kb/curriculum/03-providers-init.yaml`
- `backend/kb/curriculum/04-resources.yaml`
- `backend/kb/curriculum/05-variables-outputs.yaml`
- `backend/kb/curriculum/06-data-sources.yaml`
- `backend/kb/curriculum/07-state-management.yaml`
- `backend/kb/curriculum/08-modules.yaml`
- `backend/kb/curriculum/09-meta-arguments.yaml`
- `backend/kb/curriculum/10-workspaces-environments.yaml`
- `backend/kb/curriculum/11-cicd-vcs-workflows.yaml`
- `backend/kb/curriculum/12-advanced-patterns.yaml`

**Files to Modify**:
- `backend/kb/curriculum-loader.py` (load all 12 chapters)

## Implementation Steps

- [x] Content outline for all 12 chapters
- [x] Write Chapter 1: IaC Intro (5 sections, 5 quiz, 1 lab)
- [x] Write Chapter 2: HCL Syntax (6 sections, 8 quiz, 1 lab)
- [x] Write Chapter 3: Providers & Init (5 sections, 7 quiz, 1 lab)
- [x] Write Chapter 4: Resources (6 sections, 8 quiz, 1 lab)
- [x] Write Chapter 5: Variables & Outputs (6 sections, 8 quiz, 1 lab)
- [x] Write Chapter 6: Data Sources (5 sections, 6 quiz, 1 lab)
- [x] Write Chapter 7: State Management (7 sections, 9 quiz, 1 lab)
- [x] Write Chapter 8: Modules (6 sections, 8 quiz, 1 lab)
- [x] Write Chapter 9: Meta-Arguments (6 sections, 8 quiz, 1 lab)
- [x] Write Chapter 10: Workspaces (5 sections, 6 quiz, 1 lab)
- [x] Write Chapter 11: CI/CD & VCS (6 sections, 8 quiz, 1 lab)
- [x] Write Chapter 12: Advanced Patterns (7 sections, 10 quiz, 1 lab)
- [x] Create code examples for all labs
- [x] Review content for accuracy
- [x] Test all lab validations
- [x] Add glossary links
- [x] Proofread all chapters

## Todo List

- [x] Chapter 1 content complete
- [x] Chapter 1 quiz questions (5 MCQ)
- [x] Chapter 1 lab (starter + solution)
- [x] Chapter 2 content complete
- [x] Chapter 2 quiz questions (8 MCQ)
- [x] Chapter 2 lab (starter + solution)
- [x] Chapter 3 content complete
- [x] Chapter 3 quiz questions (7 MCQ)
- [x] Chapter 3 lab (starter + solution)
- [x] Chapter 4 content complete
- [x] Chapter 4 quiz questions (8 MCQ)
- [x] Chapter 4 lab (starter + solution)
- [x] Chapter 5 content complete
- [x] Chapter 5 quiz questions (8 MCQ)
- [x] Chapter 5 lab (starter + solution)
- [x] Chapter 6 content complete
- [x] Chapter 6 quiz questions (6 MCQ)
- [x] Chapter 6 lab (starter + solution)
- [x] Chapter 7 content complete
- [x] Chapter 7 quiz questions (9 MCQ)
- [x] Chapter 7 lab (starter + solution)
- [x] Chapter 8 content complete
- [x] Chapter 8 quiz questions (8 MCQ)
- [x] Chapter 8 lab (starter + solution)
- [x] Chapter 9 content complete
- [x] Chapter 9 quiz questions (8 MCQ)
- [x] Chapter 9 lab (starter + solution)
- [x] Chapter 10 content complete
- [x] Chapter 10 quiz questions (6 MCQ)
- [x] Chapter 10 lab (starter + solution)
- [x] Chapter 11 content complete
- [x] Chapter 11 quiz questions (8 MCQ)
- [x] Chapter 11 lab (starter + solution)
- [x] Chapter 12 content complete
- [x] Chapter 12 quiz questions (10 MCQ)
- [x] Chapter 12 lab (starter + solution)
- [x] Verify all YAML syntax
- [x] Test all lab validations
- [x] Content review for technical accuracy
- [x] Accessibility review (alt text, contrast)

## Success Criteria

- All 12 chapters deployed and accessible
- 80+ quiz questions covering all topics
- 12 lab exercises validated successfully
- Content accurate and pedagogically sound
- Estimated completion times realistic
- Cross-chapter consistency maintained
- Zero typos/grammatical errors
- Labs progressively increase in difficulty

## Risk Assessment

**Risk**: Inconsistent quiz difficulty
**Mitigation**: Difficulty matrix per chapter, peer review

**Risk**: Lab validations too strict/lenient
**Mitigation**: Test with multiple solutions, allow variations

**Risk**: Content becomes outdated (Terraform version changes)
**Mitigation**: Version pin, quarterly review, compatibility notes

## Content Quality Standards

- Code examples follow HashiCorp best practices
- Content accessible to beginners (explain jargon)
- Real-world scenarios and use cases included
- Common mistakes and pitfalls highlighted
- References to official Terraform docs
- Clear learning objectives for each section

## Next Steps

- Deploy KB module to production
- Monitor user engagement metrics
- Gather feedback for content improvements
- Plan advanced learning features (certifications, peer review)
