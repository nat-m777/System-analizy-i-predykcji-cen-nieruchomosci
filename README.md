
# 🕵️ Real Estate Scraper & Analyzer

Aplikacja typu **End-to-End** do monitorowania rynku nieruchomości. System automatycznie pobiera dane z serwisu **Otodom**, przechowuje je w bazie **PostgreSQL** i udostępnia interaktywny dashboard w **Streamlit** do analizy cen.

## 🚀 Główne Funkcje

* **Scraping na żądanie**: Pobieranie danych z wielu miast i dzielnic jednocześnie (obsługa nazw dwuczłonowych).
* **System Autoryzacji**: Każdy użytkownik ma własny widok i zarządza tylko swoimi danymi.
* **Automatyzacja**: Funkcja autoodświeżania danych co 5 minut.
* **Analiza Danych**: Obliczanie ceny za m², filtrowanie wyników i podgląd tabelaryczny.
* **Dockerized**: Całe środowisko (App + Database) uruchamiane jedną komendą.

## 🛠️ Stos technologiczny

* **Frontend/UI:** Streamlit
* **Scraper:** Selenium (Headless Chromium)
* **Baza danych:** PostgreSQL
* **Język:** Python (Pandas, SQLAlchemy)
* **Konteneryzacja:** Docker & Docker Compose

## 📦 Instalacja i Uruchomienie

### Wymagania
* Zainstalowany [Docker](https://www.docker.com/) oraz Docker Compose.

### Kroki
1. Sklonuj repozytorium:
   ```bash
   git clone https://github.com/twoj-uzytkownik/real-estate-scraper.git
   cd real_estate_scraper
   ```

2. Uruchom kontenery:
   ```bash
   docker-compose up --build
   ```

3. Otwórz aplikację w przeglądarce:
   ```text
   http://localhost:8501
   ```

## 🏗️ Struktura Projektu

```text
.
├── src/
│   ├── scraper/
│   │   └── otodom.py       # Silnik Selenium do scrapowania
│   ├── database/
│   │   └── db_manager.py   # Zarządzanie PostgreSQL (SQLAlchemy)
│   ├── auth.py             # Logika logowania i sesji
│   └── utils.py            # Funkcje pomocnicze i czyszczenie danych
├── pages/
│   ├── scraper.py          # Interfejs pobierania danych
│   └── analytics.py        # Dashboard i wizualizacje
├── main.py                 # Strona główna aplikacji
├── docker-compose.yml      # Konfiguracja usług (App, DB)
└── Dockerfile              # Instrukcja budowania obrazu aplikacji
```

## 📋 Konfiguracja Bazy Danych
Aplikacja automatycznie dba o strukturę bazy przy starcie. Główne kolumny tabeli `offers`:
* `title`, `city`, `district` – dane lokalizacyjne
* `price`, `area`, `price_per_m2` – dane finansowe
* `url` – unikalny link do oferty (zapobiega duplikatom)
* `owner` – identyfikator użytkownika, który pobrał dane

## ⚠️ Rozwiązywanie problemów

* **Problem z dzielnicami**: Jeśli dzielnica nie zwraca wyników, sprawdź czy nazwa w `city_config` jest poprawna. Scraper automatycznie zamienia polskie znaki i spacje na myślniki.
* **Baza danych**: Aby sprawdzić dane bezpośrednio w bazie (np. przez terminal), użyj komendy:
    ```bash
    docker exec -it <nazwa_kontenera_db> psql -U admin -d real_estate
    ```
* **Blokady**: Serwis Otodom może tymczasowo zablokować IP przy zbyt agresywnym scrapowaniu. Zalecane jest ustawienie `max_pages` na rozsądnym poziomie (np. 3-5).

---
