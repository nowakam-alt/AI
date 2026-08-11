# IPTV EPG Enricher

Ten katalog buduje gotowy plik XMLTV dla GitHub Pages.

Pierwsza linia opisu filmu lub serialu zawiera kompaktowe metadane:

`|2025|7.2|dramat|Aktor 1, Aktor 2, Aktor 3`

Kolejność pól: rok, ocena TMDb, gatunek, obsada. Brakujące pole pozostaje puste.
Oryginalny opis programu z XMLTV pozostaje bez zmian po jednej pustej linii.

Gatunek i obsada są pobierane najpierw z XMLTV, a brakujące dane z TMDb.
Filmy korzystają z danych TMDb Movie, a seriale z TMDb TV.
W opisie umieszczanych jest maksymalnie pięć głównych nazwisk.

Wejście:

- `https://epg.ovh/plar.xml`

Wyjście:

- `docs/epg.xml`

Wymagany sekret GitHub Actions:

- `TMDB_API_KEY` = `API Key v3` z TMDb
