# Phase 4: Leaderboard Deep Integration

**Status**: Complete
**Priority**: High
**Progress**: 100%

## Overview

Leaderboard system with real-time rankings, badge system, reputation scoring, and team/org aggregation.

## Key Insights

- Reputation scoring drives engagement (visible progress toward rewards)
- Badge unlocks create milestone celebrations (gamification)
- Team filtering allows friendly competition within groups
- Real-time updates create FOMO and urgency

## Requirements

### Functional
- Calculate user reputation scores
- Award badges on milestones
- Rank users globally and by team/org
- Support real-time score updates
- Display historical progression
- Provide badge details and unlock criteria
- Show top performers per time period

### Non-Functional
- Leaderboard query < 100ms (p95)
- Real-time updates within 1s
- Handle 1000 concurrent viewers
- Score calculation idempotent

## Architecture

### Reputation System

**Points per Activity**:
- Chapter start: +5 points
- Quiz completion (70%+): +20 points
- Quiz perfection (100%): +50 points
- Lab completion: +30 points
- Lab optimization (best practices): +15 bonus
- Streak bonus (consecutive days): +10 per day
- First to solve lab: +100 bonus

**Total**: ~400 points per completed chapter

### Badge System

**Beginner Badges**:
- First Step (complete chapter 1)
- Quiz Master (80% avg on first 3 chapters)
- Lab Validator (complete first lab)

**Intermediate Badges**:
- HCL Expert (complete chapters 1-6)
- State Master (complete chapter 7)
- Modular Thinking (complete chapter 8)

**Advanced Badges**:
- Terraform Architect (complete all 12 chapters)
- Perfect Score (100% on all quizzes)
- Community Helper (assist 10 peers)
- Week Warrior (7-day learning streak)

**Special Badges**:
- Leaderboard Top 10 (monthly)
- Speed Runner (complete chapter in < 2 hours)
- All-Nighter (complete 3 chapters in 24 hours)

### Ranking Algorithm

```
Score = (reputation_points) + (badges_count * 10) + (completion_pct * 100)
Rank = ORDER BY Score DESC LIMIT 100
```

### Real-Time Updates

- WebSocket connection for live score updates
- Broadcast score changes to connected clients
- Update frequency: every 5 seconds (batched)
- Graceful fallback to polling if WebSocket unavailable

## Related Code Files

**Files to Create/Modify**:
- `backend/kb/leaderboard.py` (core logic)
- `backend/api/routes/kb-routes.py` (endpoint)
- `backend/api/websockets/kb-leaderboard.py` (WebSocket)
- `frontend/src/pages/KBLeaderboard.tsx` (display)
- `frontend/src/hooks/useKBLeaderboard.ts` (API hook)
- `backend/db/models.py` (badge, reputation tables)

## Implementation Steps

- [x] Design reputation point system
- [x] Implement point calculation logic
- [x] Design badge unlock criteria
- [x] Implement badge assignment system
- [x] Create ranking algorithm
- [x] Optimize leaderboard queries
- [x] Implement WebSocket for real-time updates
- [x] Create leaderboard API endpoint
- [x] Add team/org filtering
- [x] Build leaderboard UI with React
- [x] Integrate real-time updates
- [x] Add badge display and tooltips
- [x] Write tests for all components

## Todo List

- [x] Point system design document
- [x] calculateReputation() function
- [x] awardPoints() transaction logic
- [x] checkAndAwardBadge() logic
- [x] getLeaderboard() with pagination
- [x] getLeaderboard(team_id) filtered
- [x] getRankingByTimeframe() (daily/weekly/all-time)
- [x] WebSocket /ws/kb/leaderboard endpoint
- [x] Broadcast score updates to clients
- [x] Client reconnect handling
- [x] Leaderboard page component
- [x] Real-time score animation
- [x] Badge display with tooltips
- [x] User rank highlighting
- [x] Team filter dropdown
- [x] Time period selector
- [x] Historical view (weekly top 10)
- [x] Unit tests for reputation calc
- [x] Integration tests for badge awards
- [x] Load test (1000 concurrent viewers)
- [x] WebSocket test (connection/reconnect)

## Success Criteria

- Reputation calculated correctly for all activities
- Badges awarded on proper unlock conditions
- Leaderboard query < 100ms for 1000+ users
- Real-time updates within 1s
- 95%+ test coverage
- No double-awarding of badges
- Reputation points immutable once awarded

## Risk Assessment

**Risk**: Race condition in badge awards (awarded twice)
**Mitigation**: Database unique constraint, idempotent logic

**Risk**: WebSocket connection flakiness
**Mitigation**: Fallback to polling, auto-reconnect with exponential backoff

**Risk**: Leaderboard query performance (N+1 problem)
**Mitigation**: Database indexing, aggregated views, caching top 100

## Security Considerations

- Prevent reputation manipulation (no client-side point claims)
- Validate all point sources server-side
- Rate limit badge checks (prevent spam)
- Audit all reputation changes
- Prevent team-swapping mid-competition

## Next Steps

- Move to Phase 5: Curriculum content creation
- Finalize all 12 chapters with content
- Review and test complete system
