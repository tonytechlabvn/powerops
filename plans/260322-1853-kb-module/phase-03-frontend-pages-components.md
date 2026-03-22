# Phase 3: Frontend Pages & Components

**Status**: Complete
**Priority**: Critical
**Progress**: 100%

## Overview

React pages and components for KB module: curriculum browser, chapter viewer, quiz interface, lab editor, and leaderboard display.

## Key Insights

- Quiz interface needs instant visual feedback (correct/incorrect)
- Lab editor requires syntax highlighting for HCL
- Leaderboard benefits from real-time updates via WebSocket
- Progress display motivates continued learning (progress bars, badges)

## Requirements

### Functional
- Display curriculum with chapter cards
- Show chapter content with navigation
- Present MCQ quiz with answer selection
- Editor for HCL lab code with validation
- Show progress and badges
- Rank display for leaderboard
- Search/filter for glossary

### Non-Functional
- Page load < 1s (including API calls)
- Mobile responsive design
- Accessible WCAG 2.1 AA
- Dark mode support (optional)

## Architecture

### Pages (4 main pages)

**1. Curriculum Page** (`/kb`)
- Chapter grid with cover images
- Progress badges (locked, in-progress, completed)
- Filter by difficulty (beginner, intermediate, advanced)
- Search by chapter title
- Start chapter button
- Stats: completion percentage, total reputation

**2. Chapter Detail Page** (`/kb/:slug`)
- Chapter title and description
- Content sections (markdown rendered)
- Learning objectives
- Estimated time to completion
- Prerequisites (if any)
- Navigation (prev/next chapter)
- Progress indicator
- Buttons: Start Quiz, Do Lab, Mark Complete

**3. Quiz Page** (`/kb/:slug/quiz`)
- Quiz title and instructions
- Question counter (1/10)
- MCQ presentation (4 options)
- Instant feedback (correct/incorrect with explanation)
- Score display
- Retry button
- Pass threshold indicator (70% required)

**4. Lab Page** (`/kb/:slug/lab`)
- Lab title and instructions
- Starter HCL code (read-only example)
- Code editor with syntax highlighting
- Real-time validation (errors/warnings on type)
- Submit button
- Results display (score, errors, suggestions)
- Next chapter prompt on success

**5. Leaderboard Page** (`/kb/leaderboard`)
- Global rankings table (top 100)
- User rank display
- Columns: rank, name, score, badges, completion %
- Team filter option
- Search user by name
- Badge legend

### Components (Reusable)

**ChapterCard**
- Cover image
- Title, description
- Difficulty indicator (color-coded)
- Progress badge
- Click to navigate

**QuizQuestion**
- Question text
- 4 option buttons
- Disabled state during grading
- Feedback message

**CodeEditor**
- Syntax highlighting (HCL/Terraform)
- Line numbers
- Real-time validation display
- Error highlighting
- Theme toggle

**ProgressBar**
- Percentage display
- Color gradient (0-100%)
- Animated transitions
- Label (e.g., "70% Complete")

**Badge**
- Badge icon/image
- Badge name and description
- Unlock criteria
- Tooltip on hover

**RankingRow**
- User rank and name
- Score display
- Badge count
- Completion percentage

## Related Code Files

**Files to Create**:
- `frontend/src/pages/KBCurriculum.tsx`
- `frontend/src/pages/KBChapter.tsx`
- `frontend/src/pages/KBQuiz.tsx`
- `frontend/src/pages/KBLab.tsx`
- `frontend/src/pages/KBLeaderboard.tsx`
- `frontend/src/components/KBChapterCard.tsx`
- `frontend/src/components/KBQuizQuestion.tsx`
- `frontend/src/components/KBCodeEditor.tsx`
- `frontend/src/components/KBProgressBar.tsx`
- `frontend/src/components/KBBadge.tsx`
- `frontend/src/components/KBRankingRow.tsx`
- `frontend/src/hooks/useKBCurriculum.ts`
- `frontend/src/hooks/useKBProgress.ts`
- `frontend/src/hooks/useKBLeaderboard.ts`

**Files to Modify**:
- `frontend/src/App.tsx` (add KB routes)
- `frontend/src/components/Navbar.tsx` (add KB link)
- `frontend/src/index.css` (KB styling)

## Implementation Steps

- [x] Setup KB page routes in React Router
- [x] Build curriculum page with chapter grid
- [x] Build chapter detail page with content
- [x] Build quiz page with MCQ interface
- [x] Build lab page with code editor
- [x] Build leaderboard page with rankings
- [x] Create reusable component library
- [x] Integrate with KB API endpoints
- [x] Add loading states and error handling
- [x] Style with TailwindCSS
- [x] Mobile responsive design
- [x] Write component unit tests
- [x] Integration tests (user flows)

## Todo List

- [x] KBCurriculum page structure
- [x] Chapter grid layout
- [x] Progress filter/search
- [x] KBChapter page content rendering
- [x] Navigation (prev/next)
- [x] Chapter start tracking
- [x] KBQuiz MCQ presentation
- [x] Instant feedback display
- [x] Score calculation
- [x] KBLab code editor (Ace or Monaco)
- [x] HCL syntax highlighting
- [x] Real-time validation display
- [x] Lab submission handling
- [x] KBLeaderboard rankings table
- [x] User rank highlighting
- [x] Pagination (if > 100 users)
- [x] ChapterCard component
- [x] QuizQuestion component
- [x] CodeEditor component
- [x] ProgressBar component
- [x] Badge component display
- [x] Custom hooks for API calls
- [x] Error boundary components
- [x] Loading spinners
- [x] TailwindCSS styling
- [x] Mobile responsiveness
- [x] Accessibility (ARIA labels, keyboard nav)
- [x] Unit tests (90%+ coverage)
- [x] E2E tests (Cypress/Playwright)

## Success Criteria

- All pages render correctly
- API integration working end-to-end
- Mobile responsive on all breakpoints
- Loading time < 1s
- 90%+ component test coverage
- WCAG 2.1 AA accessibility
- No console errors/warnings

## Risk Assessment

**Risk**: Code editor performance with large HCL files
**Mitigation**: Lazy load editor, debounce validation

**Risk**: Leaderboard load time with 1000+ users
**Mitigation**: Pagination, caching top 100, virtual scrolling

**Risk**: Quiz answer spoilers in HTML
**Mitigation**: Server-side answer removal, client-side validation

## Security Considerations

- Sanitize markdown content (XSS prevention)
- Don't expose correct quiz answers in HTML
- Validate HCL code before submission (XSS in labs)
- Protect API calls with auth tokens
- Rate limit rapid quiz submissions (client + server)

## Next Steps

- Move to Phase 4: Leaderboard deep integration
- Implement real-time updates (WebSocket)
- Add badge system and reputation
