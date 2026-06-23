# 인기 순위 산정을 위한 사전작업

## 목표

인기 순위는 서로 다른 두 질문에 답할 수 있어야 한다.

- **지금 뜨는 글**: 짧은 시간 안에 관심이 빠르게 증가하는 게시글은 무엇인가?
- **오늘의 인기글**: 하루 동안 의미 있는 반응을 많이 모은 게시글은 무엇인가?

현재 `boards` 모델에는 이미 `comment_count`, `like_count`, `created_at`,
`thumbnail`이 있다. 다음 단계는 이 값을 주기적으로 다시 수집해 스냅샷으로
저장하고, 누적 반응과 최근 증가량을 함께 계산하는 것이다.

## 인기 산정에 쓸만한 지표

### 첫 버전에 강하게 추천하는 지표

- **원본 사이트 댓글 수**: 가장 강한 토론 신호다. 현재 총 댓글 수와 최근
  댓글 증가량을 같이 본다.
- **원본 사이트 추천 수**: 댓글보다 더 명확한 긍정 반응이다. 다만 사이트마다
  제공 여부와 의미가 다를 수 있다.
- **게시글 나이**: 오래된 글이 계속 순위를 독점하지 않도록 시간 감쇠를 둔다.
- **최근 증가 속도**: 10분 또는 20분 동안의 `댓글 증가량`, `추천 증가량`.
  `실시간 인기`에서는 이 값이 핵심이다.
- **가속도**: 직전 구간보다 현재 구간의 증가 속도가 더 빨라졌는지 본다.
  갑자기 터지는 글을 잡아낼 수 있다.
- **원본 사이트 내 순위**: 원본 목록이 이미 인기/베스트 순서를 제공한다면
  약한 보조 신호로 저장한다.
- **썸네일/미디어 유무**: 클릭 가능성을 높일 수 있지만 실제 인기도는 아니므로
  동점 처리나 약한 보정 정도로만 쓴다.

### 이후에 추가하면 좋은 지표

- **원본 사이트 조회수**: 사이트가 안정적으로 제공할 때만 추가한다. 조회수는
  사이트 규모 차이가 커서 반드시 보정이 필요하다.
- **내부 클릭/조회수**: 서비스 사용량이 충분히 쌓인 뒤 별도 지표로 다룬다.
- **댓글 품질**: 고유 댓글 작성자 수, 댓글 길이, 대댓글 깊이 등. 첫 버전에는
  복잡도 대비 효용이 낮다.
- **여러 사이트 확산 여부**: 같은 이슈가 여러 커뮤니티에 동시에 뜨면 글 하나가
  아니라 이슈 클러스터를 올리는 방식으로 확장할 수 있다.
- **부정/스팸 신호**: 삭제, 차단 키워드, 비정상적으로 큰 증가량, 다운보트 등.

## 스냅샷 수집 방식

사용자가 제안한 “10분 또는 20분마다 다시 크롤링해서 댓글 수와 추천 수를
가져온다”는 방향이 맞다. 다만 매번 본문 전체, OCR, AI 요약까지 다시 돌리지
말고 **메트릭 전용 refresh**로 분리하는 것이 좋다.

추천 주기:

- 발견 후 2시간 이내: 10분마다 refresh.
- 2시간 이후 12시간 이내: 20분마다 refresh.
- 12시간 이후 24시간 이내: 60분마다 refresh.
- 24시간 이후: 인기 후보에 남아 있지 않으면 refresh 중단.

추천 후보 정책:

- 생성 후 24시간 이내 게시글은 refresh 대상.
- 원본 사이트의 인기/베스트 목록에 보인 게시글은 refresh 대상.
- 마지막 스냅샷에서 의미 있는 증가량이 있던 게시글은 refresh 유지.
- 여러 번 연속으로 증가량이 없는 글은 refresh 간격을 늘리거나 중단.

이렇게 하면 크롤러 부하를 통제하면서도 상승 중인 글을 놓치지 않을 수 있다.

## 데이터 모델 제안

게시글 카드에 필요한 최신 값은 `boards`에 유지하고, 시간 흐름은 별도 스냅샷
테이블에 저장한다.

### `boards` 추가 후보

- `native_comment_count`: 원본 사이트의 최신 댓글 수.
- `native_like_count`: 원본 사이트의 최신 추천/좋아요 수.
- `native_view_count`: 지원하는 사이트에만 저장하는 nullable 조회수.
- `source_rank`: 원본 인기 목록에서의 순위.
- `metrics_crawled_at`: 마지막 메트릭 refresh 성공 시각.
- `next_metrics_crawl_at`: 다음 refresh 우선순위 계산용 시각.
- `hot_score`: 실시간 인기 점수.
- `daily_score`: 일간 인기 점수.
- `score_updated_at`: 점수 계산 시각.

기존 `comment_count`, `like_count`는 API 호환을 위해 유지하되, 내부적으로는
`native_*` 이름이 출처를 더 분명하게 만든다.

### `board_metric_snapshots`

- `id`
- `board_id`
- `captured_at`
- `comment_count`
- `like_count`
- `view_count`
- `source_rank`
- `crawl_status`
- `crawl_error`

`(board_id, captured_at)`에 unique index를 두거나, 10분 단위 bucket으로 저장한다.

### 선택 사항: `board_popularity_scores`

점수 설명 가능성이 중요하면 점수 구성요소를 별도로 저장한다.

- `board_id`
- `computed_at`
- `score_type`: `hot` 또는 `daily`
- `score`
- `total_component`
- `velocity_component`
- `freshness_component`
- `source_rank_component`
- `normalization_component`

첫 버전은 `boards`에 `hot_score`, `daily_score`, JSON 형태의 score breakdown을
저장하는 정도로 충분하다.

## 계산법 제안

처음부터 복잡한 추천 알고리즘으로 가지 말고, 설명 가능하고 튜닝 가능한 산식으로
시작하는 것이 좋다.

### 실시간 인기 점수

실시간 인기 점수는 최근 증가량을 더 강하게 반영한다.

```text
total_component =
  1.2 * log1p(comment_count) +
  1.8 * log1p(like_count) +
  0.2 * log1p(view_count)

velocity_component =
  2.4 * log1p(delta_comments_20m) +
  3.2 * log1p(delta_likes_20m) +
  0.3 * log1p(delta_views_20m)

acceleration_component =
  1.0 * max(current_velocity - previous_velocity, 0)

source_rank_component =
  source_rank가 있으면 1 / sqrt(source_rank), 없으면 0

hot_score =
  site_normalize(
    0.35 * total_component +
    0.55 * velocity_component +
    0.10 * source_rank_component +
    acceleration_component
  ) * age_decay
```

시간 감쇠 예시:

```text
age_decay = exp(-age_hours / 12)
```

새 글에도 기회를 주면서, 실제 반응이 강한 글은 너무 빨리 사라지지 않게 하는
균형점이다.

### 일간 인기 점수

일간 인기 점수는 누적 반응을 더 크게 보고, 최근 증가량을 보조로 반영한다.

```text
daily_score =
  site_normalize(
    0.65 * total_component +
    0.25 * velocity_component +
    0.10 * source_rank_component
  ) * exp(-age_hours / 36)
```

## 사이트별 보정

raw count만 쓰면 규모가 큰 커뮤니티 글이 항상 유리해진다. 점수 계산 뒤에는
사이트별 보정이 필요하다.

- 사이트와 게시글 나이 구간별 rolling average, standard deviation을 저장한다.
- 스냅샷이 충분히 쌓이면 percentile 또는 z-score 방식으로 보정한다.
- 데이터가 부족한 첫 며칠은 보수적인 `site_weight` 설정값으로 시작한다.

초기 fallback:

```text
normalized_score = raw_score * site_weight
```

스냅샷이 충분히 쌓인 뒤 rolling percentile 보정으로 바꾸면 된다.

## 내 의견

나는 **스냅샷 기반 랭킹**으로 시작하는 것을 추천한다.

1. 메트릭 스냅샷 저장과 메트릭 전용 재크롤링을 먼저 만든다.
2. `boards`에는 최신 원본 댓글 수, 추천 수, 조회수 후보를 저장한다.
3. 투명한 산식으로 `hot_score`, `daily_score`를 계산한다.
4. `/realtime`은 `hot_score`, `/daily`는 `daily_score` 기준으로 정렬한다.
5. 점수 breakdown을 로그나 JSON으로 남겨 “왜 이 글이 위에 있는지” 설명 가능하게
   만든다.

처음부터 머신러닝이나 복잡한 추천 시스템으로 갈 필요는 없다. 지금 필요한 것은
관측 가능하고 디버깅 가능한 랭킹이다. 스냅샷과 점수 구성요소가 보이면 이후
가중치 튜닝은 훨씬 쉬워진다.

## 구현 메모

- 메트릭 refresh에서는 OCR이나 AI 요약을 다시 돌리지 않는다.
- 사이트별 adapter에서 댓글 수, 추천 수, 조회수, 원본 순위를 파싱한다.
- 크롤러 실패는 게시글 탈락 사유가 아니라 stale metric으로 처리한다.
- count가 감소하면 기본적으로 delta를 0으로 clamp한다.
- 직전 스냅샷은 delta 계산에 쓰고, 전체 스냅샷은 분석용으로 보존한다.
- 테스트는 다음을 포함한다.
  - 스냅샷 삽입
  - delta 계산
  - 시간 감쇠
  - 사이트 보정 fallback
  - 실시간/일간 랭킹 정렬 순서

## 남은 결정사항

- 기존 `comment_count`, `like_count`를 public alias로 유지할지, API 필드명을
  명확히 바꿀지 결정해야 한다.
- 각 사이트가 추천 수, 조회수, 원본 순위를 얼마나 안정적으로 제공하는지 확인해야
  한다.
- metric refresh는 `CrawlScheduler`가 전담하고, 점수 계산은 `board-service`가
  담당할지 경계를 정해야 한다.

