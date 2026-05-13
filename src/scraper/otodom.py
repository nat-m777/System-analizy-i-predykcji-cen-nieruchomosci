import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import pandas as pd
import time
import os
import re

class OtodomScraper:
    def __init__(self):
        self.driver = None
        self.all_results = []

    

    def clean_slug(self, text):
        """
        Dostosowuje nazwy do formatu Otodom (np. Praga-Północ -> praga--polnoc).
        """
        text = text.lower().strip()
        # Mapa polskich znaków
        chars = {
            'ą': 'a', 'ć': 'c', 'ę': 'e', 'ł': 'l', 'ń': 'n', 
            'ó': 'o', 'ś': 's', 'ź': 'z', 'ż': 'z'
        }
        for pol, lat in chars.items():
            text = text.replace(pol, lat)
        
        # Logika podwójnego myślnika dla Otodom
        if '-' in text:
            text = text.replace('-', '--')
        
        # Zamiana spacji na myślniki (dla dzielnic typu 'Stare Miasto')
        text = text.replace(' ', '-')
        
        # Usuwanie znaków specjalnych
        text = re.sub(r'[^a-z0-9\-]', '', text)
        return text

    def start_driver(self):
        """Inicjalizuje przeglądarkę w trybie headless."""
        if self.driver: return
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")

        chrome_bin = os.getenv("CHROME_BIN", "/usr/bin/chromium")
        driver_path = os.getenv("CHROMEDRIVER_PATH", "/usr/bin/chromedriver")
        
        try:
            if os.path.exists(chrome_bin):
                options.binary_location = chrome_bin
            service = Service(driver_path)
            self.driver = webdriver.Chrome(service=service, options=options)
        except Exception as e:
            # Fallback dla środowisk lokalnych
            self.driver = webdriver.Chrome(options=options)

    def close_driver(self):
        """Metoda, której brakowało – bezpiecznie zamyka sesję Selenium."""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None

    def scrape_page(self, url, page):
        """Pobiera dane JSON z konkretnej strony wyników."""
        full_url = f"{url}?page={page}"
        print(f"🔍 Scrapowanie: {full_url}")
        
        try:
            self.driver.get(full_url)
            time.sleep(4) 
            data = self.driver.execute_script("return window.__NEXT_DATA__")
            
            props = data.get("props", {}).get("pageProps", {})
            items = props.get("data", {}).get("searchAds", {}).get("items", [])
            
            # Rezerwowa ścieżka w JSONie
            if not items:
                items = props.get("searchAds", {}).get("items", [])
                
            return items
        except Exception as e:
            print(f"⚠️ Błąd Selenium: {e}")
            return []

    def parse_offers(self, offers, city, district):
        """Wyciąga potrzebne informacje z surowego JSONa."""
        room_map = {"ONE": 1, "TWO": 2, "THREE": 3, "FOUR": 4, "FIVE": 5}
        for offer in offers:
            try:
                price = offer.get("totalPrice", {}).get("value")
                area = offer.get("areaInSquareMeters")
                rooms = offer.get("roomsNumber")
                
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
                continue

    def fetch_data(self, city, max_pages=2, selected_districts=None):
        self.all_results = []
        city_slug = self.clean_slug(city).replace('--', '-') # Miasta zawsze mają jeden myślnik
        
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
                # 1. Przygotuj oba warianty sluga
                slug_double = self.clean_slug(district) # np. nowe--miasto
                slug_single = slug_double.replace('--', '-') # np. nowe-miasto
                
                # Próbujemy obu wariantów, zaczynając od tego z Twojego przykładu (single)
                found_for_district = False
                for current_slug in [slug_single, slug_double]:
                    if found_for_district: break
                    
                    base_url = f"https://www.otodom.pl/pl/wyniki/sprzedaz/mieszkanie/{region}/{city_slug}/{city_slug}/{city_slug}/{current_slug}"
                    
                    # Sprawdzamy pierwszą stronę
                    offers = self.scrape_page(base_url, 1)
                    if offers:
                        print(f"✅ Trafienie! Slug '{current_slug}' działa dla {district}")
                        self.parse_offers(offers, city, district)
                        found_for_district = True
                        
                        # Pobieramy resztę stron jeśli potrzeba
                        for page in range(2, max_pages + 1):
                            more_offers = self.scrape_page(base_url, page)
                            if more_offers:
                                self.parse_offers(more_offers, city, district)
                            else:
                                break
                    else:
                        print(f"... slug '{current_slug}' nie zwrócił wyników, sprawdzam dalej.")

        finally:
            self.close_driver()

        return pd.DataFrame(self.all_results)
    
    def get_driver():
        options = Options()
        options.add_argument("--headless") # Konieczne w chmurze!
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        
        return webdriver.Chrome(options=options)