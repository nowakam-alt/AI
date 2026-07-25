# IPTV EPG Enricher

Ten katalog buduje gotowy plik XMLTV dla GitHub Pages.

Na początku opisu filmu dodawany jest blok:

`[Rok produkcji: 2025 | Gatunek: dramat | Obsada: Aktor 1, Aktor 2, Aktor 3]`

Gatunek i obsada są pobierane najpierw z XMLTV, a brakujące dane z TMDb.
W opisie umieszczanych jest maksymalnie pięć głównych nazwisk.

Wejście:

- `https://epg.ovh/plar.xml`

Wyjście:

- `docs/epg.xml`

Wymagany sekret GitHub Actions:

- `TMDB_API_KEY` = `API Key v3` z TMDb
