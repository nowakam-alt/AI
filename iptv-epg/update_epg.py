import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any


SERIES_HINTS = (
    "serial",
    "series",
    "episode",
    "odc.",
    "sezon",
    "season",
    "s01",
    "e01",
)

MOVIE_CATEGORY_HINTS = (
    "film",
    "movie",
    "kino",
    "dramat",
    "komedia",
    "komediodramat",
    "thriller",
    "horror",
    "western",
    "melodramat",
    "musical",
    "kryminał",
    "kryminalny",
    "sensacyjny",
    "fantasy",
    "science fiction",
    "sci fi",
    "familijny",
    "przygodowy",
    "animowany",
    "biograficzny",
    "kostiumowy",
)

MOVIE_CATEGORY_ALIASES = {
    "dram",
    "kom",
    "thril",
    "hor",
    "sf",
    "scifi",
}

NON_MOVIE_CATEGORY_HINTS = (
    "serial",
    "series",
    "magazyn",
    "program",
    "sport",
    "piłka nożna",
    "pilka nozna",
    "informacyjne",
    "publicystyczny",
    "reality show",
)

CAST_LIMIT = 5
TMDB_WORKERS = 4


def load_config() -> dict[str, Any]:
    config_path = Path(os.environ.get("EPG_CONFIG_PATH", "epg_config.json"))
    if not config_path.exists():
        raise FileNotFoundError(f"Missing config file: {config_path}")
    return json.loads(config_path.read_text(encoding="utf-8"))


def normalize_title(title: str) -> str:
    title = title.lower().strip()
    title = re.sub(r"\([^)]*\)", "", title)
    title = re.sub(r"\[[^\]]*\]", "", title)
    title = re.sub(r"[^a-z0-9ąćęłńóśźż ]+", " ", title)
    title = re.sub(r"\s+", " ", title)
    return title.strip()


def build_search_titles(title: str) -> list[str]:
    candidates: list[str] = []

    def add(value: str) -> None:
        value = value.strip()
        if len(value) < 2:
            return
        if value not in candidates:
            candidates.append(value)

    cleaned = re.sub(r"\([^)]*\)", "", title)
    cleaned = re.sub(r"\[[^\]]*\]", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    add(title)
    add(cleaned)

    for separator in (":", " - ", " | ", " / ", ",", ". "):
        if separator in cleaned:
            left, right = cleaned.split(separator, 1)
            add(left.strip())
            add(right.strip())

    # Documentary titles often contain a subtitle or a person's name.
    words = re.findall(r"[A-ZĄĆĘŁŃÓŚŹŻ][\w'’-]*", title)
    current_span: list[str] = []
    for word in words:
        if len(word) <= 1:
            continue
        current_span.append(word)
        if len(current_span) >= 2:
            add(" ".join(current_span[-3:]))

    title_tokens = re.findall(r"[A-Za-zĄĆĘŁŃÓŚŹŻąćęłńóśźż0-9'’-]+", cleaned)
    if len(title_tokens) >= 2:
        add(" ".join(title_tokens[-2:]))
    if len(title_tokens) >= 3:
        add(" ".join(title_tokens[-3:]))

    return candidates


def looks_like_series(title: str, categories: list[str], programme: ET.Element) -> bool:
    category_text = " ".join(categories).lower()
    title_text = title.lower()
    if any(hint in title_text for hint in SERIES_HINTS):
        return True
    if "serial" in category_text or "series" in category_text:
        return True
    if programme.find("episode-num") is not None:
        return True
    return False


def looks_like_movie(categories: list[str]) -> bool:
    normalized = [normalize_title(item) for item in categories if item]
    for item in normalized:
        if any(hint in item for hint in NON_MOVIE_CATEGORY_HINTS):
            continue
        if item in MOVIE_CATEGORY_ALIASES or any(hint in item for hint in MOVIE_CATEGORY_HINTS):
            return True
    return False


def fetch_xml(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=120) as response:
        return response.read()


def load_cache(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_cache(path: Path, cache: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def fetch_json(url: str) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "Personal-IPTV-EPG-Enricher/1.0"},
    )
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code != 429 and exc.code < 500:
                raise
            if attempt == 2:
                raise
            retry_after = exc.headers.get("Retry-After")
            delay = float(retry_after) if retry_after else float(attempt + 1)
            time.sleep(max(delay, 1.0))
    return {}


def normalized_rating(value: Any) -> float | None:
    try:
        rating = float(value)
    except (TypeError, ValueError):
        return None
    if rating <= 0:
        return None
    return round(rating, 1)


def tmdb_movie_details(
    api_key: str,
    movie_id: int,
    language: str,
    fallback_release_date: str,
    fallback_rating: float | None,
    fallback_vote_count: int,
) -> dict[str, Any]:
    params = urllib.parse.urlencode({
        "api_key": api_key,
        "language": language,
        "append_to_response": "credits",
    })
    url = f"https://api.themoviedb.org/3/movie/{movie_id}?{params}"
    payload = fetch_json(url)

    release_date = payload.get("release_date") or fallback_release_date
    return {
        "year": release_date[:4] if release_date else "",
        "genres": [
            item["name"].strip()
            for item in payload.get("genres", [])
            if item.get("name")
        ],
        "cast": [
            item["name"].strip()
            for item in payload.get("credits", {}).get("cast", [])[:CAST_LIMIT]
            if item.get("name")
        ],
        "rating": normalized_rating(payload.get("vote_average")) or fallback_rating,
        "vote_count": int(payload.get("vote_count") or fallback_vote_count or 0),
        "tmdb_id": movie_id,
        "tmdb_checked": True,
    }


def tmdb_search_once(
    api_key: str,
    title: str,
    language: str,
    expected_year: str,
    include_details: bool,
) -> dict[str, Any] | None:
    params = urllib.parse.urlencode({
        "api_key": api_key,
        "query": title,
        "language": language,
        "include_adult": "false",
    })
    url = f"https://api.themoviedb.org/3/search/movie?{params}"
    payload = fetch_json(url)
    results = payload.get("results", [])
    normalized_title = normalize_title(title)
    selected = None

    for item in results:
        candidate_titles = {
            normalize_title(item.get("title") or ""),
            normalize_title(item.get("original_title") or ""),
        }
        if normalized_title in candidate_titles:
            selected = item
            break

    if selected is None and expected_year:
        for item in results:
            if (item.get("release_date") or "").startswith(expected_year):
                selected = item
                break

    if selected is None and results:
        selected = results[0]
    if selected is None or not selected.get("id"):
        return None

    rating = normalized_rating(selected.get("vote_average"))
    vote_count = int(selected.get("vote_count") or 0)
    if not include_details:
        release_date = selected.get("release_date") or ""
        return {
            "year": release_date[:4] if release_date else "",
            "genres": [],
            "cast": [],
            "rating": rating,
            "vote_count": vote_count,
            "tmdb_id": selected["id"],
            "tmdb_checked": True,
        }

    return tmdb_movie_details(
        api_key,
        selected["id"],
        language,
        selected.get("release_date") or "",
        rating,
        vote_count,
    )


def tmdb_search(
    api_key: str,
    title: str,
    language: str,
    expected_year: str = "",
    include_details: bool = True,
) -> dict[str, Any] | None:
    search_titles = build_search_titles(title)
    languages = [language]
    if language != "en-US":
        languages.append("en-US")

    for candidate_title in search_titles:
        for candidate_language in languages:
            metadata = tmdb_search_once(
                api_key,
                candidate_title,
                candidate_language,
                expected_year,
                include_details,
            )
            if metadata:
                return metadata
    return None


def unique_values(values: list[str], limit: int | None = None) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        value = value.strip()
        normalized = normalize_title(value)
        if not value or not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(value)
        if limit is not None and len(result) >= limit:
            break
    return result


def source_genres(categories: list[str]) -> list[str]:
    genres: list[str] = []
    alias_names = {
        "dram": "dramat",
        "kom": "komedia",
        "thril": "thriller",
        "hor": "horror",
        "sf": "SF",
        "scifi": "science fiction",
    }

    for category in categories:
        normalized = normalize_title(category)
        if any(hint in normalized for hint in NON_MOVIE_CATEGORY_HINTS):
            continue
        if normalized in alias_names:
            genres.append(alias_names[normalized])
            continue

        genre = re.sub(r"^(?:film|movie|kino)\s*", "", category, flags=re.IGNORECASE).strip()
        if genre and normalize_title(genre) not in {"film", "movie", "kino"}:
            genres.append(genre)

    return unique_values(genres)


def source_cast(programme: ET.Element) -> list[str]:
    credits = programme.find("credits")
    if credits is None:
        return []

    actors: list[str] = []
    for actor in credits.findall("actor"):
        value = (actor.text or "").strip()
        if not value:
            continue
        # epg.ovh commonly uses "role - actor"; XMLTV may also contain the name alone.
        if " - " in value:
            value = value.rsplit(" - ", 1)[1].strip()
        actors.append(value)
    return unique_values(actors, CAST_LIMIT)


def cached_metadata(value: Any) -> dict[str, Any]:
    if isinstance(value, str):
        return {
            "year": value,
            "genres": [],
            "cast": [],
            "rating": None,
            "vote_count": 0,
            "tmdb_checked": False,
        }
    if not isinstance(value, dict):
        return {
            "year": "",
            "genres": [],
            "cast": [],
            "rating": None,
            "vote_count": 0,
            "tmdb_checked": False,
        }
    return {
        "year": str(value.get("year") or ""),
        "genres": unique_values(value.get("genres") or []),
        "cast": unique_values(value.get("cast") or [], CAST_LIMIT),
        "rating": normalized_rating(value.get("rating")),
        "vote_count": int(value.get("vote_count") or 0),
        "tmdb_id": value.get("tmdb_id"),
        "tmdb_checked": bool(value.get("tmdb_checked")),
    }


def merge_metadata(
    primary: dict[str, Any],
    secondary: dict[str, Any],
) -> dict[str, Any]:
    return {
        "year": primary.get("year") or secondary.get("year") or "",
        "genres": unique_values(
            list(primary.get("genres") or secondary.get("genres") or [])
        ),
        "cast": unique_values(
            list(primary.get("cast") or []) + list(secondary.get("cast") or []),
            CAST_LIMIT,
        ),
        "rating": (
            primary.get("rating")
            if primary.get("rating") is not None
            else secondary.get("rating")
        ),
        "vote_count": int(
            primary.get("vote_count") or secondary.get("vote_count") or 0
        ),
        "tmdb_id": primary.get("tmdb_id") or secondary.get("tmdb_id"),
        "tmdb_checked": bool(
            primary.get("tmdb_checked") or secondary.get("tmdb_checked")
        ),
    }


def ensure_year(programme: ET.Element, year: str) -> None:
    date_node = programme.find("date")
    if date_node is None:
        date_node = ET.SubElement(programme, "date")
    date_node.text = year


def prepend_metadata_to_descriptions(
    programme: ET.Element,
    metadata: dict[str, Any],
) -> bool:
    desc_nodes = programme.findall("desc")
    fields: list[str] = []

    if metadata.get("year"):
        fields.append(f"Rok produkcji: {metadata['year']}")
    if metadata.get("rating") is not None:
        fields.append(f"Ocena TMDb: {metadata['rating']:.1f}/10")
    if metadata.get("genres"):
        fields.append(f"Gatunek: {', '.join(metadata['genres'])}")
    if metadata.get("cast"):
        fields.append(f"Obsada: {', '.join(metadata['cast'])}")
    if not fields:
        return False

    prefix = f"[{' | '.join(fields)}]"

    if not desc_nodes:
        desc_node = ET.SubElement(programme, "desc")
        desc_node.text = prefix
        return True

    for desc_node in desc_nodes:
        current_text = (desc_node.text or "").strip()
        current_text = re.sub(
            r"^\[(?=[^\]]*(?:Rok produkcji|Ocena TMDb|Gatunek|Obsada):)[^\]]*\]\s*",
            "",
            current_text,
        ).strip()
        current_text = re.sub(
            r"^Rok produkcji:\s*\d{4}\.?\s*",
            "",
            current_text,
        ).strip()
        desc_node.text = f"{prefix} {current_text}" if current_text else prefix
    return True


def main() -> int:
    config = load_config()
    source_url = config["source_epg_url"]
    output_path = Path(config.get("output_path", "docs/epg.xml"))
    cache_path = Path(config.get("cache_path", ".cache/epg_metadata.json"))
    tmdb_language = config.get("tmdb_language", "pl-PL")
    tmdb_api_key = os.environ.get("TMDB_API_KEY")
    if not tmdb_api_key:
        raise RuntimeError("Missing TMDB_API_KEY environment variable")

    raw_xml = fetch_xml(source_url)
    root = ET.fromstring(raw_xml)
    cache = load_cache(cache_path)
    updated = 0
    skipped = 0
    desc_updates = 0
    programmes_by_key: dict[str, list[ET.Element]] = {}
    titles_by_key: dict[str, str] = {}
    metadata_by_key: dict[str, dict[str, Any]] = {}

    for programme in root.findall("programme"):
        categories = [node.text.strip() for node in programme.findall("category") if node.text]
        title = (programme.findtext("title") or "").strip()
        if not title:
            skipped += 1
            continue
        if looks_like_series(title, categories, programme):
            skipped += 1
            continue
        if not looks_like_movie(categories):
            skipped += 1
            continue

        key = normalize_title(title)
        existing_year = (programme.findtext("date") or "").strip()
        source_metadata = {
            "year": existing_year[:4] if existing_year else "",
            "genres": source_genres(categories),
            "cast": source_cast(programme),
            "rating": None,
            "vote_count": 0,
            "tmdb_checked": False,
        }
        previous_metadata = metadata_by_key.get(
            key,
            cached_metadata(cache.get(key)),
        )
        metadata_by_key[key] = merge_metadata(source_metadata, previous_metadata)
        programmes_by_key.setdefault(key, []).append(programme)
        titles_by_key.setdefault(key, title)

    lookup_keys = [
        key
        for key, metadata in metadata_by_key.items()
        if (
            not metadata["tmdb_checked"]
            and (
                not metadata["year"]
                or metadata.get("rating") is None
                or not metadata["genres"]
                or len(metadata["cast"]) < CAST_LIMIT
            )
        )
    ]
    print(f"Unique TMDb lookups: {len(lookup_keys)}")

    def lookup(key: str) -> tuple[str, dict[str, Any] | None, Exception | None]:
        try:
            metadata = metadata_by_key[key]
            include_details = (
                not metadata["genres"] or len(metadata["cast"]) < CAST_LIMIT
            )
            result = tmdb_search(
                tmdb_api_key,
                titles_by_key[key],
                tmdb_language,
                expected_year=metadata["year"],
                include_details=include_details,
            )
            return key, result, None
        except Exception as exc:
            return key, None, exc

    with ThreadPoolExecutor(max_workers=TMDB_WORKERS) as executor:
        futures = [executor.submit(lookup, key) for key in lookup_keys]
        for future in as_completed(futures):
            key, tmdb_metadata, error = future.result()
            if error is not None:
                print(
                    f"TMDb lookup failed for {titles_by_key[key]!r}: {error}",
                    file=sys.stderr,
                )
                continue
            if tmdb_metadata:
                metadata_by_key[key] = merge_metadata(
                    metadata_by_key[key],
                    tmdb_metadata,
                )
            metadata_by_key[key]["tmdb_checked"] = True

    for key, programmes in programmes_by_key.items():
        metadata = metadata_by_key[key]
        cache[key] = metadata

        for programme in programmes:
            if metadata["year"]:
                ensure_year(programme, metadata["year"])
            if prepend_metadata_to_descriptions(programme, metadata):
                desc_updates += 1
                updated += 1
            else:
                skipped += 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(root).write(output_path, encoding="utf-8", xml_declaration=True)
    save_cache(cache_path, cache)

    print(f"Updated programmes: {updated}")
    print(f"Updated descriptions: {desc_updates}")
    print(f"Skipped programmes: {skipped}")
    print(f"Output: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
