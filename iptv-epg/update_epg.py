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


def tmdb_search_once(api_key: str, title: str, language: str) -> str | None:
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


def tmdb_search(api_key: str, title: str, language: str) -> str | None:
    search_titles = build_search_titles(title)
    languages = [language]
    if language != "en-US":
        languages.append("en-US")

    for candidate_title in search_titles:
        for candidate_language in languages:
            year = tmdb_search_once(api_key, candidate_title, candidate_language)
            if year:
                return year
    return None


def ensure_year(programme: ET.Element, year: str) -> None:
    date_node = programme.find("date")
    if date_node is None:
        date_node = ET.SubElement(programme, "date")
    date_node.text = year


def prepend_year_to_descriptions(programme: ET.Element, year: str) -> bool:
    desc_nodes = programme.findall("desc")
    prefix = f"Rok produkcji: {year}"

    if not desc_nodes:
        desc_node = ET.SubElement(programme, "desc")
        desc_node.text = prefix
        return True

    for desc_node in desc_nodes:
        current_text = (desc_node.text or "").strip()
        current_text = re.sub(
            r"^Rok produkcji:\s*\d{4}\.?\s*",
            "",
            current_text,
        ).strip()
        desc_node.text = f"{prefix}. {current_text}" if current_text else prefix
    return True


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
    desc_updates = 0

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

        if existing_year:
            year = existing_year[:4]
        elif key in cache:
            year = cache[key] or None
        else:
            try:
                year = tmdb_search(tmdb_api_key, title, tmdb_language)
            except Exception as exc:
                print(f"TMDb lookup failed for {title!r}: {exc}", file=sys.stderr)
                time.sleep(1)
                continue
            cache[key] = year or ""
            time.sleep(0.25)

        if year:
            ensure_year(programme, year)
            if prepend_year_to_descriptions(programme, year):
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
