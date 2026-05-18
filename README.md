# AI Automatyzacja — mini-kalkulator potencjału

Statyczny kalkulator po polsku przygotowany dla działu **Obsługa klienta** w branży **e-commerce**. Narzędzie pomaga ocenić, które zadania warto automatyzować z pomocą AI, gdzie AI powinno wspierać człowieka, a które procesy należy chronić przed pełną automatyzacją.

## Jak uruchomić aplikację

Aplikacja jest statyczną stroną HTML/CSS/JS — nie wymaga instalowania zależności ani budowania projektu.

### Opcja 1: najprościej, bez serwera

Otwórz plik `index.html` bezpośrednio w przeglądarce, np. dwuklikiem w eksploratorze plików.

### Opcja 2: lokalny serwer HTTP — rekomendowane

W katalogu projektu uruchom:

```bash
python3 -m http.server 8000
```

Następnie wejdź w przeglądarce na:

```text
http://localhost:8000
```

Możesz też użyć pełnej ścieżki do pliku głównego:

```text
http://localhost:8000/index.html
```

Jeśli wcześniej otworzyłeś/aś adres `http://localhost:8000/ai-calc-index.html`, repozytorium zawiera teraz także ten alias, który automatycznie przekierowuje do właściwego pliku `index.html`.

Aby zatrzymać serwer, wróć do terminala i naciśnij `Ctrl+C`.

### Opcja 3: VS Code / Live Server

Jeśli używasz VS Code, możesz zainstalować rozszerzenie **Live Server**, kliknąć prawym przyciskiem myszy `index.html` i wybrać **Open with Live Server**.

### Publikacja online

Kalkulator można opublikować jako statyczną stronę, np. przez GitHub Pages, Netlify albo Vercel, ponieważ składa się wyłącznie z plików `index.html`, `styles.css` i `app.js`.

## Co zawiera wersja bazowa

- wybór departamentu i branży,
- lista 8 przykładowych zadań dla Customer Support,
- ocena potencjału AI w skali 1–5,
- ocena ryzyka w skali 1–5,
- automatyczna rekomendacja: `AUTOMATE`, `AUGMENT`, `PROTECT`, `REDESIGN`, `RESKILL`,
- dopasowanie typu narzędzia AI do każdego zadania,
- tabela z komentarzem i heatmapą rekomendacji,
- odpowiedzi na 4 pytania wymagane w zadaniu konkursowym.

## Funkcje dodatkowe względem podstawowej wersji

- kalkulacja szacowanej oszczędności czasu: liczba powtórzeń miesięcznie × czas jednej czynności × procent wsparcia AI,
- liczba osób wykonujących zadanie i właściciel procesu,
- dodatkowa skala łatwości wdrożenia 1–5,
- ocena dostępności danych,
- heatmapa kolorystyczna rekomendacji,
- Top 3 quick wins,
- Top 3 zadania chronione,
- lista nowych kompetencji dla działu,
- AI red flags,
- rekomendacja dla managera,
- mini-komunikat change management,
- plan pierwszego pilota,
- szacowanie potencjału FTE z korektą ryzyka, łatwości wdrożenia i dostępności danych,
- dodawanie i usuwanie zadań bez przeładowania strony,
- eksport wyników do CSV,
- drukowanie lub zapis do PDF.
