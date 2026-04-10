import pandas as pd
import time
import random
import re
from curl_cffi import requests
from bs4 import BeautifulSoup

class OtodomScraper:
    def __init__(self):
        self.impersonate = "chrome120"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "pl-PL,pl;q=0.9",
        }

    def _normalize_city(self, city):
        chars = {'ą': 'a', 'ć': 'c', 'ę': 'e', 'ł': 'l', 'ń': 'n', 'ó': 'o', 'ś': 's', 'ź': 'z', 'ż': 'z'}
        city = city.lower().strip()
        for char, replacement in chars.items():
            city = city.replace(char, replacement)
        return city.replace(" ", "-")

    def fetch_data(self, city="warszawa"):
        all_offers = []
        
        for page in range(1, 3):
            # Używamy prostego wyszukiwania na Lento
            url = f"https://www.lento.pl/ogloszenia.html?query=mieszkanie&miejscowosc={city}&strona={page}"
            
            try:
                print(f"🚀 Skanowanie Lento (Strona {page}) dla {city.capitalize()}...")
                response = requests.get(url, headers=self.headers, impersonate=self.impersonate, timeout=20)
                
                if response.status_code != 200:
                    break

                html = response.text
                
                # SZUKAMY CEN: liczba + zł
                prices = re.findall(r'([\d\s]{4,10})\s*zł', html)
                # SZUKAMY METRAŻY: liczba + m2 lub m²
                areas = re.findall(r'(\d+[\d,\.]*)\s*m[²2]', html)

                count = min(len(prices), len(areas))
                page_count = 0
                
                for i in range(count):
                    try:
                        p_raw = re.sub(r'[^\d]', '', prices[i])
                        price = float(p_raw) if p_raw else 0
                        
                        a_raw = areas[i].replace(',', '.')
                        area = float(a_raw) if a_raw else 0

                        if 150000 < price < 10000000 and 15 < area < 250:
                            all_offers.append({
                                'title': f"Mieszkanie {city.capitalize()} {area}m2",
                                'city': city.capitalize(),
                                'price': price,
                                'area': area,
                                'price_per_m2': round(price / area, 2),
                                'source': 'Lento-Global',
                                'scrape_date': pd.Timestamp.now()
                            })
                            page_count += 1
                    except:
                        continue
                
                print(f"✅ Strona {page}: Wyciągnięto {page_count} ofert.")
                time.sleep(2)

            except Exception as e:
                print(f"🔥 Błąd: {e}")
                break

        return pd.DataFrame(all_offers)