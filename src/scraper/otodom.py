import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import pandas as pd
import time
import os


class OtodomScraper:

    def __init__(self):
        self.driver = None
        self.all_results = []

    # =====================================================
    # DRIVER
    # =====================================================
    def start_driver(self):

        options = Options()

        # Docker-safe headless
        options.add_argument("--headless=new")

        # Stability
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")

        # Anti detection
        options.add_argument("--disable-blink-features=AutomationControlled")

        # Fake normal browser
        options.add_argument(
            "user-agent=Mozilla/5.0 "
            "(Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        )

        # Chromium path (Docker)
        options.binary_location = os.getenv(
            "CHROME_BIN",
            "/usr/bin/chromium"
        )

        service = Service(
            os.getenv(
                "CHROMEDRIVER_PATH",
                "/usr/bin/chromedriver"
            )
        )

        self.driver = webdriver.Chrome(
            service=service,
            options=options
        )

        # Hide Selenium
        self.driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {
                "source": """
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    })
                """
            },
        )

        print("✅ Selenium driver started")

    # =====================================================
    # CLOSE
    # =====================================================
    def close_driver(self):

        if self.driver:
            self.driver.quit()
            self.driver = None

    # =====================================================
    # SCRAPE SINGLE PAGE
    # =====================================================
    def scrape_page(self, url, page):

        full_url = f"{url}?page={page}"

        print(f"➡️ {full_url}")

        self.driver.get(full_url)

        time.sleep(4)

        try:

            data = self.driver.execute_script(
                "return window.__NEXT_DATA__"
            )

            items = (
                data["props"]["pageProps"]["data"]
                ["searchAds"]["items"]
            )

            print(f"✅ {len(items)} offers")

            return items

        except Exception as e:

            print(f"❌ Scrape error: {e}")

            self.driver.save_screenshot(
                f"debug_page_{page}.png"
            )

            print(self.driver.page_source[:1500])

            return []

    # =====================================================
    # PARSE OFFERS
    # =====================================================
    def parse_offers(
        self,
        offers,
        city,
        district
    ):

        room_map = {
            "ONE": 1,
            "TWO": 2,
            "THREE": 3,
            "FOUR": 4,
            "FIVE": 5
        }

        for offer in offers:

            price_data = offer.get("totalPrice") or {}
            location_data = offer.get("location") or {}
            address_data = location_data.get("address") or {}

            price = price_data.get("value")
            area = offer.get("areaInSquareMeters")
            rooms = offer.get("roomsNumber")
            room_map = {
                "ONE": 1,
                "TWO": 2,
                "THREE": 3,
                "FOUR": 4,
                "FIVE": 5,
                "SIX": 6,
                "SEVEN": 7,
                "EIGHT": 8,
                "NINE": 9,
                "TEN": 10
            }

            if isinstance(rooms, str):
                rooms = room_map.get(
                    rooms.upper(),
                    None
                )

            try:
                price = float(price) if price else None
            except:
                price = None

            try:
                area = float(area) if area else None
            except:
                area = None

            if isinstance(rooms, str):
                rooms = room_map.get(
                    rooms.upper(),
                    None
                )

            price_per_m2 = None

            if price and area:
                price_per_m2 = price / area

            self.all_results.append({

                "title": offer.get("title"),

                "city": city.capitalize(),

                "district": district,

                "subdistrict": (
                    address_data.get("district")
                    or address_data.get("subdistrict")
                ),

                "price": price,

                "area": area,

                "rooms": rooms,

                "price_per_m2": price_per_m2,

                "url": (
                    "https://www.otodom.pl/pl/oferta/"
                    + str(offer.get("slug"))
                    if offer.get("slug")
                    else None
                ),

                "source": "Otodom",

                "scrape_date": pd.Timestamp.now()
            })

    # =====================================================
    # FETCH DATA
    # =====================================================
    def fetch_data(
        self,
        city,
        max_pages=2,
        selected_districts=None
    
    ):

        self.all_results = []

        city = city.lower()

        city_regions = {

            "warszawa": "mazowieckie",

            "gdansk": "pomorskie",

            "krakow": "malopolskie",

            "wroclaw": "dolnoslaskie",

            "poznan": "wielkopolskie",

            "lodz": "lodzkie"
        }

        region = city_regions.get(city)

        if not region:
            raise ValueError(
                f"Unsupported city: {city}"
            )

        if not selected_districts:
            return pd.DataFrame()

        self.start_driver()

        for district in selected_districts:

            try:

                print(
                    f"\n🏘️ Scraping district: {district}"
                )

                # IMPORTANT:
                # Otodom weird routing structure
                url = (
                    f"https://www.otodom.pl/pl/wyniki/"
                    f"sprzedaz/mieszkanie/"
                    f"{region}/"
                    f"{city}/"
                    f"{city}/"
                    f"{city}/"
                    f"{district}"
                )

                for page in range(1, max_pages + 1):

                    offers = self.scrape_page(
                        url,
                        page
                    )

                    if not offers:

                        print(
                            f"⚠️ No offers on page {page}"
                        )

                        break

                    self.parse_offers(
                        offers,
                        city,
                        district
                    )

                    time.sleep(2)

            except Exception as e:

                print(
                    f"❌ District error "
                    f"{district}: {e}"
                )

        self.close_driver()

        df = pd.DataFrame(self.all_results)

        if not df.empty:

            df["price"] = pd.to_numeric(
                df["price"],
                errors="coerce"
            )

            df["area"] = pd.to_numeric(
                df["area"],
                errors="coerce"
            )
            df["rooms"] = pd.to_numeric(
                df["rooms"],
                errors="coerce"
            )

            df = df.dropna(
                subset=["price", "area"]
            )

            df["price_per_m2"] = (
                df["price"] / df["area"]
            )
           

        return df

    # =====================================================
    # GET DISTRICTS
    # =====================================================
    def get_districts(
        self,
        city="warszawa",
        region="mazowieckie"
    ):

        self.start_driver()

        url = (
            f"https://www.otodom.pl/pl/wyniki/"
            f"sprzedaz/mieszkanie/"
            f"{region}/{city}"
        )

        self.driver.get(url)

        time.sleep(4)

        try:

            data = self.driver.execute_script(
                "return window.__NEXT_DATA__"
            )

            filters = (
                data["props"]["pageProps"]["data"]
                ["searchAds"]["filters"]
            )

            location_filter = next(
                f for f in filters
                if f.get("name") == "locations"
            )

            districts = []

            for d in location_filter.get(
                "options",
                []
            ):

                districts.append({

                    "name": d.get("label"),

                    "slug": d.get("value")
                })

            self.close_driver()

            return districts

        except Exception as e:

            print(
                f"❌ District fetch error: {e}"
            )

            self.close_driver()

            return []


# =====================================================
# STREAMLIT UI
# =====================================================

# =====================================================
# SELECT DISTRICTS
# =====================================================

if "districts" in st.session_state:

    district_map = {

        d["name"]: d["slug"]

        for d in st.session_state["districts"]
    }

    selected_names = st.multiselect(
        "Select districts",
        list(district_map.keys())
    )

    max_pages = st.slider(
        "Pages per district",
        1,
        10,
        2
    )

    # =================================================
    # SCRAPE
    # =================================================

    if st.button("Start scraping"):

        selected_slugs = [

            district_map[name]

            for name in selected_names
        ]

        with st.spinner("Scraping offers..."):

            df = scraper.fetch_data(
                city=city,
                max_pages=max_pages,
                selected_districts=selected_slugs
            )

        if df.empty:

            st.error(
                "❌ No offers downloaded"
            )

        else:

            st.success(
                f"✅ Downloaded "
                f"{len(df)} offers"
            )

            st.dataframe(
                df,
                width="stretch"
            )

            csv = df.to_csv(
                index=False
            ).encode("utf-8")

            st.download_button(
                "📥 Download CSV",
                csv,
                file_name="otodom_offers.csv",
                mime="text/csv"
            )