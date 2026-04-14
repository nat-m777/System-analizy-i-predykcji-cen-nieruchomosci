from selenium import webdriver
import pandas as pd
import time


class OtodomScraper:
    """
    Automatyczny scraper portalu Otodom wykorzystujący Selenium.
    
    Klasa parsuje dane JSON zagnieżdżone w strukturze HTML strony (window.__NEXT_DATA__)
    i obsługuje paginację oraz podział na dzielnice.
    """
    def __init__(self, driver_path=None):
        """
        Inicjalizuje instancję scrapera.
        
        Args:
            driver_path (str, optional): Ścieżka do ChromeDrivera.
        """

        self.driver_path = driver_path
        self.driver = None
        self.all_results = []

    # =====================
    # DRIVER
    # =====================
    def start_driver(self):
        """Uruchamia przeglądarkę Chrome w trybie sterowanym przez Selenium."""
        self.driver = webdriver.Chrome(
            executable_path=self.driver_path
        ) if self.driver_path else webdriver.Chrome()

    def close_driver(self):
        """Bezpiecznie zamyka przeglądarkę i zwalnia zasoby."""
        if self.driver:
            self.driver.quit()

    # =====================
    # SCRAPING
    # =====================
    def scrape_page(self, url, page):
        """
        Pobiera surowe dane ofert z konkretnej strony wyników.

        Args:
            url (str): Bazowy URL wyszukiwania.
            page (int): Numer strony do pobrania.
        
        Returns:
            list: Lista słowników z danymi ofert.
        """
        full_url = f"{url}?page={page}"
        self.driver.get(full_url)
        time.sleep(3)

        data = self.driver.execute_script("return window.__NEXT_DATA__")

        try:
            return data["props"]["pageProps"]["data"]["searchAds"]["items"]
        except KeyError:
            return []

    def parse_offers(self, offers, city, district_slug):
        """
        Przetwarza surową listę ofert na ustandaryzowany format słownika.

        Args:
            offers (list): Lista ofert z JSONa Otodom.
            city (str): Nazwa miasta.
            district_slug (str): Slug dzielnicy użyty w wyszukiwaniu.
        """
        for offer in offers:
            price_data = offer.get("totalPrice") or {}
            location_data = offer.get("location") or {}
            address_data = location_data.get("address") or {}

            price = price_data.get("value")
            area = offer.get("areaInSquareMeters")
            rooms = offer.get("roomsNumber")

            # --- konwersje ---
            price = float(price) if isinstance(price, (int, float)) else None
            area = float(area) if isinstance(area, (int, float)) else None

            room_map = {
                "ONE": 1,
                "TWO": 2,
                "THREE": 3,
                "FOUR": 4,
                "FIVE": 5
            }

            if isinstance(rooms, str):
                rooms = room_map.get(rooms.upper(), None)

            price_per_m2 = (price / area) if price and area else None

            self.all_results.append({
                "title": offer.get("title"),
                "city": city.capitalize(),
                "district": district_slug,  # 🔥 główne źródło
                "subdistrict": address_data.get("district") or address_data.get("subdistrict"),
                "price": price,
                "area": area,
                "rooms": rooms,
                "price_per_m2": price_per_m2,
                "source": "Otodom",
                "scrape_date": pd.Timestamp.now()
            })

    def scrape_district(self, city, region, district, max_pages):
        url = f"https://www.otodom.pl/pl/wyniki/sprzedaz/mieszkanie/{region}/{city}/{city}/{city}/{district}"

        page = 1
        while True:
            offers = self.scrape_page(url, page)
            if not offers:
                break

            self.parse_offers(offers, city, district)

            page += 1
            if max_pages and page > max_pages:
                break

            time.sleep(1.5)

    # =====================
    # GŁÓWNA FUNKCJA
    # =====================
    def fetch_data(self, city, max_pages=2, selected_districts=None):
        """
        Główna metoda pobierająca dane dla wybranego miasta i dzielnic.
        
        Returns:
            pd.DataFrame: Zbiór pobranych ofert z obliczoną ceną za m2.
        """

        city = city.lower()

        city_config = {
            "warszawa": {
                "region": "mazowieckie",
                "districts": [
                    "bemowo","bialoleka","bielany","mokotow","ochota",
                    "praga-polnoc","praga-poludnie","rembertow","srodmiescie",
                    "targowek","ursus","ursynow","wawer","wesola",
                    "wilanow","wlochy","wola","zoliborz"
                ]
            },
            "krakow": {
                "region": "malopolskie",
                "districts": ["stare-miasto","krowodrza","podgorze","nowa-huta"]
            },
            "wroclaw": {
                "region": "dolnoslaskie",
                "districts": ["krzyki","psie-pole","fabryczna","stare-miasto","srodmiescie"]
            },
            "lodz": {
                "region": "lodzkie",
                "districts": ["baluty","gorna","polesie","srodmiescie","widzew"]
            },
            "poznan": {
                "region": "wielkopolskie",
                "districts": ["stare-miasto","nowe-miasto","grunwald","jezyce","wilda"]
            },
            "gdansk": {
                "region": "pomorskie",
                "districts": ["wrzeszcz","oliwa","przymorze","zaspa","chelm","jasien","srodmiescie"]
            }
        }

        if city not in city_config:
            raise ValueError(f"Nieobsługiwane miasto: {city}")

        region = city_config[city]["region"]
        districts = city_config[city]["districts"]

        # 🔥 filtr dzielnic
        if selected_districts:
            districts = [d for d in districts if d in selected_districts]

        self.all_results = []
        self.start_driver()

        for district in districts:
            print(f"➡️ {city} - {district}")
            try:
                self.scrape_district(city, region, district, max_pages)
            except Exception as e:
                print(f"Błąd {district}: {e}")

        self.close_driver()

        df = pd.DataFrame(self.all_results)

        if not df.empty:
            df["price"] = pd.to_numeric(df["price"], errors="coerce")
            df["area"] = pd.to_numeric(df["area"], errors="coerce")
            df = df.dropna(subset=["price", "area"])
            df["price_per_m2"] = df["price"] / df["area"]

        return df