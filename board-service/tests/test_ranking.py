from datetime import datetime, timedelta, timezone

from app.services.ranking import RankingCandidate, balance_site_exposure


def _candidate(identity: str, site: str, score: float, minute: int = 0):
    return RankingCandidate(
        item=identity,
        identity=identity,
        site=site,
        score=score,
        created_at=datetime(2026, 8, 6, 12, minute, tzinfo=timezone.utc),
    )


def test_balanced_ranking_gives_every_active_site_one_initial_slot():
    candidates = [
        _candidate("dc-1", "dcinside", 100),
        _candidate("dc-2", "dcinside", 90),
        _candidate("dc-3", "dcinside", 80),
        _candidate("pp-1", "ppomppu", 20),
        _candidate("yg-1", "ygosu", 10),
    ]

    ranked = balance_site_exposure(candidates, limit=4)

    assert ranked[:3] == ["dc-1", "pp-1", "yg-1"]
    assert ranked[3] == "dc-2"


def test_balanced_ranking_penalizes_repeated_site_exposure_after_coverage():
    candidates = [
        _candidate("dc-1", "dcinside", 100),
        _candidate("dc-2", "dcinside", 90),
        _candidate("dc-3", "dcinside", 80),
        _candidate("pp-1", "ppomppu", 70),
        _candidate("pp-2", "ppomppu", 65),
    ]

    ranked = balance_site_exposure(candidates, limit=5)

    assert ranked == ["dc-1", "pp-1", "dc-2", "pp-2", "dc-3"]


def test_balanced_ranking_is_prefix_stable_for_pagination():
    candidates = [
        _candidate("dc-1", "dcinside", 100),
        _candidate("dc-2", "dcinside", 90),
        _candidate("dc-3", "dcinside", 80),
        _candidate("pp-1", "ppomppu", 20),
        _candidate("pp-2", "ppomppu", 10),
    ]

    first_page = balance_site_exposure(candidates, limit=2)
    two_page_prefix = balance_site_exposure(candidates, limit=4)

    assert two_page_prefix[:2] == first_page
    assert set(two_page_prefix[:2]).isdisjoint(two_page_prefix[2:])


def test_balanced_ranking_uses_recency_and_identity_as_deterministic_tiebreakers():
    created_at = datetime(2026, 8, 6, 12, tzinfo=timezone.utc)
    candidates = [
        RankingCandidate("older", "older", "dcinside", 10, created_at),
        RankingCandidate(
            "newer-b",
            "newer-b",
            "ppomppu",
            10,
            created_at + timedelta(minutes=1),
        ),
        RankingCandidate(
            "newer-a",
            "newer-a",
            "ygosu",
            10,
            created_at + timedelta(minutes=1),
        ),
    ]

    assert balance_site_exposure(candidates, limit=3) == [
        "newer-b",
        "newer-a",
        "older",
    ]


def test_balanced_ranking_deduplicates_identity():
    candidates = [
        _candidate("same", "dcinside", 10),
        _candidate("same", "dcinside", 10),
    ]

    assert balance_site_exposure(candidates, limit=2) == ["same"]


def test_balanced_ranking_does_not_reserve_coverage_for_inactive_site():
    candidates = [
        _candidate("dc-1", "dcinside", 100),
        _candidate("pp-1", "ppomppu", 10),
        RankingCandidate(
            item="legacy-1",
            identity="legacy-1",
            site="legacy",
            score=95,
            created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
            is_active=False,
        ),
    ]

    assert balance_site_exposure(candidates, limit=2) == ["dc-1", "pp-1"]
