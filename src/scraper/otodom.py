import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import pandas as pd
import time
import os
import re

class OtodomScraper:
    """
    Zaawansowany scraper portalu Otodom wykorzystujący Selenium.
    Wykorzystuje mechanizm wstrzykiwania skryptów JS do wyciągania danych 
    bezpośrednio z obiektu __NEXT_DATA__ (JSON), co jest szybsze i stabilniejsze niż parsowanie HTML.
    """
    def __init__(self):
        self.driver = None
        self.all_results = []

    def clean_slug(self, text):
        """
        Dostosowuje nazwy miast i dzielnic do specyficznego formatu URL Otodom.
        Obsługuje polskie znaki oraz unikalną logikę podwójnego myślnika (np. Praga-Północ -> praga--polnoc).
        """
        text = text.lower().strip()
        # Mapa transliteracji polskich znaków diakrytycznych
        chars = {
            'ą': 'a', 'ć': 'c', 'ę': 'e', 'ł': 'l', 'ń': 'n', 
            'ó': 'o', 'ś': 's', 'ź': 'z', 'ż': 'z'
        }
        for pol, lat in chars.items():
            text = text.replace(pol, lat)
        
        # Specyfika Otodom: dzielnice z myślnikiem często wymagają podwójnego separatora w URL
        if '-' in text:
            text = text.replace('-', '--')
        
        # Zamiana spacji na myślniki (dzielnice wieloczłonowe)
        text = text.replace(' ', '-')
        
        # Usuwanie wszelkich znaków poza alfanumerycznymi i myślnikiem
        text = re.sub(r'[^a-z0-9\-]', '', text)
        return text

    def start_driver(self):
        """
        Konfiguruje i uruchamia przeglądarkę Chrome w trybie 'headless'.
        Zawiera optymalizacje pod kątem omijania prostych systemów anty-botowych (AutomationControlled).
        """
        if self.driver: return
        options = Options()
        options.add_argument("--headless=new") # Tryb bez okna (wymagany na serwerach)
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        # Maskowanie user-agent, by symulować realną przeglądarkę
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")

        # Ścieżki do plików binarnych (obsługa środowisk Docker/Linux)
        chrome_bin = os.getenv("CHROME_BIN", "/usr/bin/chromium")
        driver_path = os.getenv("CHROMEDRIVER_PATH", "/usr/bin/chromedriver")
        
        try:
            if os.path.exists(chrome_bin):
                options.binary_location = chrome_bin
            service = Service(driver_path)
            self.driver = webdriver.Chrome(service=service, options=options)
        except Exception as e:
            # Fallback: próba uruchomienia z domyślnych ścieżek systemowych (np. Windows)
            self.driver = webdriver.Chrome(options=options)

    def close_driver(self):
        """Zwalnia zasoby systemowe poprzez poprawne zamknięcie sesji przeglądarki."""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None

    def scrape_page(self, url, page):
        """
        Ładuje stronę i wyciąga z niej dane zawarte w ukrytym obiekcie JSON (__NEXT_DATA__).
        Jest to najbardziej odporna na zmiany wyglądu strony metoda ekstrakcji.
        """
        full_url = f"{url}?page={page}"
        print(f"🔍 Scrapowanie: {full_url}")
        
        try:
            self.driver.get(full_url)
            time.sleep(4) # Czekamy na wyrenderowanie skryptów przez Reacta
            
            # Pobieranie danych bezpośrednio z pamięci przeglądarki (JSON)
            data = self.driver.execute_script("return window.__NEXT_DATA__")
            
            # Nawigacja po strukturze JSON portalu Otodom
            props = data.get("props", {}).get("pageProps", {})
            items = props.get("data", {}).get("searchAds", {}).get("items", [])
            
            # Fallback: obsługa alternatywnej struktury drzewa obiektów
            if not items:
                items = props.get("searchAds", {}).get("items", [])
                
            return items
        except Exception as e:
            print(f"⚠️ Błąd Selenium: {e}")
            return []

    def parse_offers(self, offers, city, district):
        """
        Mapuje surowy słownik z JSONa na ustandaryzowaną strukturę danych aplikacji.
        Przeprowadza czyszczenie typów (string -> float) i mapowanie pokoi.
        """
        room_map = {"ONE": 1, "TWO": 2, "THREE": 3, "FOUR": 4, "FIVE": 5}
        for offer in offers:
            try:
                price = offer.get("totalPrice", {}).get("value")
                area = offer.get("areaInSquareMeters")
                rooms = offer.get("roomsNumber")
                
                # Konwersja formatu tekstowego (ONE, TWO...) na liczbowy
                if isinstance(rooms, str):
                    rooms = room_map.get(rooms.upper(), rooms)

                self.all_results.append({
                    "title": offer.get("title"),
                    "city": city.capitalize(),
                    "district": district,
                    "price": float(price) if price else None,
                    "area": float(area) if area else None,
                    "rooms": rooms,
                    "url": "https://www.otodom.pl/pl/oferta/" + str(offer.get("slug", "")),
                    "scrape_date": pd.Timestamp.now()
                })
            except:
                continue # Pomiń oferty z uszkodzonymi danymi

    def fetch_data(self, city, max_pages=2, selected_districts=None):
        """
        Główna pętla sterująca procesem zbierania danych dla wybranych miast i dzielnic.
        Automatycznie dopasowuje strukturę regionów (mazowieckie, malopolskie itd.).
        """
        self.all_results = []
        city_slug = self.clean_slug(city).replace('--', '-') # Miasta zawsze mają separator pojedynczy
        
        # Słownik pomocniczy do budowy ścieżki geograficznej w URL
        city_regions = {
            "warszawa": "mazowieckie", "krakow": "malopolskie", 
            "wroclaw": "dolnoslaskie", "poznan": "wielkopolskie", 
            "gdansk": "pomorskie", "lodz": "lodzkie"
        }
        region = city_regions.get(city_slug)

        if not region or not selected_districts:
            return pd.DataFrame()

        self.start_driver()

        try:
            for district in selected_districts:
                # Otodom bywa niekonsekwentny w slugach (czasem pojedynczy, czasem podwójny myślnik)
                slug_double = self.clean_slug(district) 
                slug_single = slug_double.replace('--', '-') 
                
                found_for_district = False
                # Algorytm sprawdzania obu wariantów URL w celu znalezienia poprawnego
                for current_slug in [slug_single, slug_double]:
                    if found_for_district: break
                    
                    base_url = f"https://www.otodom.pl/pl/wyniki/sprzedaz/mieszkanie/{region}/{city_slug}/{city_slug}/{city_slug}/{current_slug}"
                    
                    # Weryfikacja pierwszej strony (czy slug działa?)
                    offers = self.scrape_page(base_url, 1)
                    if offers:
                        print(f"✅ Trafienie! Slug '{current_slug}' działa dla {district}")
                        self.parse_offers(offers, city, district)
                        found_for_district = True
                        
                        # Pobieranie kolejnych stron (paginacja)
                        for page in range(2, max_pages + 1):
                            more_offers = self.scrape_page(base_url, page)
                            if more_offers:
                                self.parse_offers(more_offers, city, district)
                            else:
                                break
                    else:
                        print(f"... slug '{current_slug}' nie zwrócił wyników, sprawdzam dalej.")

        finally:
            # Kluczowe: zawsze zamykamy przeglądarkę, by nie 'wyciekał' RAM
            self.close_driver()

        return pd.DataFrame(self.all_results)
    
    @staticmethod
    def get_driver():
        """Metoda statyczna do szybkiej inicjalizacji drivera (uproszczona)."""
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        return webdriver.Chrome(options=options)