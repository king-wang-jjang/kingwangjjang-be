# Popularity Ranking Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the first working popularity ranking foundation with metric snapshots, transparent score calculation, latest native metrics, and hot/daily sorting.

**Architecture:** `board-service` owns read-time ranking behavior and the score formula. `CrawlScheduler` writes latest native source metrics and snapshot rows when upserting crawled posts. Existing `comment_count` and `like_count` remain compatible, while source recommendation data moves into `native_like_count` to avoid mixing source likes with local user likes.

**Tech Stack:** FastAPI, SQLAlchemy, pytest, SQLite test databases, PostgreSQL-compatible schema compatibility helpers.

---

### Task 1: Board-Service Popularity Formula

**Files:**
- Create: `board-service/app/services/popularity.py`
- Test: `board-service/tests/test_popularity.py`

- [ ] **Step 1: Write failing formula tests**

Add tests for hot/daily score calculation, negative delta clamping, and age decay.

- [ ] **Step 2: Run formula tests**

Run: `python -m pytest tests/test_popularity.py`
Expected: FAIL because `app.services.popularity` does not exist.

- [ ] **Step 3: Implement formula service**

Create a focused score module that accepts metric values and returns hot score, daily score, and breakdown.

- [ ] **Step 4: Verify formula tests pass**

Run: `python -m pytest tests/test_popularity.py`
Expected: PASS.

### Task 2: Board-Service Snapshot Model And Ranking

**Files:**
- Modify: `board-service/app/db/models.py`
- Modify: `board-service/app/repositories/boards.py`
- Test: `board-service/tests/test_board_popularity_repository.py`
- Test: `board-service/tests/test_board_repository_filters.py`
- Test: `board-service/tests/test_rest_boards.py`

- [ ] **Step 1: Write failing repository tests**

Add tests for snapshot insertion, latest native metric updates, hot/daily score ordering, and response score fields.

- [ ] **Step 2: Run repository tests**

Run: `python -m pytest tests/test_popularity.py tests/test_board_popularity_repository.py tests/test_board_repository_filters.py tests/test_rest_boards.py`
Expected: FAIL because the snapshot model and ranking fields do not exist.

- [ ] **Step 3: Implement model and repository changes**

Add `BoardMetricSnapshot`, latest native metric columns, score columns, schema compatibility, score calculation, and hot/daily ordering.

- [ ] **Step 4: Verify board-service tests pass**

Run: `python -m pytest tests`
Expected: PASS.

### Task 3: CrawlScheduler Metric Upsert Support

**Files:**
- Create: `CrawlScheduler/crawl_scheduler/popularity.py`
- Modify: `CrawlScheduler/crawl_scheduler/db/models.py`
- Modify: `CrawlScheduler/crawl_scheduler/db/postgres_controller.py`
- Test: `CrawlScheduler/tests/test_popularity.py`
- Test: `CrawlScheduler/tests/test_postgres_controller.py`

- [ ] **Step 1: Write failing crawler tests**

Add tests that crawled `comment_count` and `like_count` populate native metrics, create metric snapshots, update scores, and use hot/daily score ordering.

- [ ] **Step 2: Run crawler tests**

Run: `python -m pytest tests/test_popularity.py tests/test_postgres_controller.py`
Expected: FAIL because native metrics and snapshot rows do not exist.

- [ ] **Step 3: Implement crawler model and upsert changes**

Mirror the score module and model fields, store snapshot rows during board upsert, update scores, and sort best lists by score.

- [ ] **Step 4: Verify crawler tests pass**

Run: `python -m pytest tests/test_popularity.py tests/test_postgres_controller.py`
Expected: PASS.

### Task 4: Final Verification And Git

**Files:**
- Review changed files in both repositories.

- [ ] **Step 1: Run backend verification**

Run in `kingwangjjang-be/board-service`: `python -m pytest tests`
Expected: PASS.

- [ ] **Step 2: Run crawler verification**

Run in `CrawlScheduler`: `python -m pytest tests/test_popularity.py tests/test_postgres_controller.py`
Expected: PASS.

- [ ] **Step 3: Commit and push**

Commit `kingwangjjang-be` and `CrawlScheduler` separately, then push each current branch.
