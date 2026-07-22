# Crawl Summary and Admin Reanalysis Design

## Goal

Generate the first AI summary automatically after crawling, allow signed-in members to retry only missing or failed summaries, and allow the system administrator to force regeneration of a completed summary.

## Current Production Evidence

- The crawler stores new boards with `analysis_status = pending`.
- The board-service analysis worker continuously claims pending rows and persists their summaries.
- Production currently contains 38,203 completed analyses and 906 failed analyses.
- The initial system administrator is the existing Kakao identity `kakao:3891969863` (`dev-user`).

## Roles

Store a role on each user:

- `member`: the default for all users.
- `system_admin`: may force regeneration of completed summaries.

The existing Kakao user `3891969863` is promoted idempotently to `system_admin` during the user-schema bootstrap. Future administrators are managed by changing the stored role rather than adding identities to application code.

The access token carries the stored role. The API gateway validates the token, removes caller-supplied identity and role headers, and forwards a trusted `X-User-Role` header with the existing identity headers. Downstream principals expose the role and provide separate authenticated-member and system-admin dependencies.

## Summary Flows

### Automatic first summary

1. The crawler inserts a new board with `analysis_status = pending`.
2. The existing board-service worker claims the row, runs the fixed server-side analysis, and stores the summary, tags, engagement score, and reason.
3. The public board response exposes the stored result. Visitors do not initiate inference.
4. Existing worker retry behavior remains the first line of recovery.

### Member retry

1. A signed-in member may request a retry only when the stored analysis is missing or has status `failed`.
2. The repository resets the retry counter and error, changes the status to `pending`, and gives the request user priority.
3. Pending or processing work is reused and is not queued twice.
4. A completed analysis cannot be changed through the member retry endpoint.

### System-admin regeneration

1. A system administrator may request regeneration for any existing board.
2. The repository clears the completed analysis fields and prior error state, resets retries, and queues the board at administrator priority.
3. The same background worker produces and persists the replacement result.
4. Non-admin callers receive HTTP 403. Anonymous callers receive HTTP 401.

## API Boundaries

- `GET /api/boards/{board_id}/ai` remains public and read-only.
- `POST /api/boards/{board_id}/ai/retry` requires an authenticated member and accepts only missing or failed analysis.
- `POST /api/boards/{board_id}/ai/regenerate` requires `system_admin` and may replace completed analysis.
- Likes and image OCR retain their existing authentication requirements.
- The old click-triggered in-memory analysis-job API and polling flow are removed because the persistent database queue and worker own analysis execution.

Both mutation endpoints return the persistent board-analysis status. The frontend refreshes the board query while status is pending or processing instead of polling an in-memory job UUID.

## Frontend Behavior

- Opening a board never starts analysis automatically.
- Anonymous visitors see the stored summary or the current pending, failed, or unavailable state.
- Signed-in members see a retry action only for missing or failed analysis.
- The system administrator also sees a regenerate action for completed analysis.
- The current authenticated-user response includes the role so the UI can render the correct action, while the backend remains the authorization authority.

## Error Handling

- Unknown board IDs return HTTP 404.
- Anonymous retry or regeneration returns HTTP 401.
- A member retry against a completed analysis returns HTTP 409.
- A non-admin regeneration request returns HTTP 403.
- Existing AI failure details and retry limits remain stored on the board.

## Data and Migration

- Add `users.role` with non-null default `member`.
- Promote `auth_provider = kakao` and `user_id = 3891969863` to `system_admin` idempotently.
- Existing board-analysis data requires no migration.
- Remove the process-local `BoardAnalysisJobStore` after routes and tests use the persistent queue exclusively.

## Testing

- Crawler repository tests prove new crawls enter the pending queue and existing completed summaries are preserved on recrawl.
- Worker tests prove pending rows are summarized automatically.
- Repository and route tests cover member retry eligibility, retry reset, duplicate prevention, and completed-analysis conflict.
- Authorization tests prove only `system_admin` can regenerate completed analysis.
- User-service and gateway tests prove the role is stored, included in tokens, stripped from untrusted inbound headers, and forwarded from validated tokens.
- Frontend tests prove board opening does not request analysis and actions are rendered from analysis state and role.
- Existing tests prove likes and image OCR remain protected.
