# Anonymous Board Summary Design

## Goal

Allow signed-out visitors to request and poll the existing fixed AI summary for a public board post while keeping user-specific and open-ended AI operations authenticated.

## Scope

- Make `POST /api/boards/{board_id}/ai` available to anonymous and authenticated callers.
- Make `GET /api/boards/ai/jobs/{job_id}` available to anonymous and authenticated callers so both groups can poll the job they receive.
- Remove the frontend authentication guard that prevents summary requests for signed-out visitors.
- Keep likes, image OCR, authentication, and all user-specific operations unchanged.
- Keep historical-day behavior unchanged: automatic analysis is requested only for today's board list.

## Request Flow

1. The API gateway removes any caller-supplied client identity header and injects a trusted `X-Client-IP` value derived from the connection address.
2. The board service accepts a summary request only for an existing board ID. The prompt remains server-controlled; callers cannot submit arbitrary prompt text.
3. Existing completed summaries are returned without running inference again.
4. Existing queued or running jobs are reused by `BoardAnalysisJobStore`, so concurrent requests for the same board create only one inference task.
5. The frontend polls the returned job ID and updates its query cache when the summary completes, regardless of login state.

## Anonymous Rate Limit

- Apply a fixed-window in-memory limit of 10 summary POST requests per client IP per 60 seconds.
- Apply the limit only to unauthenticated callers. Authenticated behavior remains unchanged.
- Do not apply this limit to job polling because a single analysis currently polls repeatedly until completion.
- Return HTTP 429 with a stable `Anonymous analysis rate limit exceeded` detail when the limit is exceeded.
- The limiter is intentionally process-local because the current deployment uses one board-service instance. A shared store is required before horizontally scaling this service.

## Security Boundaries

- The gateway owns the trusted client-IP header and overwrites spoofed input.
- Anonymous access is restricted to the existing board ID and fixed server-side analysis pipeline.
- Arbitrary prompts and image OCR remain authenticated.
- Likes and other user-owned mutations remain authenticated.
- Job IDs remain UUIDs and expose only summary-job status and results.

## Error Handling

- Unknown board IDs continue to return 404.
- Rate-limited anonymous requests return 429.
- AI failures and job progress retain the existing response format.
- Authentication failures remain unchanged on protected endpoints.

## Testing

- Backend route tests prove anonymous summary creation and polling succeed.
- Backend route tests prove anonymous rate limiting returns 429 while authenticated requests are unaffected.
- Gateway tests prove caller-supplied `X-Client-IP` is overwritten.
- Existing authentication-boundary tests prove likes and image OCR remain protected.
- Frontend/static integration tests prove summary requests no longer depend on `isAuthenticated`.
- Run focused board-service, gateway/root integration, and frontend checks before completion.
