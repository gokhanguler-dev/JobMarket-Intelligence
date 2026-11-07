"""Audit geography and vacancy identity for the public role-profile sample."""

import re
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from itertools import combinations
from urllib.parse import parse_qsl, urlsplit

from ingestion.parsers.job_text_parser import clean_html_text


# ISO country codes and unambiguous Turkish place names found in source feeds.
TURKIYE = re.compile(r"\b(?:turkiye|turkey|tr|tur)\b")
TURKISH_CITIES = re.compile(
    r"\b(?:istanbul|ankara|izmir|bursa|antalya|eskisehir|kocaeli|izmit|"
    r"tekirdag|sakarya|adana|mersin|konya|kayseri|gaziantep|samsun|trabzon|"
    r"denizli|balikesir|manisa|mugla|canakkale|edirne|aydin|diyarbakir|"
    r"erzurum|elazig|malatya|sanliurfa|kutahya|corum|afyonkarahisar)\b"
)
FOREIGN_LOCATION = re.compile(
    r"\b(?:qatar|doha|dubai|united arab emirates|uae|saudi arabia|riyadh|"
    r"germany|berlin|munich|netherlands|amsterdam|united kingdom|uk|london|"
    r"united states|usa|canada|france|paris|spain|madrid|italy|rome|"
    r"poland|warsaw|romania|bucharest|greece|athens|portugal|lisbon|"
    r"bulgaria|sofia|azerbaijan|baku|brazil|sao paulo|india|pakistan)\b"
)
REMOTE = re.compile(r"\b(?:remote|remotely|uzaktan|evden calismak|home based)\b")
HYBRID = re.compile(r"\b(?:hybrid|hibrit)\b")
ROLE_BASED_IN = re.compile(
    r"\b(?:(?:role|position|job) (?:is |will be )?(?:based|located)"
    r"|(?:candidates?|applicants?|you) (?:must |should |need to |are )?(?:be )?based"
    r"|(?:looking for|hiring)\b.{0,75}\b(?:based|located))"
    r"\s+(?:in|from|within)\s+(?:turkey|turkiye)\b"
)
ON_SITE = re.compile(r"\b(?:on site|onsite|yerinde)\b")
NO_REMOTE = re.compile(r"\b(?:not (?:a )?(?:fully )?remote|no remote|cannot work remotely|can not work remotely)\b")
RELOCATION = re.compile(
    r"\b(?:relocat(?:e|ing|ion)\s+to|on site (?:position|role) in)\s+(.+)"
)
REMOTE_FROM = re.compile(
    r"\b(?:work(?:ing)? remotely (?:from|in|within)|remote (?:work )?(?:from|within|in))\s+"
    r"(?:anywhere in )?(?:turkey|turkiye)\b"
)
REMOTE_WORLDWIDE = re.compile(r"\b(?:remote worldwide|work from anywhere in the world)\b")
ROLE_IS_REMOTE = re.compile(
    r"\b(?:(?:this|the) (?:position|role) is (?:fully |100 )?remote|"
    r"(?:fully |100 )remote (?:role|position))\b"
)
BREAK_TAGS = re.compile(r"</(?:p|li|div|h[1-6])\s*>|<br\b[^>]*>", re.IGNORECASE)
EXCERPT_BREAKS = re.compile(r"\.{2,}|…+")
TRACKING_PARAMS = {"fbclid", "gclid", "gh_src", "lever-source", "lever-origin"}
JOB_ID_PARAMS = {"jobid", "job_id", "gh_jid", "postingid", "requisitionid"}
ELIGIBLE_SCOPES = {"turkiye", "remote_from_turkiye"}
MARKET_SCOPES = (
    "turkiye", "remote_from_turkiye", "aggregator_location_only", "outside_turkiye", "unknown"
)


def normalize(value):
    value = unicodedata.normalize("NFKD", (value or "").casefold().replace("ı", "i"))
    value = "".join(character for character in value if not unicodedata.combining(character))
    return " ".join(re.findall(r"[a-z0-9]+", value))


def description_text(value):
    return clean_html_text(BREAK_TAGS.sub(" ", value or "")) or ""


def market_scope(location, work_model, title, description, source):
    location = normalize(location)
    work_model = normalize(work_model)
    title = normalize(title)
    description = normalize(description)
    relocation = RELOCATION.search(title) or RELOCATION.search(description)
    if relocation and FOREIGN_LOCATION.match(relocation[1]):
        return "outside_turkiye"

    city_match = TURKISH_CITIES.search(location)
    location_is_turkiye = bool(city_match or TURKIYE.search(location))
    text_is_turkiye = bool(
        ROLE_BASED_IN.search(description)
        or re.search(r"\bturkiye (?:de ikamet|merkezli)\b", description)
    )
    is_remote = bool(
        REMOTE.search(work_model)
        or REMOTE.search(location)
        or REMOTE.search(title)
        or ROLE_IS_REMOTE.search(description)
    )
    hybrid = bool(HYBRID.search(work_model) or HYBRID.search(location) or HYBRID.search(title))
    explicit_remote = bool(
        REMOTE_WORLDWIDE.search(description)
        or REMOTE_WORLDWIDE.search(location)
    )
    foreign_location = bool(FOREIGN_LOCATION.search(location)) and not location_is_turkiye
    on_site = bool(ON_SITE.search(work_model) or ON_SITE.search(location))
    if not (hybrid or on_site or NO_REMOTE.search(description)) and (
        REMOTE_FROM.search(description)
        or ((explicit_remote or (is_remote and location == "worldwide")) and not foreign_location)
        or (is_remote and (location_is_turkiye or text_is_turkiye))
    ):
        return "remote_from_turkiye"

    if city_match or text_is_turkiye or (location_is_turkiye and source != "Jooble"):
        return "turkiye"
    if location_is_turkiye:
        return "aggregator_location_only"
    if foreign_location:
        return "outside_turkiye"
    return "unknown"


def posting_url(value):
    """Keep posting identifiers and strip only known tracking parameters."""
    try:
        parts = urlsplit((value or "").strip())
        host = parts.hostname
    except ValueError:
        return None
    if parts.scheme not in {"http", "https"} or not host or parts.username or parts.password:
        return None

    host = host.removeprefix("www.")
    path = parts.path.rstrip("/")
    params = tuple(sorted(
        (key, item) for key, item in parse_qsl(parts.query, keep_blank_values=True)
        if key.casefold() not in TRACKING_PARAMS and not key.casefold().startswith("utm_")
    ))
    # Generic careers pages are shared by many vacancies.
    leaf = path.rsplit("/", 1)[-1]
    has_id = (
        re.search(r"\d{4,}", leaf)
        or re.fullmatch(r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}", leaf)
        or (host == "apply.workable.com" and re.fullmatch(r"/j/[0-9A-Za-z]{6,}", path))
        or any(key.casefold() in JOB_ID_PARAMS and item for key, item in params)
    )
    return (host, path, params) if has_id else None


@dataclass
class Posting:
    row: dict
    title: str
    text: str
    excerpts: frozenset
    cities: frozenset
    scope: str

    @classmethod
    def from_row(cls, row):
        text = description_text(row["Description"])
        location = row["JobLocation"]
        excerpts = frozenset(
            normalized for segment in EXCERPT_BREAKS.split(text)
            if len((normalized := normalize(segment))) >= 55 and len(normalized.split()) >= 9
        )
        return cls(
            row,
            normalize(row["JobTitle"]),
            normalize(text),
            excerpts,
            frozenset(TURKISH_CITIES.findall(normalize(location))),
            market_scope(location, row["WorkModel"], row["JobTitle"], text, row["SourceSystem"]),
        )

    @property
    def is_aggregator(self):
        return self.row["SourceSystem"] == "Jooble"

    def preference(self):
        return (
            not self.is_aggregator,
            self.scope in ELIGIBLE_SCOPES,
            self.row["LocalDay"],
            len(self.text),
            self.row["JobPostingKey"],
        )


def same_employer(left, right):
    left_key = left.row["CompanyKey"]
    right_key = right.row["CompanyKey"]
    return left_key is not None and left_key == right_key


def compatible(left, right):
    if left.cities and right.cities and left.cities.isdisjoint(right.cities):
        return False
    scopes = {left.scope, right.scope}
    return "outside_turkiye" not in scopes or not scopes.intersection(
        ELIGIBLE_SCOPES | {"aggregator_location_only"}
    )


def shared_excerpts(aggregator, direct):
    if not compatible(aggregator, direct):
        return 0
    if (
        aggregator.row["CompanyKey"] is not None
        and direct.row["CompanyKey"] is not None
        and not same_employer(aggregator, direct)
    ):
        return 0
    text = f" {direct.text} "
    return sum(f" {excerpt} " in text for excerpt in aggregator.excerpts)


def audit_role_postings(rows):
    """Return a conservative distinct sample and aggregate-only audit counts."""
    by_url = defaultdict(list)
    for row in rows:
        posting = Posting.from_row(row)
        url = posting_url(row["JobLink"])
        identity = (url, posting.title) if url and posting.title else row["JobPostingKey"]
        by_url[identity].append(posting)

    representatives = [max(postings, key=Posting.preference) for postings in by_url.values()]
    by_title = defaultdict(list)
    for posting in representatives:
        if posting.title:
            by_title[posting.title].append(posting)

    duplicate_excerpts = set()
    for postings in by_title.values():
        direct = [posting for posting in postings if not posting.is_aggregator]
        for posting in postings:
            if not posting.is_aggregator:
                continue
            matches = [candidate for candidate in direct if shared_excerpts(posting, candidate) >= 2]
            if len(matches) == 1 and (
                same_employer(posting, matches[0]) or len(posting.title.split()) >= 4
            ):
                duplicate_excerpts.add(posting.row["JobPostingKey"])

    retained = [
        posting for posting in representatives
        if posting.row["JobPostingKey"] not in duplicate_excerpts
    ]
    possible = set()
    for postings in by_title.values():
        for left, right in combinations(postings, 2):
            left_key, right_key = left.row["JobPostingKey"], right.row["JobPostingKey"]
            if {left_key, right_key}.intersection(duplicate_excerpts) or not compatible(left, right):
                continue
            aggregator, direct = (left, right) if left.is_aggregator else (right, left)
            if same_employer(left, right) or (
                aggregator.is_aggregator and not direct.is_aggregator
                and shared_excerpts(aggregator, direct)
            ):
                possible.update((left_key, right_key))

    locations = Counter(posting.scope for posting in retained)
    sources = Counter(row["SourceSystem"] for row in rows)
    return retained, {
        "source_records": len(rows),
        "source_mix": dict(sorted(sources.items(), key=lambda item: (-item[1], item[0]))),
        "distinct_postings": len(retained),
        "url_duplicates": len(rows) - len(representatives),
        "excerpt_duplicates": len(duplicate_excerpts),
        "possible_duplicate_records": len(possible),
        "locations": {scope: locations[scope] for scope in MARKET_SCOPES},
    }
