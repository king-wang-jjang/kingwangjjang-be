from collections.abc import Iterable
from dataclasses import dataclass

from app.utils.constants import (
    SITE_ARCA,
    SITE_DCINSIDE,
    SITE_FMKOREA,
    SITE_INVEN,
    SITE_PPOMPPU,
    SITE_THEQOO,
    SITE_YGOSU,
)


@dataclass(frozen=True)
class SiteFilter:
    value: str
    label: str


SITE_FILTERS = (
    SiteFilter(value=SITE_DCINSIDE, label="디시인사이드"),
    SiteFilter(value=SITE_YGOSU, label="와이고수"),
    SiteFilter(value=SITE_PPOMPPU, label="뽐뿌"),
    SiteFilter(value=SITE_THEQOO, label="더쿠"),
    SiteFilter(value=SITE_FMKOREA, label="에펨코리아"),
    SiteFilter(value=SITE_ARCA, label="아카라이브"),
    SiteFilter(value=SITE_INVEN, label="인벤"),
)
SITE_LABELS = {site_filter.value: site_filter.label for site_filter in SITE_FILTERS}


def get_board_filter_options(active_sites: Iterable[str]) -> dict:
    active_site_values = {
        cleaned_site
        for site in active_sites
        if (cleaned_site := str(site).strip())
    }
    ordered_site_values = [
        site_filter.value
        for site_filter in SITE_FILTERS
        if site_filter.value in active_site_values
    ]
    ordered_site_values.extend(sorted(active_site_values - SITE_LABELS.keys()))

    return {
        "sites": [
            {"value": site, "label": get_site_label(site)}
            for site in ordered_site_values
        ]
    }


def get_site_label(site: str) -> str:
    return SITE_LABELS.get(site, site)
