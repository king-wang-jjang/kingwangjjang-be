from datetime import datetime, timedelta, timezone

from app.services.popularity import PopularityMetrics, calculate_popularity_scores


def test_hot_score_prioritizes_recent_metric_growth():
    captured_at = datetime(2026, 6, 23, 10, 20, tzinfo=timezone.utc)
    created_at = captured_at - timedelta(hours=1)

    quiet = calculate_popularity_scores(
        PopularityMetrics(
            site="dcinside",
            created_at=created_at,
            captured_at=captured_at,
            comment_count=100,
            like_count=50,
            previous_comment_count=100,
            previous_like_count=50,
        )
    )
    rising = calculate_popularity_scores(
        PopularityMetrics(
            site="dcinside",
            created_at=created_at,
            captured_at=captured_at,
            comment_count=35,
            like_count=25,
            previous_comment_count=5,
            previous_like_count=3,
        )
    )

    assert rising.hot_score > quiet.hot_score
    assert rising.daily_score > 0
    assert rising.breakdown["delta_comments_20m"] == 30
    assert rising.breakdown["delta_likes_20m"] == 22


def test_popularity_score_clamps_negative_deltas():
    captured_at = datetime(2026, 6, 23, 10, 20, tzinfo=timezone.utc)

    scores = calculate_popularity_scores(
        PopularityMetrics(
            site="ygosu",
            created_at=captured_at - timedelta(hours=1),
            captured_at=captured_at,
            comment_count=8,
            like_count=3,
            previous_comment_count=10,
            previous_like_count=5,
        )
    )

    assert scores.breakdown["delta_comments_20m"] == 0
    assert scores.breakdown["delta_likes_20m"] == 0


def test_hot_score_decays_with_age():
    captured_at = datetime(2026, 6, 23, 10, 20, tzinfo=timezone.utc)

    fresh = calculate_popularity_scores(
        PopularityMetrics(
            site="ppomppu",
            created_at=captured_at - timedelta(hours=1),
            captured_at=captured_at,
            comment_count=20,
            like_count=10,
            previous_comment_count=1,
            previous_like_count=1,
        )
    )
    old = calculate_popularity_scores(
        PopularityMetrics(
            site="ppomppu",
            created_at=captured_at - timedelta(hours=20),
            captured_at=captured_at,
            comment_count=20,
            like_count=10,
            previous_comment_count=1,
            previous_like_count=1,
        )
    )

    assert fresh.hot_score > old.hot_score
