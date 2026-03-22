# Phase 2: API Routes & Schemas

**Status**: Complete
**Priority**: Critical
**Progress**: 100%

## Overview

12 REST API endpoints for KB operations: curriculum browsing, quiz submission, lab validation, progress tracking, and leaderboard queries.

## Key Insights

- API schema reuse across multiple endpoints (ChapterSummary, QuizResponse, etc.)
- Streaming responses needed for large curriculum loads
- Rate limiting essential for quiz submission (prevent spam)
- Pagination required for leaderboard (100+ users)

## Requirements

### Functional
- List curriculum with user progress
- Fetch chapter details
- Submit and grade quizzes
- Validate HCL labs
- Track chapter completion
- Query progress overview
- Rank users on leaderboard
- Retrieve glossary definitions

### Non-Functional
- API response < 200ms (p95)
- Support 1000 concurrent requests
- Rate limit: 10 quiz submissions/minute per user
- Pagination: 50 items per page

## Architecture

### API Endpoints (12 total)

```
GET    /api/kb/curriculum
GET    /api/kb/chapters/{slug}
POST   /api/kb/chapters/{slug}/start
GET    /api/kb/chapters/{slug}/quiz
POST   /api/kb/chapters/{slug}/quiz
GET    /api/kb/chapters/{slug}/lab
POST   /api/kb/chapters/{slug}/lab/validate
POST   /api/kb/chapters/{slug}/complete
GET    /api/kb/progress
GET    /api/kb/leaderboard
GET    /api/kb/glossary
GET    /api/kb/glossary/{term}
```

### Request/Response Schemas

**CurriculumListResponse**
- chapters: ChapterSummary[]
- progress: UserProgress
- stats: { total: int, completed: int, inProgress: int }

**ChapterDetailResponse**
- chapter: Chapter
- content: str
- prerequisites: str[]
- nextChapter: str?
- progress: UserProgress

**QuizSubmissionRequest**
- chapter_slug: str
- answers: { question_id: int, selected_option: int }[]

**QuizGradingResponse**
- score: int
- passed: bool
- feedback: str
- correct_answers: { question_id: int, correct_option: int }[]

**LabValidationRequest**
- chapter_slug: str
- hcl_code: str

**LabValidationResponse**
- valid: bool
- score: int
- errors: { line: int, message: str }[]
- warnings: { line: int, message: str }[]
- suggestions: str[]

**ProgressResponse**
- user_id: int
- chapters_completed: int
- chapters_total: int
- current_chapter: str?
- quiz_average: float
- lab_average: float
- badges: Badge[]
- reputation: int

**LeaderboardResponse**
- rankings: { rank: int, user_name: str, score: int, badges: int, completion: float }[]
- user_rank: int
- user_score: int

## Related Code Files

**Files to Create**:
- `backend/api/routes/kb-routes.py`
- `backend/api/schemas/kb-schemas.py`

**Files to Modify**:
- `backend/api/__init__.py` (register router)
- `backend/api/middleware/auth-middleware.py` (require auth for KB routes)

## Implementation Steps

- [x] Design request/response schemas
- [x] Implement curriculum list endpoint
- [x] Implement chapter detail endpoint
- [x] Implement chapter start tracking
- [x] Implement quiz retrieval endpoint
- [x] Implement quiz submission + grading
- [x] Implement lab instructions endpoint
- [x] Implement lab validation endpoint
- [x] Implement chapter completion endpoint
- [x] Implement progress query endpoint
- [x] Implement leaderboard query endpoint
- [x] Implement glossary endpoints
- [x] Add authentication middleware
- [x] Add rate limiting (quiz submissions)
- [x] Add pagination (leaderboard)
- [x] Write integration tests

## Todo List

- [x] Create Pydantic schemas for all request/response types
- [x] Curriculum list with user progress filtering
- [x] Chapter detail with content rendering
- [x] Chapter start: update progress timestamp
- [x] Quiz retrieval: load questions (hide answers)
- [x] Quiz submission: grade answers, return feedback
- [x] Lab instructions: fetch starter code
- [x] Lab validation: HCL checking + scoring
- [x] Chapter complete: unlock next chapter, award badge
- [x] Progress overview: aggregate user stats
- [x] Leaderboard: top 100 users, pagination
- [x] Glossary: integrate with learning module
- [x] Error handling for all endpoints
- [x] Request validation
- [x] Response serialization
- [x] Unit tests for all endpoints
- [x] Integration tests (full request-response cycle)

## Success Criteria

- All 12 endpoints implemented
- Request/response validation with Pydantic
- 95%+ test coverage for API layer
- API response time < 200ms (p95)
- Rate limiting enforced on quiz endpoint
- No SQL injection vulnerabilities
- Proper error messages and status codes

## Risk Assessment

**Risk**: Quiz submission spam
**Mitigation**: Redis rate limiting, CAPTCHA on repeated failures

**Risk**: Large leaderboard queries (1000+ users)
**Mitigation**: Database indexing, caching top 100, pagination

**Risk**: Missing authentication on endpoints
**Mitigation**: Middleware auth check, decorator-based protection

## Security Considerations

- All endpoints require authentication (JWT token)
- Rate limit quiz submissions (10/minute per user)
- Validate all user input (HCL code, quiz answers)
- Sanitize error messages (no SQL leakage)
- Log all modifications to progress/scores

## Next Steps

- Move to Phase 3: Frontend implementation
- Wire API calls to React components
- Implement loading states and error handling
