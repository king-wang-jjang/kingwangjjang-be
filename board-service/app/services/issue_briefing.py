"""Build an extractive public-interest briefing from stored board analyses.

Broad categories never identify an event. Matching requires concrete title
terms or a shared multi-word event tag, so e.g. two unrelated political stories
do not become one issue just because both are tagged '정치'. No model calls or
board-body reads are needed on the public request path.
"""

import re
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime


SOCIAL_TAGS = frozenset({
    "사회", "정치", "경제", "시사", "정책", "노동", "인권", "복지", "교육",
    "환경", "외교", "국제", "의료", "주거", "부동산", "교통", "안전", "범죄",
    "재난", "금융", "증시", "선거", "법률", "소비자", "사회이슈", "사회문제",
    "society", "politics", "economy", "news",
})
GENERIC_TERMS = SOCIAL_TAGS | frozenset({
    "게임", "게이밍", "유머", "이슈", "일상", "생활", "잡담", "연예", "스포츠",
    "논란", "사건", "화제", "뉴스", "속보", "정보", "커뮤니티", "한국", "대한민국",
    "오늘", "최근", "발표", "관련", "대한", "이번", "현재", "있다", "합니다",
    "했다", "하는", "되는", "때문", "새로운", "사진", "영상", "후기", "정리",
    "정부", "국회", "대통령", "의원", "장관", "법안", "일정", "공개", "논의",
    "지원", "대책", "대응", "발언", "교섭", "예고", "파업", "사고", "피해",
    "유출", "수사", "재판", "소송", "인상", "인하", "추진", "검토", "회의",
    "jpg", "jpeg", "png", "gif", "mp4", "game", "gaming", "issue", "humor",
})
PUBLIC_EVENT = re.compile(
    r"대통령|국회|국정감사|국무|장관|정부|선거|투표|탄핵|정당|의원|정책|법안|"
    r"대법원|헌법|검찰|경찰|수사|체포|구속|기소|판결|재판|소송|범죄|사기|피해자|"
    r"노동조합|노동청|노동법|파업|임금|해고|산재|과로|채용|실업|최저임금|"
    r"물가|금리|환율|관세|세금|증세|부동산|집값|전세|대출|연금|공정위|"
    r"개인정보.{0,5}유출|소비자.{0,5}피해|리콜|불매|횡령|뇌물|부패|"
    r"재난|지진|산불|홍수|침수|폭염|한파|붕괴|추락|참사|사망|사고|화재|"
    r"의료|병원|의사|감염|전염|보건|학교|교육부|등록금|급식|학폭|"
    r"성폭력|성범죄|혐오|차별|인권|기후|오염|환경부|외교|전쟁|휴전|난민|"
    r"지하철|버스|철도|교통|공공요금|정전|단수|복지|저출생"
)
ENTERTAINMENT = re.compile(
    r"게임|게이밍|플레이스테이션|닌텐도|스팀|롤드컵|e스포츠|아이돌|예능|"
    r"연예|드라마|웹툰|애니메이션|스포츠|game|gaming", re.IGNORECASE
)
# Game titles use words such as '전쟁', '사기', '사고' figuratively. Require
# explicit real-world civic signals before overriding the entertainment filter.
ENTERTAINMENT_PUBLIC_EVENT = re.compile(
    r"국정감사|공정위|공정거래|소비자원|노동조합|노동청|노동법|근로기준법|"
    r"파업|임금체불|최저임금|산업재해|산재|과로|집단해고|대규모.{0,3}해고|"
    r"소송|고소|고발|판결|기소|압수수색|규제|법안|법.{0,3}위반|"
    r"개인정보.{0,5}유출|소비자.{0,5}피해|사기.{0,5}(?:피해|혐의)|"
    r"성폭력|성범죄|학폭|횡령|뇌물|탈세|주가|상장|공시|인수합병"
)
# Korean particles on title words should not split the same event.
PARTICLES = re.compile(r"(?:에서는|으로는|에서도|에게서|에서|으로|에게|까지|부터|은|는|이|가|을|를|의|와|과|도)$")


def _normalize(value: str) -> str:
    return unicodedata.normalize("NFKC", value).strip().lstrip("#").strip().casefold()


def _terms(value: str) -> frozenset[str]:
    terms = set()
    for word in re.findall(r"[가-힣a-z0-9]+", _normalize(value)):
        stripped = PARTICLES.sub("", word)
        term = stripped if len(stripped) >= 2 else word
        if len(term) >= 2 and term not in GENERIC_TERMS and not term.isdigit():
            terms.add(term)
    return frozenset(terms)


@dataclass(frozen=True)
class BriefingPost:
    id: str
    site: str
    title: str
    url: str
    summary: str
    tags: tuple[str, ...]
    created_at: datetime


def _is_social(post: BriefingPost) -> bool:
    tags = {_normalize(tag) for tag in post.tags}
    headline = " ".join((post.title, *tags))
    # A game's reviews/updates do not qualify through an incidental category.
    # Public-interest stories about game companies (e.g. a strike) do qualify.
    if ENTERTAINMENT.search(headline):
        return bool(ENTERTAINMENT_PUBLIC_EVENT.search(headline))
    return bool(tags & SOCIAL_TAGS or PUBLIC_EVENT.search(headline))


def _event_tags(post: BriefingPost) -> frozenset[str]:
    return frozenset(
        normalized for tag in post.tags
        if (normalized := _normalize(tag)) not in GENERIC_TERMS
        and len(_terms(normalized)) >= 2
    )


def _summary(posts: list[BriefingPost]) -> str:
    """Extract up to three distinct sentences; do not invent an event narrative."""
    sentences = []
    seen = set()
    for post in posts:
        for sentence in re.split(r"(?<=[.!?。])\s+|\n+", post.summary.strip()):
            sentence = re.sub(r"\s+", " ", sentence).strip()
            key = _normalize(sentence)
            if not sentence or key in seen:
                continue
            if sentences and sum(map(len, sentences)) + len(sentence) > 480:
                continue
            sentences.append(sentence[:480])
            seen.add(key)
            if len(sentences) == 3:
                return " ".join(sentences)
    return " ".join(sentences)


def build_issue_briefing(posts: list[BriefingPost], *, limit: int = 5) -> dict:
    # A re-crawl of the same source URL contributes one mention, not two.
    unique = {}
    for post in sorted(posts, key=lambda item: (-item.created_at.timestamp(), item.id)):
        if post.summary.strip() and _is_social(post):
            unique.setdefault((post.site, post.url.strip() or post.id), post)
    candidates = sorted(unique.values(), key=lambda item: (
        -bool(_event_tags(item)), len(item.title), _normalize(item.title), item.id,
    ))
    groups: list[list[BriefingPost]] = []
    title_terms = [_terms(post.title) for post in candidates]
    event_tags = [_event_tags(post) for post in candidates]
    # Use an inverted index to avoid comparing every pair of today's posts.
    term_groups: dict[str, set[int]] = defaultdict(set)
    event_groups: dict[str, set[int]] = defaultdict(set)
    title_groups: dict[str, int] = {}
    representatives: list[int] = []
    for index, post in enumerate(candidates):
        terms = title_terms[index]
        title_key = _normalize(post.title)
        possible = set()
        if title_key in title_groups:
            possible.add(title_groups[title_key])
        for term in terms:
            possible.update(term_groups[term])
        for tag in event_tags[index]:
            possible.update(event_groups[tag])
        best_group = None
        best_score = 0.0
        for group_index in sorted(possible):
            representative = representatives[group_index]
            shared = terms & title_terms[representative]
            union = terms | title_terms[representative]
            similarity = len(shared) / len(union) if union else 0.0
            same_event_tag = bool(event_tags[index] & event_tags[representative])
            same_title = title_groups.get(title_key) == group_index
            # Match against the group's representative, avoiding transitive
            # chains that would blend unrelated events sharing one entity.
            matches = same_title or same_event_tag or (len(shared) >= 2 and similarity >= 0.45)
            score = 1.0 if same_title else 0.9 if same_event_tag else similarity
            if matches and score > best_score:
                best_group, best_score = group_index, score
        if best_group is not None:
            groups[best_group].append(post)
            title_groups.setdefault(title_key, best_group)
            continue
        group_index = len(groups)
        groups.append([post])
        representatives.append(index)
        title_groups[title_key] = group_index
        for term in terms:
            term_groups[term].add(group_index)
        for tag in event_tags[index]:
            event_groups[tag].add(group_index)

    groups.sort(key=lambda group: (
        -len(group), -len({post.site for post in group}),
        -max(post.created_at.timestamp() for post in group), _normalize(group[0].title),
    ))
    issues = []
    for rank, group in enumerate(groups[:limit], start=1):
        # Use the shortest actual headline and its stored summary first.
        ordered = sorted(group, key=lambda post: (len(post.title), post.title, post.id))
        representative = ordered[0]
        sources = Counter(post.site for post in group)
        examples = []
        used_sites = set()
        for post in ordered:
            if post.site in used_sites:
                continue
            examples.append({"board_id": post.id, "site": post.site, "title": post.title, "url": post.url})
            used_sites.add(post.site)
            if len(examples) == 3:
                break
        issues.append({
            "id": representative.id,
            "rank": rank,
            "title": representative.title,
            "summary": _summary(ordered),
            "post_count": len(group),
            "source_count": len(sources),
            "sources": [
                {"site": site, "post_count": count}
                for site, count in sorted(sources.items(), key=lambda item: (-item[1], item[0]))
            ],
            "posts": examples,
        })
    return {
        "total_posts": len(candidates),
        "total_issues": len(groups),
        "source_count": len({post.site for post in candidates}),
        "issues": issues,
    }
