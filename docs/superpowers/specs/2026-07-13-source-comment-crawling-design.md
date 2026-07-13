# Source Comment Crawling Design

## Goal

Collect comments from the original community posts without mixing them with comments written by Kingwangjjang users. Refresh source comments for the first 24 hours of a post's life, expose them through a read-only API, and show them in a separate frontend area.

The first release supports Dcinside, Ppomppu, Theqoo, and Ygosu.

## Current-State Findings

- The crawler runs the realtime-best crawl every five minutes.
- Site crawlers skip a post as soon as it already exists, so its contents and native metrics are not refreshed through that path.
- `boards` contains native comment counts and metric scheduling fields, but no source-comment body storage or active comment refresh scheduler.
- `comments` belongs to the product's user-comment feature. Source comments must not share this table because ownership, mutation rules, identity, and deletion semantics differ.
- Request timeouts and failure handling are inconsistent across site crawlers. A comment job must isolate failures by post and site.
- The local Docker engine was not running during design discovery. Both configured PostgreSQL endpoints were therefore unreachable. Production-like database inspection is a required implementation gate, not an assumed result.

## Architecture

Keep post discovery and source-comment refresh as separate jobs inside `CrawlScheduler`.

The existing post job continues to discover popular posts every five minutes. When a new board is stored, it becomes eligible for immediate source-comment crawling. A separate dispatcher wakes every minute, claims a limited batch of due boards, invokes the matching site adapter, persists a complete comment snapshot, and calculates the next due time.

Separating the jobs prevents slow comment pages, pagination, rate limiting, or one broken site parser from delaying post discovery. The first release remains in the existing crawler deployment rather than introducing a new service.

## Eligibility and Schedule

A board is eligible when all of the following are true:

- Its source creation time is less than 24 hours old.
- `next_comment_crawl_at` is due.
- It is not already claimed by another worker.
- Its source site has a supported comment adapter.

Refresh timing is based on the source post creation time:

- Up to one hour old: schedule the next refresh five minutes later.
- More than one hour and up to 24 hours old: schedule the next refresh 30 minutes later.
- More than 24 hours old: mark comment crawling complete and stop scheduling it.

The scheduler should tolerate delayed runs. It calculates the next time from the time a crawl finishes while still selecting the interval from post age. It does not enqueue every missed historical interval.

## Data Model

Create a dedicated `source_comments` table. The final migration may adjust types or index details after inspecting the actual PostgreSQL schema and query plans.

Proposed columns:

- `id`: internal UUID primary key.
- `board_id`: foreign key to `boards.id`, indexed.
- `site`: normalized source site name.
- `source_comment_id`: opaque string identifier supplied or deterministically derived by the site adapter.
- `source_parent_id`: nullable opaque source ID for reply relationships.
- `author_name`: nullable source display name.
- `content`: nullable comment body; cleared when deletion is confirmed.
- `like_count`: non-negative source reaction count, default zero.
- `is_deleted`: deletion tombstone, default false.
- `source_created_at`: nullable timestamp reported by the source.
- `source_updated_at`: nullable timestamp reported by the source.
- `first_crawled_at`: first observation time.
- `last_crawled_at`: latest observation time.

Add a unique constraint on `(board_id, source_comment_id)`. Use string source identifiers because sites may use values larger than integers or composite tokens. Keep the original parent identifier even if a parent has not yet been observed.

Add comment-crawl state to `boards`:

- `comments_crawled_at`
- `next_comment_crawl_at`
- `comment_crawl_status`
- `comment_crawl_retry_count`
- `comment_crawl_error`

Status values are `pending`, `running`, `retry`, `completed`, and `unsupported`. The migration must be explicit, repeatable, and reviewable; runtime `create_all()` or ad hoc compatibility alters are not sufficient for this feature.

## Site Adapter Contract

Each supported site implements one adapter that accepts the stored board URL and source identity and returns a `SourceCommentSnapshot`:

- normalized comments;
- whether the snapshot is complete;
- pagination diagnostics such as pages fetched;
- source post availability state;
- observation timestamp.

Each normalized comment includes source ID, optional parent ID, author display name, content, reaction count, source timestamps, and deletion status when explicitly provided by the site.

Adapters must fetch every required comment page before declaring a snapshot complete. A partial page, parse error, timeout, unexpected markup, or pagination limit produces an incomplete snapshot.

## Synchronization Rules

For every observed comment, upsert by `(board_id, source_comment_id)`, update mutable source fields, clear a previous tombstone if the comment reappears, and set `last_crawled_at`.

Only a complete snapshot may infer deletion by absence. After a complete snapshot is persisted, comments previously associated with the board but absent from the snapshot are tombstoned by setting `is_deleted=true`, clearing `content`, and updating `last_crawled_at`.

Incomplete snapshots may add or update observed comments but must never tombstone unseen comments. A missing or access-restricted source post also must not imply that every comment was deleted.

## Concurrency

Claim due boards in a short database transaction using PostgreSQL row locking with skip-locked behavior. Set each claimed board to `running`, commit the claim, then perform network requests outside the transaction. This prevents duplicate work without holding database locks during remote calls.

Persistence of one complete snapshot is transactional per board. A failed write rolls back that board's comment changes and records a retry state separately.

## Failure and Rate-Limit Handling

- Apply explicit connect and response timeouts to every request.
- Retry timeouts, HTTP 429, and transient 5xx responses with bounded exponential backoff and jitter.
- Respect `Retry-After` when supplied.
- Treat authentication walls, deleted posts, and unsupported markup as distinct outcomes.
- Preserve existing comments on every fetch or parse failure.
- Increase retry delay after consecutive failures while the post remains inside the 24-hour window.
- Stop one failing post or site from stopping other jobs.
- Record structured diagnostics without storing credentials or full sensitive HTML.

Site-level request concurrency and minimum delay must be configurable so production tuning does not require code changes.

## API

Expose a read-only board API:

```http
GET /api/boards/{board_id}/source-comments
```

The response contains the source comment list, source parent relationships, deletion state, and the board's last successful source-comment refresh time. Pagination should be deterministic, ordered by source creation time and internal ID as a tie-breaker.

Source comments do not expose create, update, delete, or like endpoints. Existing internal user-comment endpoints and data remain unchanged.

## Frontend

Display source comments in a separate area labeled `원문 댓글`, distinct from the existing Kingwangjjang user comments. The source area is read-only and shows its last refresh time. Deleted source comments render as a deletion placeholder, while replies retain their relationship where possible.

The UI must not present internal comment mutation controls for source comments. Failure to load source comments must not prevent the board or internal comments from rendering.

## Database Inspection Gate

Before writing the migration, connect to the production-like PostgreSQL database in read-only mode and record:

- row counts and table sizes for `boards`, `comments`, and `board_metric_snapshots`;
- existing columns, constraints, foreign keys, and indexes;
- site distribution and post-age distribution for recent boards;
- null rates and duplicates for board source identity;
- orphaned internal comments;
- representative query plans for selecting due boards and listing comments;
- estimated growth from the observed comment counts.

If the actual database differs from the checked-in models, update the migration and this design's physical index details before implementation. Do not modify production data during inspection.

## Testing and Rollout

Automated coverage includes:

- saved HTML fixtures for all four site adapters;
- pagination and complete-versus-incomplete snapshot detection;
- comment and reply insertion, update, reappearance, and tombstoning;
- proof that incomplete snapshots never tombstone unseen comments;
- five-minute, 30-minute, and 24-hour scheduling boundaries;
- concurrent claim behavior;
- retry, rate-limit, timeout, and parser-failure behavior;
- separation between internal and source-comment APIs;
- frontend read-only rendering and failure isolation.

Roll out with a dry-run mode that fetches and reports normalized counts without writing comments. Then enable writes for a small controlled board batch, compare source pages with stored rows, and expand site by site while retaining all four sites in first-release scope. Track crawl duration, success rate, retry count, comments observed, and incomplete snapshots.

## Out of Scope

- Crawling comments after a post is 24 hours old.
- Mixing source comments with Kingwangjjang user comments.
- Mutating or reacting to source comments from Kingwangjjang.
- Realtime push updates.
- A separate comment-crawler deployment in the first release.
