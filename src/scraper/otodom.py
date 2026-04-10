from selenium import webdriver
import pandas as pd
import time

class OtodomScraper:
    def __init__(self, max_pages=None, driver_path=None):
        self.max_pages = max_pages
        self.driver_path = driver_path
        self.driver = None
        self.all_results = []
        self.city = None
        self.region = None
        self.base_url = None

    def start_driver(self):
        self.driver = webdriver.Chrome(executable_path=self.driver_path) if self.driver_path else webdriver.Chrome()

    def close_driver(self):
        if self.driver:
            self.driver.quit()

    def scrape_page(self, page):
        url = f"{self.base_url}?page={page}"
        self.driver.get(url)
        time.sleep(5)

        data = self.driver.execute_script("return window.__NEXT_DATA__")
        try:
            offers = data["props"]["pageProps"]["data"]["searchAds"]["items"]
        except KeyError:
            return []

        return offers

    def parse_offers(self, offers):
        for offer in offers:
            price_data = offer.get("totalPrice") or {}
            location_data = offer.get("location") or {}
            address_data = location_data.get("address") or {}

        # 🔥 pobranie danych
            price = price_data.get("value")
            area = offer.get("areaInSquareMeters")
            rooms = offer.get("roomsNumber")

        # 🔥 czyszczenie danych
            price = float(price) if isinstance(price, (int, float)) else None
            area = float(area) if isinstance(area, (int, float)) else None

        # 🔥 rooms może być string ("THREE")
            room_map = {
                "ONE": 1,
                "TWO": 2,
                "THREE": 3,
                "FOUR": 4,
                "FIVE": 5
            }

            if isinstance(rooms, str):
                rooms = room_map.get(rooms.upper(), None)

        # 🔥 bezpieczne liczenie
            price_per_m2 = (price / area) if price and area else None

            self.all_results.append({
                "title": offer.get("title"),
                "city": self.city.capitalize(),
                "price": price,
                "area": area,
                "rooms": rooms,
                "district": address_data.get("district"),
                "price_per_m2": price_per_m2,
                "source": "Otodom"
            })

    def scrape_all(self):
        self.start_driver()
        page = 1
        while True:
            offers = self.scrape_page(page)
            if not offers:
                break
            self.parse_offers(offers)
            page += 1
            if self.max_pages and page > self.max_pages:
                break
            time.sleep(2)
        self.close_driver()
        df = pd.DataFrame(self.all_results)
        print(df.dtypes)

        if not df.empty:
        # 🔥 konwersja typów (NAJWAŻNIEJSZE)
            df["price"] = pd.to_numeric(df["price"], errors="coerce")
            df["area"] = pd.to_numeric(df["area"], errors="coerce")

        # 🔥 usuń złe dane
            df = df.dropna(subset=["price", "area"])

         # 🔥 dopiero teraz licz
            df["price_per_m2"] = df["price"] / df["area"]
        
        return df

    def fetch_data(self, city, max_pages=2):
        city_to_region = {
            "warszawa": "mazowieckie",
            "krakow": "malopolskie",
            "wroclaw": "dolnoslaskie",
            "lodz": "lodzkie",
            "poznan": "wielkopolskie",
            "gdansk": "pomorskie"
        }

        self.city = city.lower()
        self.base_url = f"https://www.otodom.pl/pl/wyniki/sprzedaz/mieszkanie/{self.region}/{self.city}/{self.city}/{self.city}"
        self.max_pages = int(max_pages) if max_pages is not None else None  # <- tutaj
        self.all_results = []
        return self.scrape_all()