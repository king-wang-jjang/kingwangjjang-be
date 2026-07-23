from dataclasses import dataclass

from app.utils.constants import (
    SITE_DCINSIDE,
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
)
SITE_LABELS = {site_filter.value: site_filter.label for site_filter in SITE_FILTERS}


def get_board_filter_options() -> dict:
    return {
        "sites": [
            {"value": site_filter.value, "label": site_filter.label}
            for site_filter in SITE_FILTERS
        ]
    }


def get_site_label(site: str) -> str:
    return SITE_LABELS.get(site, site)
