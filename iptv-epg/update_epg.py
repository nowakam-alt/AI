import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


MOVIE_CATEGORIES = {
    "film",
    "movie",
    "film fabularny",
    "kino",
    "dramat",
    "komedia",
    "thriller",
    "horror",
    "sensacyjny",
    "akcja",
    "romans",
    "science fiction",
    "sci-fi",
    "fantasy",
    "animacja",
    "familijny",
    "przygodowy",
    "western",
    "kryminalny",
    "dokumentalny",
}

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
    normalized = {normalize_title(item) for item in categories if item}
    return any(item in MOVIE_CATEGORIES for item in normalized)


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


def tmdb_search(api_key: str, title: str, language: str) -> str | None:
    params = urllib.parse.urlencode({
        "api_key": api_key,
        "query": title,
        "language": language,
        "include_adult": "false",
    })
    url = f"https://api.themoviedb.org/3/search/movie?{params}"
    with urllib.request.urlopen(url, timeout=60) as response:
        payload = json.loads(response.read().decode("utf-8"))
    results = payload.get("results", [])
    normalized_title = normalize_title(title)
    for item in results:
        candidate = normalize_title(item.get("title") or item.get("original_title") or "")
        if candidate == normalized_title and item.get("release_date"):
            return item["release_date"][:4]
    for item in results:
        if item.get("release_date"):
            return item["release_date"][:4]
    return None


def ensure_year(programme: ET.Element, year: str) -> None:
    date_node = programme.find("date")
    if date_node is None:
        date_node = ET.SubElement(programme, "date")
    date_node.text = year


def main() -> int:
    config = load_config()
    source_url = config["source_epg_url"]
    output_path = Path(config.get("output_path", "docs/epg.xml"))
    cache_path = Path(config.get("cache_path", ".cache/epg_years.json"))
    tmdb_language = config.get("tmdb_language", "pl-PL")
    tmdb_api_key = os.environ.get("TMDB_API_KEY")
    if not tmdb_api_key:
        raise RuntimeError("Missing TMDB_API_KEY environment variable")

    raw_xml = fetch_xml(source_url)
    root = ET.fromstring(raw_xml)
    cache = load_cache(cache_path)
    updated = 0
    skipped = 0

    for programme in root.findall("programme"):
        if programme.find("date") is not None and (programme.findtext("date") or "").strip():
            skipped += 1
            continue

        categories = [node.text.strip() for node in programme.findall("category") if node.text]
        title = (programme.findtext("title") or "").strip()
        if not title:
            skipped += 1
            continue
        if looks_like_series(title, categories, programme):
            skipped += 1
            continue
        normalized_categories = [normalize_title(item) for item in categories if item]
        is_explicit_movie = looks_like_movie(categories) or any(
            item.startswith("film") and "magazyn" not in item for item in normalized_categories
        )
        if categories and not is_explicit_movie:
            skipped += 1
            continue

        key = normalize_title(title)
        year = cache.get(key)
        if year is None:
            try:
                year = tmdb_search(tmdb_api_key, title, tmdb_language)
            except Exception as exc:
                print(f"TMDb lookup failed for {title!r}: {exc}", file=sys.stderr)
                time.sleep(1)
                continue
            cache[key] = year
            time.sleep(0.25)

        if year:
            ensure_year(programme, year)
            updated += 1
        else:
            skipped += 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(root).write(output_path, encoding="utf-8", xml_declaration=True)
    save_cache(cache_path, cache)

    print(f"Updated programmes: {updated}")
    print(f"Skipped programmes: {skipped}")
    print(f"Output: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
